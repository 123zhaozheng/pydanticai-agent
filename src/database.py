from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Import models to register them with SQLAlchemy
from src.models.tools_skills import (  # noqa: E402
    McpServer,
    Skill,
    RoleToolPermission,
    RoleSkillPermission,
    DepartmentToolPermission,
    DepartmentSkillPermission,
)

from src.models.user_management import (  # noqa: E402
    User,
    Role,
    Department,
    Menu,
    Button,
    RoleMenu,
    RoleButton,
)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
