from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import UniqueConstraint, JSON
from typing import Optional, List
from datetime import date as date_type, datetime, time
from enum import Enum


# ─── Enums ───────────────────────────────────────────────────────────────────

class ChecklistStatus(str, Enum):
    pending = "pending"
    done = "done"
    skipped = "skipped"

# WorkoutType enum removed — replaced by WorkoutTemplate (user-defined)

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

class OathStatus(str, Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"

class ProjectStatus(str, Enum):
    active = "active"
    shipped = "shipped"
    paused = "paused"
    dropped = "dropped"

class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    dropped = "dropped"


# ─── User ─────────────────────────────────────────────────────────────────────
# Lean — identity only. Goals and schedule live in their own models.

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    display_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    goals: Optional["UserGoals"] = Relationship(back_populates="user")
    workout_schedule: List["UserWorkoutSchedule"] = Relationship(
        back_populates="user"
    )
    workout_templates: List["WorkoutTemplate"] = Relationship(
        back_populates="user"
    )
    supplements: List["Supplement"] = Relationship(back_populates="user")
    food_items: List["FoodItem"] = Relationship(back_populates="user")
    days: List["Day"] = Relationship(back_populates="user")
    oaths: List["Oath"] = Relationship(back_populates="user")
    projects: List["Project"] = Relationship(back_populates="user")


# ─── User Goals ───────────────────────────────────────────────────────────────
# All targets live here. Extend freely without touching User.

class UserGoals(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)

    # Current goals
    protein_goal_grams: int = Field(default=100, ge=0, le=400)
    sprint_sessions_per_week: int = Field(default=5, ge=0, le=7)

    # Future goals slot in here without schema changes
    # calories_goal: Optional[int] = None
    # sleep_hours_goal: Optional[float] = None
    # daily_steps_goal: Optional[int] = None
    # water_ml_goal: Optional[int] = None
    # weight_goal_kg: Optional[float] = None

    updated_at: Optional[datetime] = Field(default=None)

    user: Optional[User] = Relationship(back_populates="goals")


# ─── Workout Template ─────────────────────────────────────────────────────────
# User-defined workout types. No hardcoded enum.
# e.g. "Upper Body", "Leg Day", "Yoga", "HIIT", "Rest Active Recovery"

class WorkoutTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    name: str
    color: Optional[str] = Field(default=None)  # hex, for UI
    active: bool = Field(default=True)           # soft delete
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="workout_templates")
    schedule_slots: List["UserWorkoutSchedule"] = Relationship(
        back_populates="workout_template"
    )
    logs: List["WorkoutLog"] = Relationship(back_populates="workout_template")


# ─── User Workout Schedule ────────────────────────────────────────────────────
# One row per scheduled workout slot. Clean, queryable, flexible.
# Mon=0, Sun=6

class UserWorkoutSchedule(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "user_id", "weekday",
            name="uq_schedule_user_weekday"
        ),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    weekday: int = Field(ge=0, le=6)
    workout_template_id: int = Field(foreign_key="workouttemplate.id")

    user: Optional[User] = Relationship(back_populates="workout_schedule")
    workout_template: Optional[WorkoutTemplate] = Relationship(
        back_populates="schedule_slots"
    )


# ─── Supplement ───────────────────────────────────────────────────────────────

class Supplement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    name: str
    scheduled_time: SupplementTime
    notes: Optional[str] = None
    active: bool = Field(default=True)   # soft delete — never hard delete
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    user: Optional[User] = Relationship(back_populates="supplements")
    logs: List["SupplementLog"] = Relationship(back_populates="supplement")


# ─── Food Item ────────────────────────────────────────────────────────────────
# Decoupled from nutrition — FoodItem is the item, FoodItemNutrition
# holds its facts. Extend nutrition freely without touching this model.

class FoodItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    name: str
    meal_time: MealTime
    serving_description: Optional[str] = None  # "200g", "1 cup", "2 whole"
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    user: Optional[User] = Relationship(back_populates="food_items")
    nutrition: Optional["FoodItemNutrition"] = Relationship(
        back_populates="food_item"
    )
    logs: List["FoodLog"] = Relationship(back_populates="food_item")


