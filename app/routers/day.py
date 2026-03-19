from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from datetime import date as date_type, timedelta, datetime
from app.database import get_session
from app.models import (
    User, UserGoals, UserWorkoutSchedule, WorkoutTemplate,
    Day, SupplementLog, FoodLog, WorkoutLog, SprintLog,
    Supplement, FoodItem, FoodItemNutrition,
    ChecklistStatus, WorkoutStatus, SprintStatus
)
from app.auth import require_user

router = APIRouter(prefix="/day", tags=["day"])
templates = Jinja2Templates(directory="app/templates")


def get_user_goals(session: Session, user_id: int) -> UserGoals:
    goals = session.exec(
        select(UserGoals).where(UserGoals.user_id == user_id)
    ).first()
    if not goals:
        # Fallback defaults if onboarding was skipped
        goals = UserGoals(user_id=user_id)
        session.add(goals)
        session.commit()
        session.refresh(goals)
    return goals


def get_or_create_today(session: Session, user_id: int) -> Day:
    today = date_type.today()
    day = session.exec(
        select(Day)
        .where(Day.log_date == today)
        .where(Day.user_id == user_id)
    ).first()

    if day:
        return day

    day = Day(log_date=today, user_id=user_id)
    session.add(day)
    session.flush()
    assert day.id is not None

    # Supplements — only active ones
    supplements = session.exec(
        select(Supplement)
        .where(Supplement.user_id == user_id)
        .where(Supplement.active == True)
    ).all()
    for sup in supplements:
        session.add(SupplementLog(day_id=day.id, supplement_id=sup.id))

    # Food items — only active ones
    food_items = session.exec(
        select(FoodItem)
        .where(FoodItem.user_id == user_id)
        .where(FoodItem.active == True)
    ).all()
    for item in food_items:
        session.add(FoodLog(day_id=day.id, food_item_id=item.id))

    # Workout — look up schedule for today's weekday
    # No calendar-week derivation — explicit user config only
    weekday = today.weekday()
    schedule_slot = session.exec(
        select(UserWorkoutSchedule)
        .where(UserWorkoutSchedule.user_id == user_id)
        .where(UserWorkoutSchedule.weekday == weekday)
    ).first()

    if schedule_slot:
        session.add(WorkoutLog(
            day_id=day.id,
            workout_template_id=schedule_slot.workout_template_id,
            status=WorkoutStatus.pending
        ))

    # Sprint — every day
    session.add(SprintLog(day_id=day.id, duration_minutes=10))

    session.commit()
    session.refresh(day)
    return day


def compute_weekly_stats(session: Session, user: User) -> dict:
    goals = get_user_goals(session, user.id)
    today = date_type.today()
    monday = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]
    past_dates = [d for d in week_dates if d <= today]

    sprint_done = 0
    workout_done = 0
    workout_scheduled = 0
    protein_met = 0
    sup_pcts = []

    # Fetch scheduled workout weekdays for this user
    schedule = session.exec(
        select(UserWorkoutSchedule)
        .where(UserWorkoutSchedule.user_id == user.id)
    ).all()
    scheduled_weekdays = {s.weekday for s in schedule}

    for d in past_dates:
        day = session.exec(
            select(Day)
            .where(Day.log_date == d)
            .where(Day.user_id == user.id)
        ).first()
        if not day:
            continue

        sprint = session.exec(
            select(SprintLog).where(SprintLog.day_id == day.id)
        ).first()
        if sprint and sprint.status == SprintStatus.done:
            sprint_done += 1

        workout = session.exec(
            select(WorkoutLog).where(WorkoutLog.day_id == day.id)
        ).first()
        if workout:
            workout_scheduled += 1
            if workout.status == WorkoutStatus.done:
                workout_done += 1

        # Protein — join through FoodItemNutrition
        food_logs = session.exec(
            select(FoodLog, FoodItem, FoodItemNutrition)
            .where(FoodLog.day_id == day.id)
            .where(FoodLog.food_item_id == FoodItem.id)
            .where(FoodItemNutrition.food_item_id == FoodItem.id)
        ).all()
        protein = sum(
            n.protein_grams or 0
            for _, _, n in food_logs
            if food_logs and _
            # only eaten items
        )
        # Recalculate correctly
        protein = 0
        for log, item, nutrition in food_logs:
            if log.eaten and nutrition and nutrition.protein_grams:
                protein += nutrition.protein_grams

        if protein >= goals.protein_goal_grams:
            protein_met += 1

        sup_logs = session.exec(
            select(SupplementLog).where(SupplementLog.day_id == day.id)
        ).all()
        if sup_logs:
            pct = int(
                sum(1 for s in sup_logs
                    if s.status == ChecklistStatus.done)
                / len(sup_logs) * 100
            )
            sup_pcts.append(pct)

    days_elapsed = len(past_dates)
    sup_avg = int(sum(sup_pcts) / len(sup_pcts)) if sup_pcts else 0
    workout_target = sum(
        1 for d in past_dates if d.weekday() in scheduled_weekdays
    )

    return {
        "sprint_done": sprint_done,
        "sprint_target": min(days_elapsed, goals.sprint_sessions_per_week),
        "sprint_pct": min(int(
            sprint_done / max(goals.sprint_sessions_per_week, 1) * 100
        ), 100),
        "workout_done": workout_done,
        "workout_target": workout_target,
        "workout_pct": min(int(
            workout_done / max(workout_target, 1) * 100
        ), 100),
        "protein_met": protein_met,
        "protein_target": days_elapsed,
        "protein_pct": min(int(
            protein_met / max(days_elapsed, 1) * 100
        ), 100),
        "sup_avg": sup_avg,
        "sup_pct": sup_avg,
        "days_elapsed": days_elapsed,
        "monday": monday,
    }


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request,
              session: Session = Depends(get_session)):
    user = require_user(request, session)
    goals = get_user_goals(session, user.id)
    day = get_or_create_today(session, user.id)

    sup_logs = session.exec(
        select(SupplementLog, Supplement)
        .where(SupplementLog.day_id == day.id)
        .where(SupplementLog.supplement_id == Supplement.id)
    ).all()

    # Food logs joined with nutrition
    food_data = session.exec(
        select(FoodLog, FoodItem, FoodItemNutrition)
        .where(FoodLog.day_id == day.id)
        .where(FoodLog.food_item_id == FoodItem.id)
        .where(FoodItemNutrition.food_item_id == FoodItem.id)
    ).all()

    protein_eaten = int(sum(
        n.protein_grams or 0
        for log, item, n in food_data
        if log.eaten
    ))
    protein_goal = goals.protein_goal_grams
    protein_pct = min(int((protein_eaten / max(protein_goal, 1)) * 100), 100)

    # Workout with template name
    workout_row = session.exec(
        select(WorkoutLog, WorkoutTemplate)
        .where(WorkoutLog.day_id == day.id)
        .where(WorkoutLog.workout_template_id == WorkoutTemplate.id)
    ).first()

    sprint = session.exec(
        select(SprintLog).where(SprintLog.day_id == day.id)
    ).first()

    weekly = compute_weekly_stats(session, user)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "day": day,
        "sup_logs": [
            {"log": log, "sup": sup} for log, sup in sup_logs
        ],
        "food_logs": [
            {"log": log, "item": item, "nutrition": nutrition}
            for log, item, nutrition in food_data
        ],
        "protein_eaten": protein_eaten,
        "protein_goal": protein_goal,
        "protein_pct": protein_pct,
        "workout": workout_row[0] if workout_row else None,
        "workout_template": workout_row[1] if workout_row else None,
        "sprint": sprint,
        "weekly": weekly,
    })


