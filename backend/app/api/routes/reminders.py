from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.middleware.error_handler import ApiException
from app.schemas.contracts import ReminderCreateRequest, ReminderResponse, ReminderUpdateRequest
from app.services.container import get_reminder_service
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/reminders", tags=["reminders"])


def _to_response(service: ReminderService, reminder) -> ReminderResponse:
    return ReminderResponse(
        id=reminder.id,
        title=reminder.title,
        note=reminder.note,
        scheduled_for=reminder.scheduled_for,
        completed=reminder.completed,
        created_at=reminder.created_at,
        updated_at=reminder.updated_at,
        due_now=service.is_due(reminder),
    )


@router.post("/create", response_model=ReminderResponse)
def create_reminder(
    payload: ReminderCreateRequest,
    db: Session = Depends(get_db),
    service: ReminderService = Depends(get_reminder_service),
) -> ReminderResponse:
    reminder = service.create(db=db, title=payload.title, note=payload.note, scheduled_for=payload.scheduled_for)
    return _to_response(service, reminder)


@router.get("/list", response_model=list[ReminderResponse])
def list_reminders(
    db: Session = Depends(get_db),
    service: ReminderService = Depends(get_reminder_service),
) -> list[ReminderResponse]:
    reminders = service.list(db=db)
    return [_to_response(service, reminder) for reminder in reminders]


@router.put("/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
    reminder_id: str,
    payload: ReminderUpdateRequest,
    db: Session = Depends(get_db),
    service: ReminderService = Depends(get_reminder_service),
) -> ReminderResponse:
    reminder = service.get(db=db, reminder_id=reminder_id)
    if not reminder:
        raise ApiException(code="not_found", message="Reminder not found", status_code=404)
    reminder = service.update(
        db=db,
        reminder=reminder,
        title=payload.title,
        note=payload.note,
        scheduled_for=payload.scheduled_for,
        completed=payload.completed,
    )
    return _to_response(service, reminder)


@router.delete("/{reminder_id}")
def delete_reminder(
    reminder_id: str,
    db: Session = Depends(get_db),
    service: ReminderService = Depends(get_reminder_service),
) -> dict[str, bool]:
    reminder = service.get(db=db, reminder_id=reminder_id)
    if not reminder:
        raise ApiException(code="not_found", message="Reminder not found", status_code=404)
    service.delete(db=db, reminder=reminder)
    return {"ok": True}
