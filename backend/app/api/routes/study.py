from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.contracts import StudyProgressResponse
from app.services.container import get_study_service
from app.services.study_service import StudyService

router = APIRouter(prefix="/study", tags=["study"])


@router.get("/progress", response_model=StudyProgressResponse)
def progress(
    db: Session = Depends(get_db),
    service: StudyService = Depends(get_study_service),
) -> StudyProgressResponse:
    data = service.get_progress(db=db)
    return StudyProgressResponse(**data)
