from pydantic import BaseModel
from typing import Optional


class QuestionCreate(BaseModel):
    """Lo que el usuario manda al crear una pregunta (sin id, lo asigna la DB)."""
    question: str
    answer: str
    category: Optional[str] = None
    source: Optional[str] = None


class QuestionResponse(BaseModel):
    """Lo que la API devuelve (con id incluido)."""
    id: int
    question: str
    answer: str
    category: Optional[str] = None
    source: Optional[str] = None

    class Config:
        from_attributes = True