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

  // 3. Optional Shopify Admin API lookup if SHOPIFY_STORE_DOMAIN & token are set
  const storeDomain = process.env.SHOPIFY_STORE_DOMAIN;
  const accessToken = process.env.SHOPIFY_ADMIN_API_ACCESS_TOKEN;
  if (storeDomain && accessToken) {
    try {
      const cleanDomain = storeDomain.replace(/^https?:\/\//, '').replace(/\/.*$/, '');
      const url = `https://${cleanDomain}/admin/api/2024-01/variants/${idStr}.json`;
      const res = await fetch(url, {
        headers: {
          'X-Shopify-Access-Token': accessToken,
          'Content-Type': 'application/json',
        },
      });
      if (res.ok) {
        const data = await res.json();
        const variant = data.variant;
        if (variant) {
          // Fetch parent product title if possible
          let fullTitle = variant.title && variant.title !== 'Default Title' ? variant.title : '';
          if (variant.product_id) {
            const pRes = await fetch(`https://${cleanDomain}/admin/api/2024-01/products/${variant.product_id}.json`, {
              headers: { 'X-Shopify-Access-Token': accessToken },
            });
            if (pRes.ok) {
              const pData = await pRes.json();
              if (pData.product?.title) {
                fullTitle = fullTitle ? `${pData.product.title} (${fullTitle})` : pData.product.title;
              }
            }
          }
          if (fullTitle) {
            memoryCache.set(idStr, fullTitle);
            await pool.query(
              `INSERT INTO coexistence.product_catalog_cache (variant_id, title, price, updated_at)
               VALUES ($1, $2, $3, NOW())
               ON CONFLICT (variant_id) DO UPDATE SET title = EXCLUDED.title, updated_at = NOW()`,
              [idStr, fullTitle, variant.price || null]
            ).catch(() => {});
            return fullTitle;
          }
        }
      }
    } catch (shopifyErr) {
      console.error('[productCatalog] Shopify variant lookup failed:', shopifyErr.message);
    }
  }

  return idStr;
}

module.exports = {
  resolveProductName,
  ensureProductTable,
};
