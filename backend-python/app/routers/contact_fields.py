import time
import random
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.core.database import db
from app.middleware.auth import require_permission, get_current_user

router = APIRouter(prefix="/api/contact-fields", tags=["Contact Fields"])

FIELD_TYPES = {'text', 'number', 'phone', 'email', 'date', 'url', 'textarea'}

def gen_id(prefix: str) -> str:
    now_ms = int(time.time() * 1000)
    rand = random.randint(0, 9999)
    return f"{prefix}-{now_ms}-{rand}"

def norm_type(t: Optional[str]) -> str:
    if t and t in FIELD_TYPES:
        return t
    return "text"

class ContactFieldCreate(BaseModel):
    name: str
    description: Optional[str] = None
    fieldType: Optional[str] = "text"
    sortOrder: Optional[int] = 0

class ContactFieldUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    fieldType: Optional[str] = None
    sortOrder: Optional[int] = None

@router.get("")
async def list_contact_fields(user: dict = Depends(get_current_user)):
    rows = await db.fetch(
        """
        SELECT id, name, description, field_type, sort_order, created_at, updated_at
        FROM coexistence.contact_field_definitions
        ORDER BY sort_order ASC, name ASC
        """
    )
    return [dict(r) for r in rows]

@router.post("", status_code=201)
async def create_contact_field(payload: ContactFieldCreate, user: dict = Depends(require_permission("admin-settings:fields"))):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Field name is required")
    
    field_id = gen_id("fld")
    desc = payload.description.strip() if payload.description else None
    ftype = norm_type(payload.fieldType)
    sort_order = payload.sortOrder if payload.sortOrder is not None else 0

    row = await db.fetchrow(
        """
        INSERT INTO coexistence.contact_field_definitions
          (id, name, description, field_type, sort_order)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, name, description, field_type, sort_order, created_at, updated_at
        """,
        field_id, name, desc, ftype, sort_order
    )
    return dict(row)

@router.put("/{field_id}")
async def update_contact_field(field_id: str, payload: ContactFieldUpdate, user: dict = Depends(require_permission("admin-settings:fields"))):
    if payload.name is not None and not payload.name.strip():
        raise HTTPException(status_code=400, detail="Field name cannot be empty")
    
    current = await db.fetchrow("SELECT * FROM coexistence.contact_field_definitions WHERE id = $1", field_id)
    if not current:
        raise HTTPException(status_code=404, detail="Field not found")

    new_name = payload.name.strip() if payload.name is not None else current["name"]
    new_desc = payload.description.strip() if payload.description is not None else current["description"]
    new_ftype = norm_type(payload.fieldType) if payload.fieldType is not None else current["field_type"]
    new_sort = payload.sortOrder if payload.sortOrder is not None else current["sort_order"]

    row = await db.fetchrow(
        """
        UPDATE coexistence.contact_field_definitions SET
          name = $2,
          description = $3,
          field_type = $4,
          sort_order = $5,
          updated_at = NOW()
        WHERE id = $1
        RETURNING id, name, description, field_type, sort_order, created_at, updated_at
        """,
        field_id, new_name, new_desc, new_ftype, new_sort
    )
    return dict(row)

@router.delete("/{field_id}")
async def delete_contact_field(field_id: str, user: dict = Depends(require_permission("admin-settings:fields"))):
    result = await db.execute(
        "DELETE FROM coexistence.contact_field_definitions WHERE id = $1",
        field_id
    )
    if result.endswith(" 0"):
        raise HTTPException(status_code=404, detail="Field not found")
    return {"ok": True}
