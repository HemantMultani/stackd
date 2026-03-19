from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database import get_session
from app.models import SupplementLog, Supplement, ChecklistStatus
from datetime import datetime

router = APIRouter(prefix="/supplements", tags=["supplements"])
templates = Jinja2Templates(directory="app/templates")


@router.patch("/{log_id}/status", response_class=HTMLResponse)
def update_supplement_status(
    log_id: int,
    status: ChecklistStatus,
    request: Request,
    session: Session = Depends(get_session)
):
    log = session.get(SupplementLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Supplement log not found")

    log.status = status
    log.updated_at = datetime.utcnow()
    session.add(log)
    session.commit()
    session.refresh(log)

    sup = session.get(Supplement, log.supplement_id)

    return templates.TemplateResponse("partials/sup_row.html", {
        "request": request,
        "entry": {"log": log, "sup": sup}
    })