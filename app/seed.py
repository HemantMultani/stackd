from sqlmodel import Session, select
from app.database import engine
from app.models import Supplement, FoodItem, SupplementTime, MealTime


def seed_supplements(session: Session):
    existing = session.exec(select(Supplement)).first()
    if existing:
        return  # already seeded, skip

    supplements = [
        # Morning
        Supplement(name="Vitamin C 500mg",        scheduled_time=SupplementTime.morning),
        Supplement(name="Calcium Citrate Tab 1",   scheduled_time=SupplementTime.morning,
                   notes="Separate from Zinc by 2+ hours"),
        Supplement(name="Creatine Monohydrate",    scheduled_time=SupplementTime.morning),
        Supplement(name="Ashwagandha KSM-66",      scheduled_time=SupplementTime.morning),
        Supplement(name="Omega-3 Fish Oil",        scheduled_time=SupplementTime.morning),
        # Afternoon
        Supplement(name="Zinc with Copper",        scheduled_time=SupplementTime.afternoon,
                   notes="Separate from Calcium by 2+ hours"),
        # Night
        Supplement(name="Calcium Citrate Tab 2",   scheduled_time=SupplementTime.night),
        Supplement(name="Magnesium Bisglycinate",  scheduled_time=SupplementTime.night),
    ]
    session.add_all(supplements)
    session.commit()


def seed_food_items(session: Session):
    existing = session.exec(select(FoodItem)).first()
    if existing:
        return

    food_items = [
        FoodItem(name="Oats + seeds in soy milk",  protein_grams=10, meal_time=MealTime.breakfast),
        FoodItem(name="2 whole eggs post-workout",  protein_grams=14, meal_time=MealTime.breakfast),
        FoodItem(name="4 multigrain roti",          protein_grams=20, meal_time=MealTime.lunch),
        FoodItem(name="200g chicken breast",        protein_grams=50, meal_time=MealTime.dinner),
        FoodItem(name="200g curd",                  protein_grams=7,  meal_time=MealTime.dinner),
    ]
    session.add_all(food_items)
    session.commit()


def run_seed():
    with Session(engine) as session:
        seed_supplements(session)
        seed_food_items(session)
    print("✅ Seed data loaded.")