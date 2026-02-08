from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.constants import DEMO_USER_ID
from app.db.database import get_db
from app.models import User


def get_demo_user(db: Session = Depends(get_db)) -> User:
    user = db.get(User, DEMO_USER_ID)
    if user is None:
        raise RuntimeError("Demo user is not initialized")
    return user
