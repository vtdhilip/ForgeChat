import os
import time
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.core.config import settings

router = APIRouter(prefix="/api", tags=["Uploads"])

UPLOAD_DIR = os.getenv("UPLOADS_DIR", "/app/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only JPG and PNG files are allowed")

    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 2MB)")

    filename = f"bda-{int(time.time() * 1000)}-{os.urandom(4).hex()}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(contents)

    return {"url": f"/uploads/{filename}"}
