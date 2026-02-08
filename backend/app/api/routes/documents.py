from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.middleware.error_handler import ApiException
from app.schemas.contracts import DocumentMetaResponse
from app.services.container import get_document_service
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentMetaResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> DocumentMetaResponse:
    try:
        document = await service.create_document(db=db, upload=file)
    except ValueError as exc:
        raise ApiException(code="invalid_document", message=str(exc), status_code=400) from exc
    except RuntimeError as exc:
        raise ApiException(code="processing_failed", message=str(exc), status_code=500) from exc
    return DocumentMetaResponse.model_validate(document)


@router.get("/list", response_model=list[DocumentMetaResponse])
def list_documents(
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> list[DocumentMetaResponse]:
    docs = service.list_documents(db=db)
    return [DocumentMetaResponse.model_validate(doc) for doc in docs]


@router.get("/{doc_id}", response_model=DocumentMetaResponse)
def get_document(
    doc_id: str,
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> DocumentMetaResponse:
    document = service.get_document(db=db, doc_id=doc_id)
    if not document:
        raise ApiException(code="not_found", message="Document not found", status_code=404)
    return DocumentMetaResponse.model_validate(document)


@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> dict[str, bool]:
    deleted = service.delete_document(db=db, doc_id=doc_id)
    if not deleted:
        raise ApiException(code="not_found", message="Document not found", status_code=404)
    return {"ok": True}