class FoodItemNutrition(SQLModel, table=True):
    """
    Nutrition facts per serving. All values optional —
    user fills what they know. Extend without touching FoodItem.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    food_item_id: int = Field(foreign_key="fooditem.id", unique=True)

    protein_grams: Optional[float] = Field(default=None, ge=0)

    # Future slots — uncomment as needed, no migration pain
    # calories: Optional[float] = Field(default=None, ge=0)
    # carbs_grams: Optional[float] = Field(default=None, ge=0)
    # fat_grams: Optional[float] = Field(default=None, ge=0)
    # fiber_grams: Optional[float] = Field(default=None, ge=0)

    updated_at: Optional[datetime] = Field(default=None)

    food_item: Optional[FoodItem] = Relationship(back_populates="nutrition")


# ─── Day ──────────────────────────────────────────────────────────────────────

class Day(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "user_id", "log_date",
            name="uq_day_user_date"
        ),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    log_date: date_type = Field(index=True)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="days")
    supplement_logs: List["SupplementLog"] = Relationship(
        back_populates="day"
    )
    food_logs: List["FoodLog"] = Relationship(back_populates="day")
    workout_logs: List["WorkoutLog"] = Relationship(back_populates="day")
    sprint_logs: List["SprintLog"] = Relationship(back_populates="day")
    project_logs: List["ProjectDailyLog"] = Relationship(back_populates="day")


# ─── Supplement Log ───────────────────────────────────────────────────────────

class SupplementLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day_id: int = Field(foreign_key="day.id")
    supplement_id: int = Field(foreign_key="supplement.id")
    status: ChecklistStatus = Field(default=ChecklistStatus.pending)
    updated_at: Optional[datetime] = Field(default=None)

    day: Optional[Day] = Relationship(back_populates="supplement_logs")
    supplement: Optional[Supplement] = Relationship(back_populates="logs")


# ─── Food Log ─────────────────────────────────────────────────────────────────

class FoodLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day_id: int = Field(foreign_key="day.id")
    food_item_id: int = Field(foreign_key="fooditem.id")
    eaten: bool = Field(default=False)
    updated_at: Optional[datetime] = Field(default=None)

    day: Optional[Day] = Relationship(back_populates="food_logs")
    food_item: Optional[FoodItem] = Relationship(back_populates="logs")


# ─── Workout Log ──────────────────────────────────────────────────────────────

class WorkoutLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day_id: int = Field(foreign_key="day.id")
    workout_template_id: Optional[int] = Field(
        default=None, foreign_key="workouttemplate.id"
    )
    status: WorkoutStatus = Field(default=WorkoutStatus.pending)
    notes: Optional[str] = None
    updated_at: Optional[datetime] = Field(default=None)

    day: Optional[Day] = Relationship(back_populates="workout_logs")
    workout_template: Optional[WorkoutTemplate] = Relationship(
        back_populates="logs"
    )


# ─── Sprint Log ───────────────────────────────────────────────────────────────

class SprintLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day_id: int = Field(foreign_key="day.id")
    duration_minutes: int = Field(default=10)
    status: SprintStatus = Field(default=SprintStatus.pending)
    updated_at: Optional[datetime] = Field(default=None)

    day: Optional[Day] = Relationship(back_populates="sprint_logs")


# ─── Oath ─────────────────────────────────────────────────────────────────────

class Oath(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    title: str
    intention: str
    start_date: date_type
    end_date: date_type
    status: OathStatus = Field(default=OathStatus.active)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    user: Optional[User] = Relationship(back_populates="oaths")
    milestones: List["OathMilestone"] = Relationship(back_populates="oath")


class OathMilestone(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    oath_id: int = Field(foreign_key="oath.id")
    title: str
    target_date: Optional[date_type] = None
    completed: bool = Field(default=False)
    completed_date: Optional[date_type] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    oath: Optional[Oath] = Relationship(back_populates="milestones")


# ─── Project ──────────────────────────────────────────────────────────────────

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    name: str
    description: Optional[str] = None
    status: ProjectStatus = Field(default=ProjectStatus.active)
    started_date: date_type
    shipped_date: Optional[date_type] = None
    goal: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    user: Optional[User] = Relationship(back_populates="projects")
    tasks: List["ProjectTask"] = Relationship(back_populates="project")
    daily_logs: List["ProjectDailyLog"] = Relationship(
        back_populates="project"
    )


class ProjectTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    title: str
    status: TaskStatus = Field(default=TaskStatus.todo)
    priority: int = Field(default=2, ge=1, le=3)
    created_date: date_type
    completed_date: Optional[date_type] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    project: Optional[Project] = Relationship(back_populates="tasks")


class ProjectDailyLog(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "project_id", "day_id",
            name="uq_projectdailylog_project_day"
        ),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    day_id: int = Field(foreign_key="day.id")
    worked: bool = Field(default=False)
    note: Optional[str] = None
    updated_at: Optional[datetime] = Field(default=None)

    project: Optional[Project] = Relationship(back_populates="daily_logs")
    day: Optional[Day] = Relationship(back_populates="project_logs")