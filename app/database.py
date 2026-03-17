from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv
import os

load_dotenv()

ENV = os.getenv("ENV", "dev")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./stackd_dev.db")

print(f"🔧 Environment: {ENV}")
print(f"🗄️  Database: {DATABASE_URL}")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
        if DATABASE_URL.startswith("sqlite") else {}
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session