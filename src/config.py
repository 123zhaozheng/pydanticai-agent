from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Directory where uploaded files will be stored
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Database URL
DATABASE_URL = f"sqlite:///{BASE_DIR}/app.db"
