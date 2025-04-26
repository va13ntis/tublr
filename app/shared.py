from pathlib import Path

from fastapi.templating import Jinja2Templates

# Initialize Jinja2 templates
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
