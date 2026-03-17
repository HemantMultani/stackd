from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from datetime import date as date_type
from app.database import get_session
from app.models import Oath, OathMilestone

router = APIRouter(prefix="/oath", tags=["oath"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def oath_page(request: Request, session: Session = Depends(get_session)):
    oath = session.exec(select(Oath)).first()
    if not oath:
        raise HTTPException(status_code=404, detail="No oath found")

    milestones = session.exec(
        select(OathMilestone).where(OathMilestone.oath_id == oath.id)
    ).all()

    today = date_type.today()
    days_elapsed = (today - oath.start_date).days
    days_total = (oath.end_date - oath.start_date).days
    days_remaining = max((oath.end_date - today).days, 0)
    pct = min(int((days_elapsed / days_total) * 100), 100)

    return templates.TemplateResponse("oath.html", {
        "request": request,
        "oath": oath,
        "milestones": milestones,
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "days_total": days_total,
        "pct": pct,
        "today": today,
    })


@router.patch("/milestones/{milestone_id}/complete",
              response_class=HTMLResponse)
def complete_milestone(
    milestone_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    m = session.get(OathMilestone, milestone_id)
    if not m:
        raise HTTPException(status_code=404, detail="Milestone not found")

    m.completed = not m.completed
    m.completed_date = date_type.today() if m.completed else None
    session.add(m)
    session.commit()
    session.refresh(m)

    return templates.TemplateResponse("partials/milestone_row.html", {
        "request": request,
        "m": m,
    })