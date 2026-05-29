import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    """El endpoint raíz devuelve 200 y el mensaje correcto."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Questions API funcionando" in response.json()["message"]


def test_list_questions():
    """Devuelve una lista con hasta 10 preguntas por defecto."""
    response = client.get("/questions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10


def test_list_questions_con_limite():
    """El parámetro limit funciona correctamente."""
    response = client.get("/questions?limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_get_question_existente():
    """Una pregunta con ID válido devuelve 200 y tiene los campos correctos."""
    response = client.get("/questions/3779")
    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert "answer" in data
    assert "id" in data


def test_get_question_inexistente():
    """Un ID que no existe devuelve 404."""
    response = client.get("/questions/999999")
    assert response.status_code == 404


def test_stats():
    """El endpoint de estadísticas devuelve total y desglose por categoría."""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_questions" in data
    assert "by_category" in data
    assert data["total_questions"] > 0


def test_create_question():
    """Crear una pregunta nueva devuelve 201 y la pregunta con ID asignado."""
    nueva = {
        "question": "¿Cuál es la capital de Argentina?",
        "answer": "Buenos Aires",
        "category": "geografía",
        "source": None
    }
    response = client.post("/questions", json=nueva)
    assert response.status_code == 201
    data = response.json()
    assert data["question"] == nueva["question"]
    assert data["answer"] == nueva["answer"]
    assert data["category"] == "geografía"
    assert "id" in data


def test_category_con_datos():
    """Después de crear una pregunta con categoría, el filtro funciona."""
    client.post("/questions", json={
        "question": "¿Cuántos habitantes tiene Brasil?",
        "answer": "215 millones",
        "category": "test-categoria",
        "source": None
    })
    response = client.get("/questions/category/test-categoria")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all(q["category"] == "test-categoria" for q in data)


def test_category_inexistente():
    """Una categoría que no existe devuelve 404."""
    response = client.get("/questions/category/categoria-que-no-existe-jamas")
    assert response.status_code == 404