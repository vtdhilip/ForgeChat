import os
import time
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from app.core.config import settings
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api", tags=["Uploads"])

UPLOAD_DIR = os.getenv("UPLOADS_DIR", "/app/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only JPG and PNG files are allowed")

    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 2MB)")

    if ext == ".png" and not contents.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=400, detail="Invalid PNG file signature")
    if ext in (".jpg", ".jpeg") and not contents.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=400, detail="Invalid JPEG file signature")

    filename = f"bda-{int(time.time() * 1000)}-{os.urandom(4).hex()}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(contents)

    return {"url": f"/uploads/{filename}"}
