import time
import random
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.core.database import db
from app.middleware.auth import require_permission, get_current_user
from app.services.product_catalog import sync_products_from_shopify

router = APIRouter(prefix="/api", tags=["Categories & Tags"])

def gen_id(prefix: str) -> str:
    now_ms = int(time.time() * 1000)
    rand = random.randint(0, 9999)
    return f"{prefix}-{now_ms}-{rand}"

# --- Models ---
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class CategoryUpdate(BaseModel):
    name: str
    description: Optional[str] = ""

class TagCreate(BaseModel):
    name: str
    color: Optional[str] = "#dc2626"
    categoryId: str

class TagUpdate(BaseModel):
    name: str
    color: Optional[str] = "#dc2626"
    categoryId: str

class ShopifySyncRequest(BaseModel):
    domain: Optional[str] = None
    accessToken: Optional[str] = None

# --- Categories ---

@router.get("/categories")
async def list_categories(user: dict = Depends(get_current_user)):
    rows = await db.fetch(
        "SELECT id, name, description, created_at, updated_at FROM coexistence.categories ORDER BY name ASC"
    )
    return [dict(r) for r in rows]

@router.post("/categories", status_code=201)
async def create_category(payload: CategoryCreate, user: dict = Depends(require_permission("admin-settings:category"))):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    cat_id = gen_id("cat")
    desc = (payload.description or "").strip()
    row = await db.fetchrow(
        """
        INSERT INTO coexistence.categories (id, name, description)
        VALUES ($1, $2, $3)
        RETURNING id, name, description, created_at, updated_at
        """,
        cat_id, name, desc
    )
    return dict(row)

@router.put("/categories/{category_id}")
async def update_category(category_id: str, payload: CategoryUpdate, user: dict = Depends(require_permission("admin-settings:category"))):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    desc = (payload.description or "").strip()
    row = await db.fetchrow(
        """
        UPDATE coexistence.categories
        SET name = $1, description = $2, updated_at = NOW()
        WHERE id = $3
        RETURNING id, name, description, created_at, updated_at
        """,
        name, desc, category_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Category not found")
    return dict(row)

@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, user: dict = Depends(require_permission("admin-settings:category"))):
    result = await db.execute("DELETE FROM coexistence.categories WHERE id = $1", category_id)
    # result string is like "DELETE 1" or "DELETE 0"
    if result.endswith(" 0"):
        raise HTTPException(status_code=404, detail="Category not found")
    return {"ok": True}

# --- Tags ---

@router.get("/tags")
async def list_tags(user: dict = Depends(get_current_user)):
    rows = await db.fetch(
        """
        SELECT t.id, t.name, t.color, t.category_id, t.created_at, t.updated_at,
               c.name as category_name
        FROM coexistence.tags t
        LEFT JOIN coexistence.categories c ON c.id = t.category_id
        ORDER BY t.name ASC
        """
    )
    return [dict(r) for r in rows]

@router.post("/tags", status_code=201)
async def create_tag(payload: TagCreate, user: dict = Depends(require_permission("admin-settings:tags"))):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if not payload.categoryId:
        raise HTTPException(status_code=400, detail="Category is required")
    
    tag_id = gen_id("tag")
    color = payload.color.strip() if payload.color else "#dc2626"
    row = await db.fetchrow(
        """
        INSERT INTO coexistence.tags (id, name, color, category_id)
        VALUES ($1, $2, $3, $4)
        RETURNING id, name, color, category_id, created_at, updated_at
        """,
        tag_id, name, color, payload.categoryId
    )
    return dict(row)

@router.put("/tags/{tag_id}")
async def update_tag(tag_id: str, payload: TagUpdate, user: dict = Depends(require_permission("admin-settings:tags"))):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    color = payload.color.strip() if payload.color else "#dc2626"
    row = await db.fetchrow(
        """
        UPDATE coexistence.tags
        SET name = $1, color = $2, category_id = $3, updated_at = NOW()
        WHERE id = $4
        RETURNING id, name, color, category_id, created_at, updated_at
        """,
        name, color, payload.categoryId, tag_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Tag not found")
    return dict(row)

@router.delete("/tags/{tag_id}")
async def delete_tag(tag_id: str, user: dict = Depends(require_permission("admin-settings:tags"))):
    result = await db.execute("DELETE FROM coexistence.tags WHERE id = $1", tag_id)
    if result.endswith(" 0"):
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"ok": True}

# --- Shopify Sync ---

@router.post("/products/sync-shopify")
async def sync_shopify_catalog(payload: Optional[ShopifySyncRequest] = None, user: dict = Depends(get_current_user)):
    domain = (payload.domain if payload else None) or os.getenv("SHOPIFY_STORE_DOMAIN")
    access_token = (payload.accessToken if payload else None) or os.getenv("SHOPIFY_ADMIN_API_ACCESS_TOKEN")
    if not domain:
        raise HTTPException(status_code=400, detail="Shopify domain is required (e.g. your-shop.myshopify.com)")
    
    count = await sync_products_from_shopify(domain, access_token)
    return {"ok": True, "domain": domain, "syncedVariants": count}
