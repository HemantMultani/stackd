from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from datetime import date as date_type, datetime
from app.database import get_session
from app.models import (
    FoodLog, FoodItem, FoodItemNutrition,
    Day, UserGoals
)
from app.auth import require_user

router = APIRouter(prefix="/food", tags=["food"])
templates = Jinja2Templates(directory="app/templates")


@router.patch("/{log_id}/eaten", response_class=HTMLResponse)
def mark_food_eaten(
    log_id: int,
    eaten: bool,
    request: Request,
    session: Session = Depends(get_session)
):
    user = require_user(request, session)

    log = session.get(FoodLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Food log not found")

    log.eaten = eaten
    log.updated_at = datetime.utcnow()
    session.add(log)
    session.commit()
    session.refresh(log)

    item = session.get(FoodItem, log.food_item_id)
    nutrition = session.exec(
        select(FoodItemNutrition)
        .where(FoodItemNutrition.food_item_id == item.id)
    ).first()

    # Recompute protein for OOB protein bar update
    today = date_type.today()
    day = session.exec(
        select(Day)
        .where(Day.log_date == today)
        .where(Day.user_id == user.id)
    ).first()

    goals = session.exec(
        select(UserGoals).where(UserGoals.user_id == user.id)
    ).first()

    food_data = session.exec(
        select(FoodLog, FoodItem, FoodItemNutrition)
        .where(FoodLog.day_id == day.id)
        .where(FoodLog.food_item_id == FoodItem.id)
        .where(FoodItemNutrition.food_item_id == FoodItem.id)
    ).all()

    protein_eaten = int(sum(
        n.protein_grams or 0
        for l, i, n in food_data
        if l.eaten
    ))
    protein_goal = goals.protein_goal_grams if goals else 100
    protein_pct = min(int((protein_eaten / max(protein_goal, 1)) * 100), 100)

    food_row_html = templates.TemplateResponse(
        "partials/food_row.html", {
            "request": request,
            "entry": {"log": log, "item": item, "nutrition": nutrition}
        }
    ).body.decode()

    protein_bar_html = templates.TemplateResponse(
        "partials/protein_bar.html", {
            "request": request,
            "protein_eaten": protein_eaten,
            "protein_goal": protein_goal,
            "protein_pct": protein_pct,
        }
    ).body.decode()

    return HTMLResponse(content=food_row_html + protein_bar_html)