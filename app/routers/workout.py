from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from app.database import get_session
from app.models import WorkoutLog, WorkoutStatus
from datetime import datetime

router = APIRouter(prefix="/workout", tags=["workout"])
templates = Jinja2Templates(directory="app/templates")


@router.patch("/{log_id}/status", response_class=HTMLResponse)
def update_workout_status(
    log_id: int,
    status: WorkoutStatus,
    request: Request,
    session: Session = Depends(get_session)
):
    log = session.get(WorkoutLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Workout log not found")

    log.status = status
    log.updated_at = datetime.utcnow()
    session.add(log)
    session.commit()
    session.refresh(log)

    return templates.TemplateResponse("partials/workout_row.html", {
        "request": request,
        "workout": log
    })