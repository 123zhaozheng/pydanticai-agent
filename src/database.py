from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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


class UploadedFileModel(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    content_type = Column(String)
    size = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
