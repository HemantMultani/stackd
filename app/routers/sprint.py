from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from app.database import get_session
from app.models import SprintLog, SprintStatus

router = APIRouter(prefix="/sprint", tags=["sprint"])
templates = Jinja2Templates(directory="app/templates")


@router.patch("/{log_id}/status", response_class=HTMLResponse)
def update_sprint_status(
    log_id: int,
    status: SprintStatus,
    request: Request,
    session: Session = Depends(get_session)
):
    log = session.get(SprintLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Sprint log not found")

    log.status = status
    session.add(log)
    session.commit()
    session.refresh(log)

    return templates.TemplateResponse("partials/sprint_row.html", {
        "request": request,
        "sprint": log
    })