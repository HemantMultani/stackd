from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from datetime import date as date_type, datetime
from typing import Optional
from app.database import get_session
from app.models import (Project, ProjectTask, ProjectDailyLog,
                        ProjectStatus, TaskStatus, Day)
from app.auth import require_user


router = APIRouter(prefix="/projects", tags=["projects"])
templates = Jinja2Templates(directory="app/templates")


def get_or_create_today(session: Session) -> Day:
    today = date_type.today()
    day = session.exec(select(Day).where(Day.log_date == today)).first()
    if not day:
        day = Day(log_date=today)
        session.add(day)
        session.commit()
        session.refresh(day)
    return day


@router.get("/", response_class=HTMLResponse)
def projects_page(request: Request,
                  session: Session = Depends(get_session)):
    user = require_user(request, session)
    projects = session.exec(
        select(Project).where(Project.user_id == user.id)
    ).all()
    today = date_type.today()
    day = get_or_create_today(session)

    projects_data = []
    for p in projects:
        tasks = session.exec(
            select(ProjectTask)
            .where(ProjectTask.project_id == p.id)
            .order_by(ProjectTask.priority)
        ).all()
        daily_log = session.exec(
            select(ProjectDailyLog)
            .where(ProjectDailyLog.project_id == p.id)
            .where(ProjectDailyLog.day_id == day.id)
        ).first()
        # daily_log may be None — handle in template

        todo_count = sum(1 for t in tasks
                        if t.status == TaskStatus.todo)
        done_count = sum(1 for t in tasks
                        if t.status == TaskStatus.done)
        projects_data.append({
            "project": p,
            "tasks": tasks,
            "daily_log": daily_log,
            "todo_count": todo_count,
            "done_count": done_count,
        })

    return templates.TemplateResponse("projects.html", {
        "request": request,
        "user": user,
        "projects_data": projects_data,
        "today": today,
    })

@router.patch("/{project_id}/log/worked", response_class=HTMLResponse)
def toggle_worked(
    project_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    from app.routers.day import get_or_create_today
    user = require_user(request, session)
    day = get_or_create_today(session, user.id)

    log = session.exec(
        select(ProjectDailyLog)
        .where(ProjectDailyLog.project_id == project_id)
        .where(ProjectDailyLog.day_id == day.id)
    ).first()

    if not log:
        # Create lazily — only on first interaction
        log = ProjectDailyLog(
            project_id=project_id,
            day_id=day.id,
            worked=False
        )
        session.add(log)
        session.flush()

    log.worked = not log.worked
    log.updated_at = datetime.utcnow()
    session.add(log)
    session.commit()
    session.refresh(log)

    project = session.get(Project, project_id)
    return templates.TemplateResponse("partials/project_worked.html", {
        "request": request,
        "project": project,
        "daily_log": log,
    })

@router.post("/{project_id}/log/note", response_class=HTMLResponse)
def save_note(
    project_id: int,
    request: Request,
    note: str = Form(""),
    session: Session = Depends(get_session)
):
    day = get_or_create_today(session)
    log = session.exec(
        select(ProjectDailyLog)
        .where(ProjectDailyLog.project_id == project_id)
        .where(ProjectDailyLog.day_id == day.id)
    ).first()

    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    log.note = note.strip() or None
    session.add(log)
    session.commit()
    session.refresh(log)

    return HTMLResponse('<span style="color:#0F6E56;font-size:12px;">saved</span>')


@router.patch("/tasks/{task_id}/status", response_class=HTMLResponse)
def update_task_status(
    task_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    task = session.get(ProjectTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Cycle: todo → in_progress → done → todo
    cycle = {
        TaskStatus.todo: TaskStatus.in_progress,
        TaskStatus.in_progress: TaskStatus.done,
        TaskStatus.done: TaskStatus.todo,
    }
    task.status = cycle.get(task.status, TaskStatus.todo)
    task.completed_date = date_type.today() if task.status == TaskStatus.done else None
    session.add(task)
    session.commit()
    session.refresh(task)

    return templates.TemplateResponse("partials/task_row.html", {
        "request": request,
        "task": task,
    })


@router.post("/{project_id}/tasks/add", response_class=HTMLResponse)
def add_task(
    project_id: int,
    request: Request,
    title: str = Form(...),
    priority: int = Form(2),
    session: Session = Depends(get_session)
):
    task = ProjectTask(
        project_id=project_id,
        title=title,
        priority=priority,
        created_date=date_type.today(),
        status=TaskStatus.todo
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    return templates.TemplateResponse("partials/task_row.html", {
        "request": request,
        "task": task,
    })