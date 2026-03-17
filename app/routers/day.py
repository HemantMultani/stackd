import os
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import date as date_type, timedelta
from typing import Optional
from app.database import get_session
from app.models import (
    Day, SupplementLog, FoodLog, WorkoutLog, SprintLog,
    Supplement, FoodItem, WorkoutType,
    ChecklistStatus, WorkoutStatus, SprintStatus
)
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/day", tags=["day"])

PROTEIN_GOAL = int(os.getenv("PROTEIN_GOAL", "100"))


def get_or_create_today(session: Session) -> Day:
    today = date_type.today()
    day = session.exec(select(Day).where(Day.log_date == today)).first()

    if day:
        return day

    # First visit of the day — bootstrap everything
    day = Day(log_date=today)
    session.add(day)
    session.flush()  # get day.id before creating logs
    assert day.id is not None  # flush guarantees this, assert makes type checker happy

    # Create supplement logs from master list
    supplements = session.exec(select(Supplement)).all()
    for sup in supplements:
        assert sup.id is not None  # flush guarantees this, assert makes type checker happy
        session.add(SupplementLog(day_id=day.id, supplement_id=sup.id))

    # Create food logs from master list
    food_items = session.exec(select(FoodItem)).all()
    for item in food_items:
        assert item.id is not None  # flush guarantees this, assert makes type checker happy
        session.add(FoodLog(day_id=day.id, food_item_id=item.id))

    # Create workout log based on day of week
    # Mon=0, Tue=1, Wed=2, Thu=3 get a workout slot
    weekday = today.weekday()
    if weekday in (0, 1, 2, 3):
        # Alternate upper/lower body — even weeks upper on Mon/Wed, lower Tue/Thu
        week_number = today.isocalendar()[1]
        if weekday in (0, 2):
            wtype = WorkoutType.upper_body if week_number % 2 == 0 else WorkoutType.lower_body
        else:
            wtype = WorkoutType.lower_body if week_number % 2 == 0 else WorkoutType.upper_body
        session.add(WorkoutLog(day_id=day.id, workout_type=wtype))

    # Sprint log — every day
    session.add(SprintLog(day_id=day.id, duration_minutes=10))

    session.commit()
    session.refresh(day)
    return day

@router.get("/today")
def get_today(session: Session = Depends(get_session)):
    day = get_or_create_today(session)

    # Fetch supplement logs with supplement details
    sup_logs = session.exec(
        select(SupplementLog, Supplement)
        .where(SupplementLog.day_id == day.id)
        .where(SupplementLog.supplement_id == Supplement.id)
    ).all()

    # Fetch food logs with food item details
    food_logs = session.exec(
        select(FoodLog, FoodItem)
        .where(FoodLog.day_id == day.id)
        .where(FoodLog.food_item_id == FoodItem.id)
    ).all()

    # Compute protein
    protein_eaten = sum(
        item.protein_grams for log, item in food_logs if log.eaten
    )

    # Fetch workout log
    workout = session.exec(
        select(WorkoutLog).where(WorkoutLog.day_id == day.id)
    ).first()

    # Fetch sprint log
    sprint = session.exec(
        select(SprintLog).where(SprintLog.day_id == day.id)
    ).first()

    return {
        "date": day.log_date,
        "supplements": [
            {
                "log_id": log.id,
                "name": sup.name,
                "scheduled_time": sup.scheduled_time,
                "notes": sup.notes,
                "status": log.status,
            }
            for log, sup in sup_logs
        ],
        "food": {
            "items": [
                {
                    "log_id": log.id,
                    "name": item.name,
                    "protein_grams": item.protein_grams,
                    "meal_time": item.meal_time,
                    "eaten": log.eaten,
                }
                for log, item in food_logs
            ],
            "protein_eaten": protein_eaten,
            "protein_goal": PROTEIN_GOAL,
            "protein_goal_met": protein_eaten >= PROTEIN_GOAL,
        },
        "workout": {
            "log_id": workout.id if workout else None,
            "type": workout.workout_type if workout else None,
            "status": workout.status if workout else None,
            "scheduled": workout is not None,
        },
        "sprint": {
            "log_id": sprint.id if sprint else None,
            "duration_minutes": sprint.duration_minutes if sprint else None,
            "status": sprint.status if sprint else None,
        }
    }


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_session)):
    day = get_or_create_today(session)

    sup_logs = session.exec(
        select(SupplementLog, Supplement)
        .where(SupplementLog.day_id == day.id)
        .where(SupplementLog.supplement_id == Supplement.id)
    ).all()

    food_logs = session.exec(
        select(FoodLog, FoodItem)
        .where(FoodLog.day_id == day.id)
        .where(FoodLog.food_item_id == FoodItem.id)
    ).all()

    protein_eaten = sum(
        item.protein_grams for log, item in food_logs if log.eaten
    )

    workout = session.exec(
        select(WorkoutLog).where(WorkoutLog.day_id == day.id)
    ).first()

    sprint = session.exec(
        select(SprintLog).where(SprintLog.day_id == day.id)
    ).first()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "day": day,
        "sup_logs": [{"log": log, "sup": sup} for log, sup in sup_logs],
        "food_logs": [{"log": log, "item": item} for log, item in food_logs],
        "protein_eaten": int(protein_eaten),
        "protein_goal": PROTEIN_GOAL,
        "protein_pct": min(int((protein_eaten / PROTEIN_GOAL) * 100), 100),
        "workout": workout,
        "sprint": sprint,
    })

