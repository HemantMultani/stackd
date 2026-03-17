from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import date as date_type, time
from enum import Enum


# ─── Enums ───────────────────────────────────────────────────────────────────
# Each status enum is intentionally separate despite similar values.
# They will diverge as features are added. Do not consolidate.
class ChecklistStatus(str, Enum):
    pending = "pending"
    done = "done"
    skipped = "skipped"

class WorkoutType(str, Enum):
    upper_body = "upper_body"
    lower_body = "lower_body"

class WorkoutStatus(str, Enum):
    pending = "pending"
    done = "done"
    skipped = "skipped"

class SprintStatus(str, Enum):
    pending = "pending"
    done = "done"
    skipped = "skipped"

class SupplementTime(str, Enum):
    morning = "morning"
    afternoon = "afternoon"
    night = "night"

class MealTime(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


# ─── Supplement Library (master list, seeded once) ───────────────────────────

class Supplement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    scheduled_time: SupplementTime
    notes: Optional[str] = None  # e.g. "separate from zinc by 2hrs"

    logs: List["SupplementLog"] = Relationship(back_populates="supplement")


# ─── Food Item Library (master list, seeded once) ────────────────────────────

class FoodItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    protein_grams: float
    meal_time: MealTime  # suggested meal slot

    logs: List["FoodLog"] = Relationship(back_populates="food_item")


# ─── Day (anchor for everything) ─────────────────────────────────────────────

class Day(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    log_date: date_type  = Field(index=True, unique=True)
    notes: Optional[str] = None  # free text, used later for Joy Journal

    supplement_logs: List["SupplementLog"] = Relationship(back_populates="day")
    food_logs: List["FoodLog"] = Relationship(back_populates="day")
    workout_logs: List["WorkoutLog"] = Relationship(back_populates="day")
    sprint_logs: List["SprintLog"] = Relationship(back_populates="day")
    checklist_items: List["ChecklistItem"] = Relationship(back_populates="day")
    project_logs: List["ProjectDailyLog"] = Relationship(back_populates="day")


# ─── Supplement Log (daily intake tracking) ──────────────────────────────────

class SupplementLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day_id: int = Field(foreign_key="day.id")
    supplement_id: int = Field(foreign_key="supplement.id")
    status: ChecklistStatus = ChecklistStatus.pending

    day: Optional[Day] = Relationship(back_populates="supplement_logs")
    supplement: Optional[Supplement] = Relationship(back_populates="logs")


# ─── Food Log (daily food + protein tracking) ────────────────────────────────

class FoodLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day_id: int = Field(foreign_key="day.id")
    food_item_id: int = Field(foreign_key="fooditem.id")
    eaten: bool = False

    day: Optional[Day] = Relationship(back_populates="food_logs")
    food_item: Optional[FoodItem] = Relationship(back_populates="logs")


# ─── Workout Log ──────────────────────────────────────────────────────────────

class WorkoutLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day_id: int = Field(foreign_key="day.id")
    workout_type: WorkoutType
    status: WorkoutStatus = WorkoutStatus.pending
    notes: Optional[str] = None

    day: Optional[Day] = Relationship(back_populates="workout_logs")


# ─── Sprint Log ───────────────────────────────────────────────────────────────

class SprintLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day_id: int = Field(foreign_key="day.id")
    duration_minutes: int = 10
    status: SprintStatus = SprintStatus.pending

    day: Optional[Day] = Relationship(back_populates="sprint_logs")


# ─── Checklist Item (work, personal tasks) ───────────────────────────────────

class ChecklistItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day_id: int = Field(foreign_key="day.id")
    title: str
    scheduled_time: Optional[time] = None
    status: ChecklistStatus = ChecklistStatus.pending
    category: Optional[str] = None  # "work" / "personal" / etc.

    day: Optional[Day] = Relationship(back_populates="checklist_items")

# ─── Oath ────────────────────────────────────────────────────────────────────

class OathStatus(str, Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"

class Oath(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str                          # "6 Month Apex Oath"
    intention: str                      # why you're doing this
    start_date: date_type
    end_date: date_type                 # start + 180 days
    status: OathStatus = OathStatus.active

    milestones: List["OathMilestone"] = Relationship(back_populates="oath")


class OathMilestone(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    oath_id: int = Field(foreign_key="oath.id")
    title: str                          # "Ship 3 products"
    target_date: Optional[date_type] = None
    completed: bool = False
    completed_date: Optional[date_type] = None

    oath: Optional[Oath] = Relationship(back_populates="milestones")


# ─── Projects ────────────────────────────────────────────────────────────────

class ProjectStatus(str, Enum):
    active = "active"
    shipped = "shipped"
    paused = "paused"
    dropped = "dropped"

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.active
    started_date: date_type
    shipped_date: Optional[date_type] = None
    goal: Optional[str] = None          # "Ship v1 by April"

    tasks: List["ProjectTask"] = Relationship(back_populates="project")
    daily_logs: List["ProjectDailyLog"] = Relationship(back_populates="project")


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    dropped = "dropped"

class ProjectTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    title: str
    status: TaskStatus = TaskStatus.todo
    created_date: date_type
    completed_date: Optional[date_type] = None
    priority: int = Field(default=2)    # 1=high 2=medium 3=low

    project: Optional[Project] = Relationship(back_populates="tasks")


class ProjectDailyLog(SQLModel, table=True):
    """Did you work on this project today? What did you do?"""
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    day_id: int = Field(foreign_key="day.id")
    worked: bool = False
    note: Optional[str] = None         # "Built auth flow, fixed HTMX bug"

    project: Optional[Project] = Relationship(back_populates="daily_logs")
    day: Optional[Day] = Relationship(back_populates="project_logs")