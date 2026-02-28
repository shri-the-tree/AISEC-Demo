from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.routes import router
from app.config import settings
from app.db.models import Base
from app.db.repository import Repository
from app.db.session import SessionLocal, engine


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(router)


@app.on_event('startup')
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    # Add tool_calls_json column to existing DBs that pre-date this migration
    with engine.connect() as conn:
        existing_cols = [c['name'] for c in inspect(engine).get_columns('messages')]
        if 'tool_calls_json' not in existing_cols:
            conn.execute(text('ALTER TABLE messages ADD COLUMN tool_calls_json TEXT'))
            conn.commit()
    db = SessionLocal()
    try:
        repo = Repository(db)
        repo.seed_patients()
    finally:
        db.close()
