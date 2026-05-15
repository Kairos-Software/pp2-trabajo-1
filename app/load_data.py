import pandas as pd
import requests
import tempfile
import os
from app.database import SessionLocal, engine
from app.models import Base, Question

DATASET_URL = "https://huggingface.co/datasets/stanfordnlp/web_questions/resolve/main/data/train-00000-of-00001.parquet"

def download_parquet(url: str) -> str:
    print(f"Descargando {url}...")
    r = requests.get(url, stream=True)
    r.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".parquet")
    tmp.write(r.content)
    tmp.close()
    return tmp.name

def load_questions():
    Base.metadata.create_all(bind=engine)

    parquet_path = download_parquet(DATASET_URL)
    df = pd.read_parquet(parquet_path)
    os.unlink(parquet_path)

    print(f"Columnas disponibles: {list(df.columns)}")
    print(f"Filas: {len(df)}")
    print(df.head(3))

    session = SessionLocal()
    try:
        for _, row in df.iterrows():
            # Convertir 'answers' a string manejando arrays
            answers_val = row['answers']
            if hasattr(answers_val, 'tolist'):  # es array de NumPy
                answers_list = answers_val.tolist()
            elif isinstance(answers_val, list):
                answers_list = answers_val
            else:
                answers_list = [str(answers_val)] if pd.notna(answers_val) else []
            
            answer_text = ", ".join(answers_list) if answers_list else ""

            question = Question(
                question=row['question'],
                answer=answer_text,
                category=None,
                source=row.get('url', None)
            )
            session.add(question)

        session.commit()
        print(f"Se insertaron {len(df)} preguntas correctamente.")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    load_questions()