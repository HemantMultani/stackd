from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.database import get_session
from app.models import FoodLog

router = APIRouter(prefix="/food", tags=["food"])


@router.patch("/{log_id}/eaten")
def mark_food_eaten(
    log_id: int,
    eaten: bool,
    session: Session = Depends(get_session)
):
    log = session.get(FoodLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Food log not found")

    log.eaten = eaten
    session.add(log)
    session.commit()
    session.refresh(log)
    return {"log_id": log.id, "eaten": log.eaten}