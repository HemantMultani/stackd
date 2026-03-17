from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database import get_session
from app.models import FoodLog, FoodItem, Day
from datetime import date as date_type

router = APIRouter(prefix="/food", tags=["food"])
templates = Jinja2Templates(directory="app/templates")

PROTEIN_GOAL = 100


@router.patch("/{log_id}/eaten", response_class=HTMLResponse)
def mark_food_eaten(
    log_id: int,
    eaten: bool,
    request: Request,
    session: Session = Depends(get_session)
):
    log = session.get(FoodLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Food log not found")

    log.eaten = eaten
    session.add(log)
    session.commit()
    session.refresh(log)

    item = session.get(FoodItem, log.food_item_id)

    # Recompute protein across all food logs for today
    today = date_type.today()
    day = session.exec(
        select(Day).where(Day.log_date == today)
    ).first()

    all_food_logs = session.exec(
        select(FoodLog, FoodItem)
        .where(FoodLog.day_id == day.id)
        .where(FoodLog.food_item_id == FoodItem.id)
    ).all()

    protein_eaten = int(sum(i.protein_grams for l, i in all_food_logs if l.eaten))
    protein_pct = min(int((protein_eaten / PROTEIN_GOAL) * 100), 100)

    # Render both partials and concatenate — HTMX picks each by ID
    food_row_html = templates.TemplateResponse("partials/food_row.html", {
        "request": request,
        "entry": {"log": log, "item": item}
    }).body.decode()

    protein_bar_html = templates.TemplateResponse("partials/protein_bar.html", {
        "request": request,
        "protein_eaten": protein_eaten,
        "protein_goal": PROTEIN_GOAL,
        "protein_pct": protein_pct,
    }).body.decode()

    return HTMLResponse(content=food_row_html + protein_bar_html)