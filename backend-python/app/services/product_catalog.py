import re
import os
import httpx
from typing import Optional
from app.core.database import db

memory_cache = {}

async def ensure_product_table():
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS coexistence.product_catalog_cache (
                variant_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                price NUMERIC,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
    except Exception as e:
        print(f"[productCatalog] ensure table failed: {e}")

async def sync_products_from_shopify(domain: str, access_token: Optional[str] = None) -> int:
    if not domain:
        return 0
    await ensure_product_table()
    clean_domain = re.sub(r"^https?://", "", domain).split("/")[0].strip()
    count = 0

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Try public /products.json
        try:
            public_url = f"https://{clean_domain}/products.json?limit=250"
            res = await client.get(public_url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                data = res.json()
                products = data.get("products", [])
                for p in products:
                    p_title = p.get("title", "")
                    for v in p.get("variants", []):
                        v_id = str(v.get("id"))
                        v_sub = f" ({v['title']})" if v.get("title") and v["title"] != "Default Title" else ""
                        full_title = f"{p_title}{v_sub}"
                        memory_cache[v_id] = full_title
                        price = None
                        try:
                            if v.get("price") is not None:
                                price = float(v["price"])
                        except (ValueError, TypeError):
                            pass
                        try:
                            await db.execute(
                                """
                                INSERT INTO coexistence.product_catalog_cache (variant_id, title, price, updated_at)
                                VALUES ($1, $2, $3, NOW())
                                ON CONFLICT (variant_id) DO UPDATE SET title = EXCLUDED.title, updated_at = NOW()
                                """,
                                v_id, full_title, price
                            )
                            count += 1
                        except Exception:
                            pass
                if count > 0:
                    return count
        except Exception as e:
            print(f"[productCatalog] Public fetch failed for {clean_domain}: {e}")

        # 2. Fallback to Admin API
        if access_token:
            try:
                admin_url = f"https://{clean_domain}/admin/api/2024-01/products.json?limit=250"
                res = await client.get(
                    admin_url,
                    headers={"X-Shopify-Access-Token": access_token, "Content-Type": "application/json"}
                )
                if res.status_code == 200:
                    data = res.json()
                    products = data.get("products", [])
                    for p in products:
                        p_title = p.get("title", "")
                        for v in p.get("variants", []):
                            v_id = str(v.get("id"))
                            v_sub = f" ({v['title']})" if v.get("title") and v["title"] != "Default Title" else ""
                            full_title = f"{p_title}{v_sub}"
                            memory_cache[v_id] = full_title
                            price = None
                            try:
                                if v.get("price") is not None:
                                    price = float(v["price"])
                            except (ValueError, TypeError):
                                pass
                            try:
                                await db.execute(
                                    """
                                    INSERT INTO coexistence.product_catalog_cache (variant_id, title, price, updated_at)
                                    VALUES ($1, $2, $3, NOW())
                                    ON CONFLICT (variant_id) DO UPDATE SET title = EXCLUDED.title, updated_at = NOW()
                                    """,
                                    v_id, full_title, price
                                )
                                count += 1
                            except Exception:
                                pass
            except Exception as admin_err:
                print(f"[productCatalog] Admin API fetch failed for {clean_domain}: {admin_err}")

    return count
