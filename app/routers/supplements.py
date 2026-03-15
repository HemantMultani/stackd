from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import SupplementLog, ChecklistStatus

router = APIRouter(prefix="/supplements", tags=["supplements"])


@router.patch("/{log_id}/status")
def update_supplement_status(
    log_id: int,
    status: ChecklistStatus,
    session: Session = Depends(get_session)
):
    log = session.get(SupplementLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Supplement log not found")

    log.status = status
    session.add(log)
    session.commit()
    session.refresh(log)
    return {"log_id": log.id, "status": log.status}