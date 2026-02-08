from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.constants import DEMO_DISPLAY_NAME, DEMO_EMAIL, DEMO_USER_ID
from app.db.database import Base, engine
from app.models import StudyProgress, User


def create_all() -> None:
    Base.metadata.create_all(bind=engine)


def ensure_fts(session: Session) -> None:
    session.execute(
        text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts
            USING fts5(chunk_text, doc_id UNINDEXED, chunk_index UNINDEXED, content='document_chunks', content_rowid='rowid');
            """
        )
    )

    session.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS document_chunks_ai AFTER INSERT ON document_chunks BEGIN
              INSERT INTO document_chunks_fts(rowid, chunk_text, doc_id, chunk_index)
              VALUES (new.rowid, new.chunk_text, new.doc_id, new.chunk_index);
            END;
            """
        )
    )
    session.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS document_chunks_ad AFTER DELETE ON document_chunks BEGIN
              INSERT INTO document_chunks_fts(document_chunks_fts, rowid, chunk_text, doc_id, chunk_index)
              VALUES('delete', old.rowid, old.chunk_text, old.doc_id, old.chunk_index);
            END;
            """
        )
    )
    session.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS document_chunks_au AFTER UPDATE ON document_chunks BEGIN
              INSERT INTO document_chunks_fts(document_chunks_fts, rowid, chunk_text, doc_id, chunk_index)
              VALUES('delete', old.rowid, old.chunk_text, old.doc_id, old.chunk_index);
              INSERT INTO document_chunks_fts(rowid, chunk_text, doc_id, chunk_index)
              VALUES(new.rowid, new.chunk_text, new.doc_id, new.chunk_index);
            END;
            """
        )
    )
    session.commit()


def seed_demo_user(session: Session) -> None:
    existing = session.get(User, DEMO_USER_ID)
    if existing is None:
        session.add(
            User(
                id=DEMO_USER_ID,
                email=DEMO_EMAIL,
                display_name=DEMO_DISPLAY_NAME,
                password_hash=None,
            )
        )
        session.add(
            StudyProgress(
                user_id=DEMO_USER_ID,
                cards_reviewed_today=0,
                total_reviews=0,
                average_score=0.0,
            )
        )
        session.commit()
