from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from datetime import date as date_type, timedelta, datetime
from typing import List, Optional
from app.database import get_session
from app.models import (User, Supplement, FoodItem, Oath, OathMilestone,
                        SupplementTime, MealTime, OathStatus, WorkoutType)
from app.auth import require_user

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def onboarding_start(request: Request,
                     session: Session = Depends(get_session)):
    user = require_user(request, session)
    return templates.TemplateResponse("onboarding/start.html", {
        "request": request, "user": user
    })


@router.get("/persona", response_class=HTMLResponse)
def persona_page(request: Request,
                 session: Session = Depends(get_session)):
    user = require_user(request, session)
    return templates.TemplateResponse("onboarding/persona.html", {
        "request": request,
        "user": user,
        "workout_types": [w.value for w in WorkoutType]
    })


@router.post("/persona")
def save_persona(
    request: Request,
    display_name: str = Form(...),
    protein_goal: int = Form(100),
    sprint_target: int = Form(5),
    workout_days: str = Form(""),
    workout_split_a: str = Form("upper_body"),
    workout_split_b: str = Form("lower_body"),
    session: Session = Depends(get_session)
):
    user = require_user(request, session)

    # Validate ranges
    if not 50 <= protein_goal <= 400:
        return templates.TemplateResponse("onboarding/persona.html", {
            "request": request, "user": user,
            "error": "Protein goal must be between 50 and 400g",
            "workout_types": [w.value for w in WorkoutType]
        })

    if not 1 <= sprint_target <= 7:
        return templates.TemplateResponse("onboarding/persona.html", {
            "request": request, "user": user,
            "error": "Sprint target must be between 1 and 7",
            "workout_types": [w.value for w in WorkoutType]
        })

    # Parse workout days from comma-separated string to JSON list
    try:
        days_list = [int(d) for d in workout_days.split(",") if d.strip()]
        days_list = [d for d in days_list if 0 <= d <= 6]
    except ValueError:
        days_list = [0, 1, 2, 3]

    user.display_name = display_name.strip()
    user.protein_goal = protein_goal
    user.sprint_target = sprint_target
    user.workout_days = days_list           # stored as JSON list
    user.workout_split_a = workout_split_a  # explicit, never derived
    user.workout_split_b = workout_split_b
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    return RedirectResponse(url="/onboarding/supplements", status_code=302)


@router.get("/supplements", response_class=HTMLResponse)
def supplements_page(request: Request,
                     session: Session = Depends(get_session)):
    user = require_user(request, session)
    return templates.TemplateResponse("onboarding/supplements.html", {
        "request": request,
        "user": user,
        "times": [t.value for t in SupplementTime]
    })


@router.post("/supplements")
def save_supplements(
    request: Request,
    names: List[str] = Form(...),
    times: List[str] = Form(...),
    notes: List[str] = Form(default=[]),
    session: Session = Depends(get_session)
):
    user = require_user(request, session)
    assert user.id is not None

    saved = 0
    for i, name in enumerate(names):
        if not name.strip():
            continue
        try:
            scheduled_time = SupplementTime(times[i])
        except (ValueError, IndexError):
            continue
        sup = Supplement(
            user_id=user.id,
            name=name.strip(),
            scheduled_time=scheduled_time,
            notes=notes[i].strip() if i < len(notes) and notes[i] else None
        )
        session.add(sup)
        saved += 1

    if saved == 0:
        # Allow skipping — not everyone tracks supplements
        session.commit()
    else:
        session.commit()

    return RedirectResponse(url="/onboarding/food", status_code=302)


@router.get("/food", response_class=HTMLResponse)
def food_page(request: Request,
              session: Session = Depends(get_session)):
    user = require_user(request, session)
    return templates.TemplateResponse("onboarding/food.html", {
        "request": request,
        "user": user,
        "meal_times": [m.value for m in MealTime]
    })


@router.post("/food")
def save_food(
    request: Request,
    names: List[str] = Form(...),
    proteins: List[str] = Form(...),   # strings for safe parsing
    meal_times: List[str] = Form(...),
    session: Session = Depends(get_session)
):
    user = require_user(request, session)
    assert user.id is not None

    for i, name in enumerate(names):
        if not name.strip():
            continue
        try:
            protein = float(proteins[i])
            if protein < 0 or protein > 500:
                continue
            meal_time = MealTime(meal_times[i])
        except (ValueError, IndexError):
            continue

        item = FoodItem(
            user_id=user.id,
            name=name.strip(),
            protein_grams=protein,
            meal_time=meal_time
        )
        session.add(item)

    session.commit()
    return RedirectResponse(url="/onboarding/oath", status_code=302)


@router.get("/oath", response_class=HTMLResponse)
def oath_page(request: Request,
              session: Session = Depends(get_session)):
    user = require_user(request, session)
    return templates.TemplateResponse("onboarding/oath.html", {
        "request": request, "user": user
    })


@router.post("/oath")
def save_oath(
    request: Request,
    title: str = Form(...),
    intention: str = Form(...),
    duration_days: int = Form(180),
    milestone_1: str = Form(""),
    milestone_2: str = Form(""),
    milestone_3: str = Form(""),
    session: Session = Depends(get_session)
):
    user = require_user(request, session)
    assert user.id is not None

    # Validate duration
    if not 30 <= duration_days <= 365:
        duration_days = 180

    start = date_type.today()
    oath = Oath(
        user_id=user.id,
        title=title.strip(),
        intention=intention.strip(),
        start_date=start,
        end_date=start + timedelta(days=duration_days),
        status=OathStatus.active
    )
    session.add(oath)
    session.flush()
    assert oath.id is not None

    for m_title in [milestone_1, milestone_2, milestone_3]:
        if m_title.strip():
            session.add(OathMilestone(
                oath_id=oath.id,
                title=m_title.strip(),
                target_date=start + timedelta(days=duration_days // 2)
            ))

    session.commit()
    return RedirectResponse(url="/day/", status_code=302)