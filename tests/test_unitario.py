"""
Tests UNITARIOS

Objetivo: validar la lógica interna de los componentes en total aislamiento,
SIN conexión a base de datos y SIN levantar la API (no se usa TestClient).
"""

import pytest
from pydantic import ValidationError

from app.question_schemas import QuestionCreate, QuestionResponse
from app.models import Question


# ---------------------------------------------------------------------------
# QuestionCreate: validación de datos de entrada
# ---------------------------------------------------------------------------

def test_question_create_acepta_datos_completos():
    """QuestionCreate debe aceptar todos los campos cuando vienen bien tipados."""
    data = QuestionCreate(
        question="¿Cuál es la capital de Francia?",
        answer="París",
        category="geografía",
        source="wikipedia",
    )
    assert data.question == "¿Cuál es la capital de Francia?"
    assert data.answer == "París"
    assert data.category == "geografía"
    assert data.source == "wikipedia"


def test_question_create_campos_opcionales_por_defecto_none():
    """category y source son opcionales: si no se mandan, deben quedar en None."""
    data = QuestionCreate(question="¿Pregunta?", answer="Respuesta")
    assert data.category is None
    assert data.source is None


def test_question_create_falla_sin_question():
    """question es obligatorio: omitirlo debe disparar ValidationError."""
    with pytest.raises(ValidationError):
        QuestionCreate(answer="Respuesta sin pregunta")


def test_question_create_falla_sin_answer():
    """answer es obligatorio: omitirlo debe disparar ValidationError."""
    with pytest.raises(ValidationError):
        QuestionCreate(question="Pregunta sin respuesta")


def test_question_create_falla_con_question_none():
    """question no puede ser None explícito (no está declarado como Optional)."""
    with pytest.raises(ValidationError):
        QuestionCreate(question=None, answer="Respuesta")


def test_question_create_ignora_campos_extra():
    """Campos no declarados en el schema no deben romper la validación
    (comportamiento por defecto de Pydantic v2: los ignora silenciosamente)."""
    data = QuestionCreate(
        question="¿Pregunta?",
        answer="Respuesta",
        campo_inventado="esto no existe en el schema",
    )
    assert not hasattr(data, "campo_inventado")


# ---------------------------------------------------------------------------
# Question (modelo SQLAlchemy): instanciación aislada, sin DB
# ---------------------------------------------------------------------------

def test_question_model_se_instancia_sin_tocar_la_db():
    """Crear un objeto Question en memoria no requiere conexión a la base."""
    q = Question(
        question="¿Pregunta de prueba?",
        answer="Respuesta de prueba",
        category="test",
        source=None,
    )
    assert q.question == "¿Pregunta de prueba?"
    assert q.answer == "Respuesta de prueba"
    assert q.category == "test"
    assert q.source is None
    assert q.id is None  # todavía no fue persistido, no tiene id asignado


def test_question_model_tablename_y_columnas():
    """Chequeo simple de la definición del modelo: nombre de tabla y columnas
    declaradas, sin necesidad de que la tabla exista realmente en Postgres."""
    assert Question.__tablename__ == "questions"
    columnas = {c.name for c in Question.__table__.columns}
    assert columnas == {"id", "question", "answer", "category", "source"}


# ---------------------------------------------------------------------------
# QuestionResponse: conversión desde un objeto tipo ORM (from_attributes)
# ---------------------------------------------------------------------------

def test_question_response_desde_objeto_orm():
    """QuestionResponse debe poder construirse a partir de un objeto Question
    (no de un dict), gracias a `from_attributes = True` en su Config."""
    q = Question(
        id=1,
        question="¿Pregunta?",
        answer="Respuesta",
        category="geografía",
        source="wikipedia",
    )
    response = QuestionResponse.model_validate(q)
    assert response.id == 1
    assert response.question == "¿Pregunta?"
    assert response.category == "geografía"


def test_question_response_acepta_category_y_source_none():
    """category y source pueden venir NULL desde la base; el schema debe
    aceptarlos como None sin fallar (son Optional)."""
    q = Question(id=2, question="¿Pregunta?", answer="Respuesta", category=None, source=None)
    response = QuestionResponse.model_validate(q)
    assert response.category is None
    assert response.source is None


def test_question_response_falla_si_falta_id():
    """id es obligatorio en QuestionResponse: un objeto sin id asignado
    (como uno todavía no guardado en la base) debe fallar la validación."""
    q = Question(question="¿Pregunta?", answer="Respuesta")  # id queda None
    with pytest.raises(ValidationError):
        QuestionResponse.model_validate(q)