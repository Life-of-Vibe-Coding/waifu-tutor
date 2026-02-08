from fastapi import APIRouter, Depends

from app.api.deps import get_demo_user
from app.models import User
from app.schemas.contracts import UserProfile

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile", response_model=UserProfile)
def profile(user: User = Depends(get_demo_user)) -> UserProfile:
    return UserProfile(id=user.id, email=user.email, display_name=user.display_name)