@router.get("/protein-bar", response_class=HTMLResponse)
def protein_bar(request: Request, session: Session = Depends(get_session)):
    day = get_or_create_today(session)

    food_logs = session.exec(
        select(FoodLog, FoodItem)
        .where(FoodLog.day_id == day.id)
        .where(FoodLog.food_item_id == FoodItem.id)
    ).all()

    protein_eaten = int(sum(item.protein_grams for log, item in food_logs if log.eaten))
    protein_pct = min(int((protein_eaten / PROTEIN_GOAL) * 100), 100)

    return templates.TemplateResponse("partials/protein_bar.html", {
        "request": request,
        "protein_eaten": protein_eaten,
        "protein_goal": PROTEIN_GOAL,
        "protein_pct": protein_pct,
    })

@router.get("/week", response_class=HTMLResponse)
def weekly_summary(request: Request, session: Session = Depends(get_session)):
    today = date_type.today()
    # Week starts Monday
    monday = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]

    days_data = []
    for d in week_dates:
        day = session.exec(select(Day).where(Day.log_date == d)).first()
        if not day:
            days_data.append({
                "date": d,
                "exists": False,
                "is_future": d > today,
            })
            continue

        # Supplements
        sup_logs = session.exec(
            select(SupplementLog).where(SupplementLog.day_id == day.id)
        ).all()
        sup_done = sum(1 for s in sup_logs if s.status == ChecklistStatus.done)
        sup_total = len(sup_logs)

        # Food + protein
        food_logs = session.exec(
            select(FoodLog, FoodItem)
            .where(FoodLog.day_id == day.id)
            .where(FoodLog.food_item_id == FoodItem.id)
        ).all()
        protein_eaten = int(sum(i.protein_grams for l, i in food_logs if l.eaten))
        protein_met = protein_eaten >= PROTEIN_GOAL

        # Workout
        workout = session.exec(
            select(WorkoutLog).where(WorkoutLog.day_id == day.id)
        ).first()

        # Sprint
        sprint = session.exec(
            select(SprintLog).where(SprintLog.day_id == day.id)
        ).first()

        days_data.append({
            "date": d,
            "exists": True,
            "is_future": d > today,
            "is_today": d == today,
            "sup_done": sup_done,
            "sup_total": sup_total,
            "protein_eaten": protein_eaten,
            "protein_met": protein_met,
            "workout_status": workout.status.value if workout else None,
            "workout_scheduled": workout is not None,
            "sprint_status": sprint.status.value if sprint else None,
        })

    # Week-level stats
    past_days = [d for d in days_data if d["exists"] and not d["is_future"]]
    protein_met_count = sum(1 for d in past_days if d.get("protein_met"))
    sprint_done_count = sum(1 for d in past_days if d.get("sprint_status") == "done")
    workout_done_count = sum(1 for d in past_days if d.get("workout_status") == "done")
    workout_scheduled_count = sum(1 for d in past_days if d.get("workout_scheduled"))
    sup_completion = 0
    if past_days:
        sup_completion = int(sum(
            (d["sup_done"] / d["sup_total"] * 100) if d["sup_total"] else 0
            for d in past_days
        ) / len(past_days))

    return templates.TemplateResponse("week.html", {
        "request": request,
        "week_dates": week_dates,
        "days_data": days_data,
        "today": today,
        "monday": monday,
        "timedelta": timedelta,
        "protein_met_count": protein_met_count,
        "sprint_done_count": sprint_done_count,
        "workout_done_count": workout_done_count,
        "workout_scheduled_count": workout_scheduled_count,
        "sup_completion": sup_completion,
        "protein_goal": PROTEIN_GOAL,
    })