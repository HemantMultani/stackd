from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import create_db_and_tables
from app.seed import run_seed
from app.routers import day, supplements, food, workout, sprint
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    run_seed()
    yield

app = FastAPI(title="Stackd", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(day.router)
app.include_router(supplements.router)
app.include_router(food.router)
app.include_router(workout.router)
app.include_router(sprint.router)


@app.get("/")
def root():
    return RedirectResponse(url="/day/")