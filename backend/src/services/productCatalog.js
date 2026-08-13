const pool = require('../db');

// In-memory cache for fast synchronous lookup during webhook parsing
const memoryCache = new Map();

/**
 * Ensure product_catalog_cache table exists in Postgres
 */
async function ensureProductTable() {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS coexistence.product_catalog_cache (
        variant_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        price NUMERIC,
        updated_at TIMESTAMPTZ DEFAULT NOW()
      );
    `);
  } catch (err) {
    console.error('[productCatalog] ensure table failed:', err.message);
  }
}

/**
 * Syncs products from a Shopify domain (using public /products.json or Admin API) into DB & memory cache.
 */
async function syncProductsFromShopify(domain, accessToken = null) {
  if (!domain) return 0;
  await ensureProductTable();
  const cleanDomain = domain.replace(/^https?:\/\//, '').replace(/\/.*$/, '').trim();
  let count = 0;

  try {
    // 1. Try public /products.json endpoint (no token required!)
    const publicUrl = `https://${cleanDomain}/products.json?limit=250`;
    const pRes = await fetch(publicUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (pRes.ok) {
      const pData = await pRes.json();
      const products = pData.products || [];
      for (const p of products) {
        const pTitle = p.title || '';
        const variants = p.variants || [];
        for (const v of variants) {
          const vId = String(v.id);
          const vSub = v.title && v.title !== 'Default Title' ? ` (${v.title})` : '';
          const fullTitle = `${pTitle}${vSub}`;
          memoryCache.set(vId, fullTitle);
          await pool.query(
            `INSERT INTO coexistence.product_catalog_cache (variant_id, title, price, updated_at)
             VALUES ($1, $2, $3, NOW())
             ON CONFLICT (variant_id) DO UPDATE SET title = EXCLUDED.title, updated_at = NOW()`,
            [vId, fullTitle, v.price || null]
          ).catch(() => {});
          count++;
        }
      }
      if (count > 0) {
        console.log(`[productCatalog] Synced ${count} product variants from public https://${cleanDomain}/products.json`);
        return count;
      }
    }
  } catch (err) {
    console.error(`[productCatalog] Public fetch failed for ${cleanDomain}:`, err.message);
  }

  // 2. Fallback to Admin API if access token is available
  if (accessToken) {
    try {
      const adminUrl = `https://${cleanDomain}/admin/api/2024-01/products.json?limit=250`;
      const res = await fetch(adminUrl, {
        headers: { 'X-Shopify-Access-Token': accessToken, 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        const data = await res.json();
        const products = data.products || [];
        for (const p of products) {
          const pTitle = p.title || '';
          const variants = p.variants || [];
          for (const v of variants) {
            const vId = String(v.id);
            const vSub = v.title && v.title !== 'Default Title' ? ` (${v.title})` : '';
            const fullTitle = `${pTitle}${vSub}`;
            memoryCache.set(vId, fullTitle);
            await pool.query(
              `INSERT INTO coexistence.product_catalog_cache (variant_id, title, price, updated_at)
               VALUES ($1, $2, $3, NOW())
               ON CONFLICT (variant_id) DO UPDATE SET title = EXCLUDED.title, updated_at = NOW()`,
              [vId, fullTitle, v.price || null]
            ).catch(() => {});
            count++;
          }
        }
      }
    } catch (adminErr) {
      console.error(`[productCatalog] Admin API fetch failed for ${cleanDomain}:`, adminErr.message);
    }
  }

  return count;
}

/**
 * Resolves a product_retailer_id (e.g. "46019039690948") to its friendly name (e.g. "LINNDEN Premium Modal Trunk").
 */
async function resolveProductName(retailerId) {
  if (!retailerId) return 'Product';
  const idStr = String(retailerId).trim();

  // If it already looks like a human-readable title (contains letters/spaces, not pure digits)
  if (/[a-zA-Z]/.test(idStr)) {
    return idStr;
  }

  // 1. Check in-memory cache
  if (memoryCache.has(idStr)) {
    return memoryCache.get(idStr);
  }

  // 2. Check DB cache
  try {
    await ensureProductTable();
    const { rows } = await pool.query(
      `SELECT title FROM coexistence.product_catalog_cache WHERE variant_id = $1 LIMIT 1`,
      [idStr]
    );
    if (rows.length > 0 && rows[0].title) {
      memoryCache.set(idStr, rows[0].title);
      return rows[0].title;
    }
  } catch (err) {
    // Non-fatal DB lookup error
  }

  // 3. Auto-sync from process.env.SHOPIFY_STORE_DOMAIN if configured
  const storeDomain = process.env.SHOPIFY_STORE_DOMAIN;
  const accessToken = process.env.SHOPIFY_ADMIN_API_ACCESS_TOKEN;
  if (storeDomain) {
    const synced = await syncProductsFromShopify(storeDomain, accessToken);
    if (synced > 0 && memoryCache.has(idStr)) {
      return memoryCache.get(idStr);
    }
  }

  return idStr;
}

module.exports = {
  resolveProductName,
  syncProductsFromShopify,
  ensureProductTable,
};
