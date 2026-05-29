from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.database import get_db, engine
from app.models import Base, Question
from app.question_schemas import QuestionCreate, QuestionResponse

app = FastAPI(title="Questions API", version="1.0.0")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {
        "message": "Questions API funcionando",
        "endpoints": [
            "/questions",
            "/questions/{id}",
            "/questions/category/{category}",
            "/stats",
        ]
    }


@app.get("/questions", response_model=List[QuestionResponse])
def list_questions(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    questions = db.query(Question).offset(skip).limit(limit).all()
    return questions


@app.get("/questions/{question_id}", response_model=QuestionResponse)
def get_question(question_id: int, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    return question


# 1

@app.get("/questions/category/{category}", response_model=List[QuestionResponse])
def get_by_category(
    category: str,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Devuelve preguntas de una categoría específica.
    Como el dataset no tiene categorías cargadas, primero creá una pregunta
    con POST /questions asignándole categoría, y después buscala acá.
    """
    questions = (
        db.query(Question)
        .filter(Question.category == category)
        .offset(skip)
        .limit(limit)
        .all()
    )
    if not questions:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron preguntas para la categoría '{category}'"
        )
    return questions


# 2

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """
    Devuelve el total de preguntas y cuántas hay por cada categoría.
    func.count() es el equivalente a COUNT() en SQL puro.
    """
    total = db.query(func.count(Question.id)).scalar()

    by_category = (
        db.query(Question.category, func.count(Question.id))
        .group_by(Question.category)
        .all()
    )

    return {
        "total_questions": total,
        "by_category": [
            {
                "category": cat if cat else "sin categoría",
                "count": count
            }
            for cat, count in by_category
        ]
    }


# 4

@app.post("/questions", response_model=QuestionResponse, status_code=201)
def create_question(data: QuestionCreate, db: Session = Depends(get_db)):
    """
    Crea una pregunta nueva en la DB.
    status_code=201 es el estándar HTTP para 'recurso creado'.
    db.refresh(nueva) recarga el objeto desde la DB para obtener el id asignado.
    """
    nueva = Question(
        question=data.question,
        answer=data.answer,
        category=data.category,
        source=data.source,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva