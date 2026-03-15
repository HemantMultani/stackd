from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.database import get_session
from app.models import WorkoutLog, WorkoutStatus

router = APIRouter(prefix="/workout", tags=["workout"])


@router.patch("/{log_id}/status")
def update_workout_status(
    log_id: int,
    status: WorkoutStatus,
    session: Session = Depends(get_session)
):
    log = session.get(WorkoutLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Workout log not found")

    log.status = status
    session.add(log)
    session.commit()
    session.refresh(log)
    return {"log_id": log.id, "status": log.status}