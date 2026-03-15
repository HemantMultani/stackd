from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.database import get_session
from app.models import SprintLog, SprintStatus

router = APIRouter(prefix="/sprint", tags=["sprint"])


@router.patch("/{log_id}/status")
def update_sprint_status(
    log_id: int,
    status: SprintStatus,
    session: Session = Depends(get_session)
):
    log = session.get(SprintLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Sprint log not found")

    log.status = status
    session.add(log)
    session.commit()
    session.refresh(log)
    return {"log_id": log.id, "status": log.status}