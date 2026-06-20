"""
Tests de SANIDAD (Sanity Testing)

Objetivo: chequeos rápidos y baratos para confirmar que lo más básico
funciona ANTES de correr el resto.
"""

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.database import engine, SessionLocal
from app.models import Question

client = TestClient(app)


def test_la_app_se_importa_y_levanta():
    """La app de FastAPI se pudo importar e instanciar sin explotar
    (si esto falla, ningún otro test va a poder correr)."""
    assert app is not None
    assert app.title == "Questions API"


def test_la_base_de_datos_responde():
    """Postgres está arriba y acepta conexiones. Si esto falla, todos los
    tests de integración/validación van a fallar por la misma razón."""
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1


def test_la_tabla_questions_tiene_datos_cargados():
    """La tabla questions no está vacía: el dataset de Stanford fue cargado
    (load_data.py corrió correctamente en algún momento)."""
    session = SessionLocal()
    try:
        total = session.query(Question).count()
        assert total > 0
    finally:
        session.close()


def test_endpoint_raiz_responde():
    """El endpoint más simple de la API responde 200. Si esto falla, ni
    vale la pena revisar los endpoints más complejos."""
    response = client.get("/")
    assert response.status_code == 200


def test_endpoints_principales_no_devuelven_error_de_servidor():
    """Smoke test: pegarle a los endpoints principales y confirmar que
    ninguno devuelve 5xx (no es un chequeo de contenido, solo de que el
    servidor no se cayó)."""
    for ruta in ("/", "/questions", "/stats"):
        response = client.get(ruta)
        assert response.status_code < 500


def test_documentacion_automatica_disponible():
    """/docs y /openapi.json deben estar disponibles: confirma que FastAPI
    registró las rutas y generó el esquema sin errores de arranque."""
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200