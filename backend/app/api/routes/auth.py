from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_demo_user
from app.core.security import issue_demo_token
from app.db.database import get_db
from app.middleware.error_handler import ApiException
from app.models import User
from app.schemas.contracts import AuthRequest, AuthResponse, UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(payload: AuthRequest, db: Session = Depends(get_db), demo_user: User = Depends(get_demo_user)) -> AuthResponse:
    _ = db
    if payload.email and payload.password:
        return AuthResponse(
            access_token=issue_demo_token(demo_user.id),
            profile=UserProfile(id=demo_user.id, email=demo_user.email, display_name=demo_user.display_name),
        )
    raise ApiException(code="invalid_request", message="Invalid registration payload", status_code=400)


@router.post("/login", response_model=AuthResponse)
def login(payload: AuthRequest, db: Session = Depends(get_db), demo_user: User = Depends(get_demo_user)) -> AuthResponse:
    _ = db
    if payload.email and payload.password:
        return AuthResponse(
            access_token=issue_demo_token(demo_user.id),
            profile=UserProfile(id=demo_user.id, email=demo_user.email, display_name=demo_user.display_name),
        )
    raise ApiException(code="invalid_credentials", message="Invalid credentials", status_code=401)
