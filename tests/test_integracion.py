"""
Tests de INTEGRACIÓN

Objetivo: comprobar que los módulos se comunican correctamente entre sí:
SQLAlchemy (database.py + models.py) se conecta de verdad a PostgreSQL,
usa la tabla 'questions', e inserta/actualiza/borra/consulta datos reales.
"""

import uuid

import pytest
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.models import Question


@pytest.fixture
def db_session():
    """Sesión real de SQLAlchemy contra PostgreSQL. Al terminar el test,
    borra cualquier fila que el propio test haya creado (por id)."""
    session = SessionLocal()
    created_ids = []
    try:
        yield session, created_ids
    finally:
        if created_ids:
            session.query(Question).filter(Question.id.in_(created_ids)).delete(
                synchronize_session=False
            )
            session.commit()
        session.close()


def test_engine_conecta_a_postgresql():
    """El engine de SQLAlchemy debe poder abrir una conexión real a Postgres."""
    with engine.connect() as conn:
        resultado = conn.execute(text("SELECT 1"))
        assert resultado.scalar() == 1


def test_tabla_questions_existe_en_la_base():
    """La tabla 'questions' debe existir en el esquema public de questions_db
    (la creó Base.metadata.create_all en el evento de startup de la app)."""
    with engine.connect() as conn:
        resultado = conn.execute(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'questions'"
                ")"
            )
        )
        assert resultado.scalar() is True


def test_insertar_y_recuperar_pregunta(db_session):
    """Insertar una Question vía SQLAlchemy y volver a leerla con una query
    nueva debe devolver exactamente los mismos datos: prueba que el ORM
    y la conexión a Postgres funcionan juntos de punta a punta."""
    session, created_ids = db_session
    marca = uuid.uuid4().hex[:8]

    nueva = Question(
        question=f"¿Pregunta de integración {marca}?",
        answer="Respuesta de integración",
        category="test-integracion",
        source="pytest",
    )
    session.add(nueva)
    session.commit()
    session.refresh(nueva)
    created_ids.append(nueva.id)

    assert nueva.id is not None  # Postgres le asignó un id autoincremental

    recuperada = session.query(Question).filter(Question.id == nueva.id).first()
    assert recuperada is not None
    assert recuperada.question == f"¿Pregunta de integración {marca}?"
    assert recuperada.answer == "Respuesta de integración"
    assert recuperada.category == "test-integracion"
    assert recuperada.source == "pytest"


def test_actualizar_pregunta_existente(db_session):
    """Modificar un campo, hacer commit, y volver a leer desde la base debe
    reflejar el cambio: prueba que el ciclo update -> commit -> refresh
    funciona correctamente contra Postgres."""
    session, created_ids = db_session

    nueva = Question(question="Pregunta original", answer="Respuesta original")
    session.add(nueva)
    session.commit()
    created_ids.append(nueva.id)

    nueva.answer = "Respuesta corregida"
    session.commit()

    releida = session.query(Question).filter(Question.id == nueva.id).first()
    assert releida.answer == "Respuesta corregida"


def test_eliminar_pregunta(db_session):
    """Borrar una fila y volver a buscarla por id debe devolver None: prueba
    que delete() + commit() se propagan de verdad a Postgres."""
    session, _created_ids = db_session

    nueva = Question(question="Pregunta a borrar", answer="Respuesta a borrar")
    session.add(nueva)
    session.commit()
    id_creado = nueva.id

    session.delete(nueva)
    session.commit()

    borrada = session.query(Question).filter(Question.id == id_creado).first()
    assert borrada is None


def test_filtro_por_categoria_contra_la_base_real(db_session):
    """Insertar varias preguntas con una categoría única y filtrar por esa
    categoría debe devolver exactamente esas filas: prueba la integración
    entre el filtro de SQLAlchemy (.filter) y los datos reales en Postgres."""
    session, created_ids = db_session
    categoria = f"test-cat-{uuid.uuid4().hex[:8]}"

    for i in range(3):
        q = Question(
            question=f"Pregunta {i} de la categoría {categoria}",
            answer=f"Respuesta {i}",
            category=categoria,
        )
        session.add(q)
    session.commit()

    insertadas = session.query(Question).filter(Question.category == categoria).all()
    created_ids.extend([q.id for q in insertadas])

    assert len(insertadas) == 3
    assert all(q.category == categoria for q in insertadas)