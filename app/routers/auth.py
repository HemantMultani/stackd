from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database import get_session
from app.models import User
from app.auth import (hash_password, verify_password, validate_password,
                      create_session_token, SESSION_COOKIE)

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html",
                                      {"request": request, "error": None})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    user = session.exec(
        select(User).where(User.username == username.strip().lower())
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Invalid username or password"
        })

    token = create_session_token(user.id)
    response = RedirectResponse(url="/day/", status_code=302)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        samesite="lax"
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html",
                                      {"request": request, "error": None})


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    session: Session = Depends(get_session)
):
    # Validate inputs
    username = username.strip().lower()
    display_name = display_name.strip()

    if not username or len(username) < 3:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "Username must be at least 3 characters"
        })

    password_error = validate_password(password)
    if password_error:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": password_error
        })

    if not display_name:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "Display name is required"
        })

    existing = session.exec(
        select(User).where(User.username == username)
    ).first()
    if existing:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "Username already taken"
        })

    user = User(
        username=username,
        hashed_password=hash_password(password),
        display_name=display_name,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_session_token(user.id)
    response = RedirectResponse(url="/onboarding/", status_code=302)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        samesite="lax"
    )
    return response