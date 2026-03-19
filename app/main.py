from fastapi import FastAPI, Request as FastAPIRequest
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from contextlib import asynccontextmanager
from app.database import create_db_and_tables
from app.auth import NeedsAuthException
from app.routers import day, supplements, food, workout, sprint, oath, projects
from app.routers import auth, onboarding


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Stackd", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(NeedsAuthException)
async def auth_exception_handler(request: FastAPIRequest,
                                  exc: NeedsAuthException):
    # HTMX requests need HX-Redirect header, not a 302 body
    # Without this, HTMX swaps login HTML into a random div
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content="",
            status_code=200,
            headers={"HX-Redirect": "/auth/login"}
        )
    return RedirectResponse(url="/auth/login", status_code=302)


app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(day.router)
app.include_router(supplements.router)
app.include_router(food.router)
app.include_router(workout.router)
app.include_router(sprint.router)
app.include_router(oath.router)
app.include_router(projects.router)


@app.get("/")
def root():
    return RedirectResponse(url="/day/")