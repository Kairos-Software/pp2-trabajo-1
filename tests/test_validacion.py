"""
Tests de VALIDACIÓN

Objetivo: verificar que lo que recibe el USUARIO FINAL de la API es correcto:
status codes esperados, estructura JSON correcta, tipos de datos correctos.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Question

client = TestClient(app)

ID_INEXISTENTE = 999_999_999  # imposible que exista, sin depender del conteo actual


@pytest.fixture
def limpiar_despues():
    """Borra de la base (acceso directo, no hay endpoint DELETE) cualquier
    id que el test registre, al terminar."""
    ids_a_borrar = []
    yield ids_a_borrar
    if ids_a_borrar:
        session = SessionLocal()
        session.query(Question).filter(Question.id.in_(ids_a_borrar)).delete(
            synchronize_session=False
        )
        session.commit()
        session.close()


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

def test_root_estructura_correcta():
    """La respuesta de / debe tener 'message' (string no vacío) y 'endpoints'
    (lista no vacía), tal como espera consumir un cliente de la API."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["message"], str) and len(data["message"]) > 0
    assert isinstance(data["endpoints"], list) and len(data["endpoints"]) > 0


# ---------------------------------------------------------------------------
# GET /questions
# ---------------------------------------------------------------------------

def test_questions_devuelve_lista_con_tipos_correctos():
    """Cada elemento de /questions debe tener exactamente los campos del
    QuestionResponse, con los tipos correctos (id int, question/answer str
    no vacíos, category/source str o None)."""
    response = client.get("/questions?limit=20")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) and len(data) > 0

    for item in data:
        assert set(item.keys()) == {"id", "question", "answer", "category", "source"}
        assert isinstance(item["id"], int)
        assert isinstance(item["question"], str) and len(item["question"]) > 0
        assert isinstance(item["answer"], str) and len(item["answer"]) > 0
        assert item["category"] is None or isinstance(item["category"], str)
        assert item["source"] is None or isinstance(item["source"], str)


def test_questions_paginacion_skip_y_limit_no_se_solapan():
    """skip y limit deben funcionar como paginación real: la página 1 y la
    página 2 no deben compartir ningún id."""
    pagina_1 = client.get("/questions?skip=0&limit=10").json()
    pagina_2 = client.get("/questions?skip=10&limit=10").json()

    ids_1 = {q["id"] for q in pagina_1}
    ids_2 = {q["id"] for q in pagina_2}

    assert len(pagina_1) == 10
    assert len(pagina_2) == 10
    assert ids_1.isdisjoint(ids_2)


def test_questions_limit_cero_devuelve_lista_vacia():
    """limit=0 es un caso límite válido: debe devolver una lista vacía, no
    un error."""
    response = client.get("/questions?limit=0")
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /questions/{id}
# ---------------------------------------------------------------------------

def test_get_question_por_id_real_devuelve_esa_pregunta():
    """Tomamos un id real (consultando /questions) y verificamos que
    /questions/{id} devuelve exactamente esa misma pregunta."""
    alguna = client.get("/questions?limit=1").json()[0]

    response = client.get(f"/questions/{alguna['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == alguna["id"]
    assert data["question"] == alguna["question"]
    assert data["answer"] == alguna["answer"]


def test_get_question_inexistente_devuelve_404_con_mensaje_correcto():
    """Un id que con certeza no existe debe devolver 404 con el detail
    exacto que define la API."""
    response = client.get(f"/questions/{ID_INEXISTENTE}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Pregunta no encontrada"}


def test_get_question_id_no_numerico_devuelve_422():
    """Si el id no es un entero, FastAPI debe rechazarlo en la validación
    del path param (antes de llegar a tocar la base), con 422."""
    response = client.get("/questions/no-soy-un-numero")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /questions
# ---------------------------------------------------------------------------

def test_create_question_devuelve_201_y_la_pregunta_creada(limpiar_despues):
    """Crear una pregunta debe devolver 201 con el mismo contenido enviado
    más un id válido asignado por Postgres."""
    marca = uuid.uuid4().hex[:8]
    nueva = {
        "question": f"¿Pregunta de validación {marca}?",
        "answer": "Respuesta de validación",
        "category": "test-validacion",
        "source": "pytest",
    }

    response = client.post("/questions", json=nueva)
    assert response.status_code == 201
    data = response.json()

    assert isinstance(data["id"], int) and data["id"] > 0
    assert data["question"] == nueva["question"]
    assert data["answer"] == nueva["answer"]
    assert data["category"] == "test-validacion"
    assert data["source"] == "pytest"

    limpiar_despues.append(data["id"])


def test_create_question_sin_campo_obligatorio_devuelve_422():
    """Si falta 'answer' (obligatorio), la API debe rechazar la petición
    con 422 antes de llegar a crear nada en la base."""
    response = client.post("/questions", json={"question": "¿Pregunta incompleta?"})
    assert response.status_code == 422


def test_create_question_sin_category_ni_source_quedan_en_none(limpiar_despues):
    """category y source son opcionales: si no se mandan, deben volver
    como None en la respuesta (y no como string vacío ni faltar la key)."""
    nueva = {"question": "¿Pregunta sin opcionales?", "answer": "Respuesta"}

    response = client.post("/questions", json=nueva)
    assert response.status_code == 201
    data = response.json()
    assert data["category"] is None
    assert data["source"] is None

    limpiar_despues.append(data["id"])


# ---------------------------------------------------------------------------
# GET /questions/category/{category}
# ---------------------------------------------------------------------------

def test_filtro_por_categoria_devuelve_solo_esa_categoria(limpiar_despues):
    """Creamos preguntas con una categoría única y verificamos que el
    endpoint de filtro devuelve únicamente preguntas de esa categoría."""
    categoria = f"test-cat-{uuid.uuid4().hex[:8]}"

    for i in range(2):
        response = client.post(
            "/questions",
            json={"question": f"Pregunta {i}", "answer": f"Respuesta {i}", "category": categoria},
        )
        limpiar_despues.append(response.json()["id"])

    response = client.get(f"/questions/category/{categoria}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(q["category"] == categoria for q in data)


def test_filtro_por_categoria_inexistente_devuelve_404():
    """Una categoría que con certeza no existe debe devolver 404 con el
    mensaje que indica cuál fue la categoría buscada."""
    categoria_inexistente = f"no-existe-{uuid.uuid4().hex[:8]}"
    response = client.get(f"/questions/category/{categoria_inexistente}")
    assert response.status_code == 404
    assert categoria_inexistente in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------

def test_stats_estructura_y_coherencia_de_los_numeros():
    """/stats debe devolver un total > 0 y un desglose por categoría cuya
    suma coincida EXACTAMENTE con el total: si no coinciden, hay un bug
    de lógica aunque el endpoint responda 200 con la estructura 'correcta'."""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["total_questions"], int)
    assert data["total_questions"] > 0
    assert isinstance(data["by_category"], list)

    suma_categorias = sum(c["count"] for c in data["by_category"])
    assert suma_categorias == data["total_questions"]

    for c in data["by_category"]:
        assert isinstance(c["category"], str)
        assert isinstance(c["count"], int) and c["count"] > 0