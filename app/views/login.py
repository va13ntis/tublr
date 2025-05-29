import base64
import io
from datetime import datetime

import pyotp
import qrcode
from fastapi import Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db, User, RecognizedIP
from app.main import app, templates