@router.get("/protein-bar", response_class=HTMLResponse)
def protein_bar(request: Request,
                session: Session = Depends(get_session)):
    user = require_user(request, session)
    goals = get_user_goals(session, user.id)
    day = get_or_create_today(session, user.id)

    food_data = session.exec(
        select(FoodLog, FoodItem, FoodItemNutrition)
        .where(FoodLog.day_id == day.id)
        .where(FoodLog.food_item_id == FoodItem.id)
        .where(FoodItemNutrition.food_item_id == FoodItem.id)
    ).all()

    protein_eaten = int(sum(
        n.protein_grams or 0
        for log, item, n in food_data
        if log.eaten
    ))
    protein_pct = min(
        int((protein_eaten / max(goals.protein_goal_grams, 1)) * 100), 100
    )

    return templates.TemplateResponse("partials/protein_bar.html", {
        "request": request,
        "protein_eaten": protein_eaten,
        "protein_goal": goals.protein_goal_grams,
        "protein_pct": protein_pct,
    })


@router.get("/week", response_class=HTMLResponse)
def weekly_summary(request: Request,
                   session: Session = Depends(get_session)):
    user = require_user(request, session)
    goals = get_user_goals(session, user.id)
    today = date_type.today()
    monday = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]

    days_data = []
    for d in week_dates:
        day = session.exec(
            select(Day)
            .where(Day.log_date == d)
            .where(Day.user_id == user.id)
        ).first()

        if not day:
            days_data.append({
                "date": d, "exists": False, "is_future": d > today
            })
            continue

        sup_logs = session.exec(
            select(SupplementLog)
            .where(SupplementLog.day_id == day.id)
        ).all()

        food_data = session.exec(
            select(FoodLog, FoodItem, FoodItemNutrition)
            .where(FoodLog.day_id == day.id)
            .where(FoodLog.food_item_id == FoodItem.id)
            .where(FoodItemNutrition.food_item_id == FoodItem.id)
        ).all()
        protein_eaten = int(sum(
            n.protein_grams or 0
            for log, item, n in food_data
            if log.eaten
        ))

        workout = session.exec(
            select(WorkoutLog).where(WorkoutLog.day_id == day.id)
        ).first()
        sprint = session.exec(
            select(SprintLog).where(SprintLog.day_id == day.id)
        ).first()

        days_data.append({
            "date": d,
            "exists": True,
            "is_future": d > today,
            "is_today": d == today,
            "sup_done": sum(
                1 for s in sup_logs
                if s.status == ChecklistStatus.done
            ),
            "sup_total": len(sup_logs),
            "protein_eaten": protein_eaten,
            "protein_met": protein_eaten >= goals.protein_goal_grams,
            "workout_status": workout.status.value if workout else None,
            "workout_scheduled": workout is not None,
            "sprint_status": sprint.status.value if sprint else None,
        })

    weekly = compute_weekly_stats(session, user)

    return templates.TemplateResponse("week.html", {
        "request": request,
        "user": user,
        "week_dates": week_dates,
        "days_data": days_data,
        "today": today,
        "monday": monday,
        "timedelta": timedelta,
        "weekly": weekly,
        "protein_goal": goals.protein_goal_grams,
    })