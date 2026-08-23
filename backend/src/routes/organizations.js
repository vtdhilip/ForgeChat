/**
 * Organizations (Tenants) Management API
 */

const { Router } = require('express');
const pool = require('../db');
const { requireOrgRole } = require('../middleware/tenantContext');

const router = Router();

// Helper to slugify organization name
function slugify(name) {
  return String(name || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || `org-${Date.now()}`;
}

// ── GET /api/organizations ──────────────────────────────────────────────────
// List all organizations the authenticated user belongs to
router.get('/', async (req, res) => {
  try {
    const userId = req.user.id;
    const isSuperAdmin = req.user.role === 'admin';

    let query = `
      SELECT o.id, o.name, o.slug, o.plan, o.settings, o.is_active, o.created_at,
             om.role AS member_role,
             (SELECT COUNT(*) FROM coexistence.organization_members WHERE org_id = o.id)::int AS member_count,
             (SELECT COUNT(*) FROM coexistence.whatsapp_accounts WHERE org_id = o.id)::int AS wa_count
        FROM coexistence.organizations o
    `;

    if (isSuperAdmin) {
      // Super-admins can view all orgs, joining membership if present
      query += `
        LEFT JOIN coexistence.organization_members om ON om.org_id = o.id AND om.user_id = $1
       ORDER BY o.created_at ASC
      `;
    } else {
      query += `
        JOIN coexistence.organization_members om ON om.org_id = o.id AND om.user_id = $1
       WHERE o.is_active = true
       ORDER BY o.created_at ASC
      `;
    }

    const { rows } = await pool.query(query, [userId]);

    const activeOrgId = req.orgId || (rows.length > 0 ? rows[0].id : null);

    res.json({
      organizations: rows.map(r => ({
        id: r.id,
        name: r.name,
        slug: r.slug,
        plan: r.plan,
        settings: r.settings || {},
        isActive: r.is_active,
        role: r.member_role || (isSuperAdmin ? 'owner' : 'viewer'),
        memberCount: r.member_count,
        waCount: r.wa_count,
        createdAt: r.created_at,
        isCurrent: r.id === activeOrgId,
      })),
      activeOrgId,
    });
  } catch (err) {
    console.error('[organizations] Error listing organizations:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ── POST /api/organizations ─────────────────────────────────────────────────
// Create a new organization (tenant)
router.post('/', async (req, res) => {
  try {
    const { name, plan = 'starter', settings = {} } = req.body;
    if (!name || !name.trim()) {
      return res.status(400).json({ error: 'Organization name is required' });
    }

    let slug = slugify(name);
    // Ensure slug uniqueness
    const { rows: slugCheck } = await pool.query(
      `SELECT 1 FROM coexistence.organizations WHERE slug = $1`,
      [slug]
    );
    if (slugCheck.length > 0) {
      slug = `${slug}-${Math.floor(1000 + Math.random() * 9000)}`;
    }

    const initialSettings = {
      order_prefix: `${name.slice(0, 3).toUpperCase()}-`,
      currency: 'INR',
      ...settings,
    };

    const client = await pool.connect();
    try {
      await client.query('BEGIN');

      const { rows } = await client.query(
        `INSERT INTO coexistence.organizations (name, slug, plan, settings)
         VALUES ($1, $2, $3, $4)
         RETURNING *`,
        [name.trim(), slug, plan, JSON.stringify(initialSettings)]
      );
      const newOrg = rows[0];

      // Assign creator as 'owner'
      await client.query(
        `INSERT INTO coexistence.organization_members (org_id, user_id, role)
         VALUES ($1, $2, 'owner')`,
        [newOrg.id, req.user.id]
      );

      await client.query('COMMIT');

      // Set cookie for active org
      res.cookie('forgecrm_active_org', newOrg.id, {
        httpOnly: false,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 365 * 24 * 60 * 60 * 1000,
      });

      res.status(201).json({
        success: true,
        organization: {
          id: newOrg.id,
          name: newOrg.name,
          slug: newOrg.slug,
          plan: newOrg.plan,
          settings: newOrg.settings,
          role: 'owner',
        },
      });
    } catch (txErr) {
      await client.query('ROLLBACK');
      throw txErr;
    } finally {
      client.release();
    }
  } catch (err) {
    console.error('[organizations] Error creating organization:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ── POST /api/organizations/switch ──────────────────────────────────────────
// Switch active organization
router.post('/switch', async (req, res) => {
  try {
    const { org_id } = req.body;
    if (!org_id) return res.status(400).json({ error: 'org_id is required' });

    // Verify membership
    const isSuperAdmin = req.user.role === 'admin';
    let query = `
      SELECT o.id, o.name, o.slug, o.plan, o.settings, om.role
        FROM coexistence.organizations o
    `;
    const params = [org_id];

    if (isSuperAdmin) {
      query += `
        LEFT JOIN coexistence.organization_members om ON om.org_id = o.id AND om.user_id = $2
       WHERE o.id::text = $1 OR o.slug = $1
      `;
      params.push(req.user.id);
    } else {
      query += `
        JOIN coexistence.organization_members om ON om.org_id = o.id AND om.user_id = $2
       WHERE (o.id::text = $1 OR o.slug = $1) AND o.is_active = true
      `;
      params.push(req.user.id);
    }

    const { rows } = await pool.query(query, params);
    if (rows.length === 0) {
      return res.status(403).json({ error: 'Access denied to this organization' });
    }

    const org = rows[0];

    res.cookie('forgecrm_active_org', org.id, {
      httpOnly: false,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 365 * 24 * 60 * 60 * 1000,
    });

    res.json({
      success: true,
      activeOrg: {
        id: org.id,
        name: org.name,
        slug: org.slug,
        plan: org.plan,
        settings: org.settings || {},
        role: org.role || (isSuperAdmin ? 'owner' : 'viewer'),
      },
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── GET /api/organizations/:id ──────────────────────────────────────────────
router.get('/:id', async (req, res) => {
  try {
    const orgId = req.params.id;
    const { rows } = await pool.query(
      `SELECT o.*,
              (SELECT COUNT(*) FROM coexistence.organization_members WHERE org_id = o.id)::int AS member_count,
              (SELECT COUNT(*) FROM coexistence.whatsapp_accounts WHERE org_id = o.id)::int AS wa_count,
              (SELECT COUNT(*) FROM coexistence.contacts WHERE org_id = o.id)::int AS contact_count,
              (SELECT COUNT(*) FROM coexistence.orders WHERE org_id = o.id)::int AS order_count
         FROM coexistence.organizations o
        WHERE o.id::text = $1 OR o.slug = $1`,
      [orgId]
    );

    if (rows.length === 0) return res.status(404).json({ error: 'Organization not found' });
    res.json({ organization: rows[0] });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── PUT /api/organizations/:id ──────────────────────────────────────────────
// Update organization details & integration settings (Requires 'owner' or 'admin')
router.put('/:id', requireOrgRole('owner', 'admin'), async (req, res) => {
  try {
    const orgId = req.params.id;
    const { name, settings, plan } = req.body;

    const updates = [];
    const params = [orgId];

    if (name && name.trim()) {
      params.push(name.trim());
      updates.push(`name = $${params.length}`);
    }
    if (plan && req.user.role === 'admin') {
      params.push(plan);
      updates.push(`plan = $${params.length}`);
    }
    if (settings && typeof settings === 'object') {
      params.push(JSON.stringify(settings));
      updates.push(`settings = $${params.length}`);
    }

    if (updates.length === 0) {
      return res.json({ success: true, message: 'No updates provided' });
    }

    updates.push(`updated_at = NOW()`);

    const { rows } = await pool.query(
      `UPDATE coexistence.organizations
          SET ${updates.join(', ')}
        WHERE id::text = $1
        RETURNING *`,
      params
    );

    res.json({ success: true, organization: rows[0] });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── GET /api/organizations/:id/members ──────────────────────────────────────
// List team members of an organization
router.get('/:id/members', async (req, res) => {
  try {
    const orgId = req.params.id;
    const { rows } = await pool.query(
      `SELECT u.id, u.username, u.email, u.display_name, u.role AS global_role,
              om.role AS org_role, om.created_at AS joined_at
         FROM coexistence.organization_members om
         JOIN coexistence.forgecrm_users u ON u.id = om.user_id
        WHERE om.org_id::text = $1
        ORDER BY om.created_at ASC`,
      [orgId]
    );
    res.json({ members: rows });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── POST /api/organizations/:id/members ─────────────────────────────────────
// Add member to organization
router.post('/:id/members', requireOrgRole('owner', 'admin'), async (req, res) => {
  try {
    const orgId = req.params.id;
    const { email, username, role = 'member' } = req.body;

    // Find user
    const { rows: userRows } = await pool.query(
      `SELECT id, username, email FROM coexistence.forgecrm_users
        WHERE LOWER(email) = LOWER($1) OR LOWER(username) = LOWER($2) LIMIT 1`,
      [email || '', username || '']
    );

    if (userRows.length === 0) {
      return res.status(404).json({ error: 'User account not found' });
    }

    const targetUser = userRows[0];

    const { rows } = await pool.query(
      `INSERT INTO coexistence.organization_members (org_id, user_id, role)
       VALUES ($1, $2, $3)
       ON CONFLICT (org_id, user_id) DO UPDATE SET role = EXCLUDED.role
       RETURNING *`,
      [orgId, targetUser.id, role]
    );

    res.json({ success: true, member: { ...targetUser, org_role: rows[0].role } });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── DELETE /api/organizations/:id/members/:userId ───────────────────────────
// Remove member from organization
router.delete('/:id/members/:userId', requireOrgRole('owner', 'admin'), async (req, res) => {
  try {
    const { id: orgId, userId } = req.params;

    // Prevent removing the last owner
    const { rows: owners } = await pool.query(
      `SELECT user_id FROM coexistence.organization_members WHERE org_id::text = $1 AND role = 'owner'`,
      [orgId]
    );
    if (owners.length === 1 && String(owners[0].user_id) === String(userId)) {
      return res.status(400).json({ error: 'Cannot remove the only owner of the organization' });
    }

    await pool.query(
      `DELETE FROM coexistence.organization_members WHERE org_id::text = $1 AND user_id = $2`,
      [orgId, userId]
    );

    res.json({ success: true, message: 'Member removed from organization' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── GET /api/organizations/:id/integrations ──────────────────────────────
router.get('/:id/integrations', async (req, res) => {
  try {
    const orgId = req.params.id;
    const { rows } = await pool.query(
      `SELECT settings FROM coexistence.organizations WHERE id::text = $1`,
      [orgId]
    );
    if (rows.length === 0) return res.status(404).json({ error: 'Organization not found' });

    const s = rows[0].settings || {};
    res.json({
      integrations: {
        razorpay_key_id: s.razorpay_key_id || process.env.RAZORPAY_KEY_ID || '',
        razorpay_key_secret: s.razorpay_key_secret || process.env.RAZORPAY_KEY_SECRET || '',
        shiprocket_email: s.shiprocket_email || process.env.SHIPROCKET_EMAIL || '',
        shiprocket_password: s.shiprocket_password || process.env.SHIPROCKET_PASSWORD || '',
        shiprocket_token: s.shiprocket_token || process.env.SHIPROCKET_API_TOKEN || '',
        shiprocket_pickup_location: s.shiprocket_pickup_location || process.env.SHIPROCKET_PICKUP_LOCATION || 'warehouse',
        google_sheet_webhook_url: s.google_sheet_webhook_url || process.env.GOOGLE_SHEET_WEBHOOK_URL || '',
        whatsapp_flow_id: s.whatsapp_flow_id || process.env.WHATSAPP_FLOW_ID || '',
        openai_api_key: s.openai_api_key || process.env.OPENAI_API_KEY || '',
        anthropic_api_key: s.anthropic_api_key || process.env.ANTHROPIC_API_KEY || '',
        order_prefix: s.order_prefix || 'LN-',
        shipping_fee: s.shipping_fee || 60,
      }
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── PUT /api/organizations/:id/integrations ──────────────────────────────
router.put('/:id/integrations', requireOrgRole('owner', 'admin'), async (req, res) => {
  try {
    const orgId = req.params.id;
    const incoming = req.body.integrations || req.body || {};

    const { rows: current } = await pool.query(
      `SELECT settings FROM coexistence.organizations WHERE id::text = $1`,
      [orgId]
    );
    if (current.length === 0) return res.status(404).json({ error: 'Organization not found' });

    const existingSettings = current[0].settings || {};
    const updatedSettings = {
      ...existingSettings,
      ...incoming,
    };

    await pool.query(
      `UPDATE coexistence.organizations
          SET settings = $1, updated_at = NOW()
        WHERE id::text = $2`,
      [JSON.stringify(updatedSettings), orgId]
    );

    res.json({ success: true, message: 'Integration settings saved successfully', settings: updatedSettings });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── POST /api/organizations/:id/integrations/test ─────────────────────────
router.post('/:id/integrations/test', async (req, res) => {
  try {
    const { type, credentials } = req.body;
    if (type === 'shiprocket') {
      const email = credentials?.shiprocket_email || process.env.SHIPROCKET_EMAIL;
      const password = credentials?.shiprocket_password || process.env.SHIPROCKET_PASSWORD;
      if (!email || !password) return res.status(400).json({ success: false, error: 'Email and password required' });

      const testRes = await fetch('https://apiv2.shiprocket.in/v1/external/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await testRes.json();
      if (testRes.ok && data.token) {
        return res.json({ success: true, message: 'Shiprocket authentication successful!' });
      } else {
        return res.status(400).json({ success: false, error: data.message || 'Shiprocket authentication failed' });
      }
    } else if (type === 'razorpay') {
      const keyId = credentials?.razorpay_key_id || process.env.RAZORPAY_KEY_ID;
      const keySecret = credentials?.razorpay_key_secret || process.env.RAZORPAY_KEY_SECRET;
      if (!keyId || !keySecret) return res.status(400).json({ success: false, error: 'Key ID and Key Secret required' });

      const authHeader = 'Basic ' + Buffer.from(`${keyId}:${keySecret}`).toString('base64');
      const testRes = await fetch('https://api.razorpay.com/v1/payments?count=1', {
        headers: { 'Authorization': authHeader },
      });
      if (testRes.ok) {
        return res.json({ success: true, message: 'Razorpay keys verified successfully!' });
      } else {
        return res.status(400).json({ success: false, error: `Razorpay verification failed (HTTP ${testRes.status})` });
      }
    } else {
      return res.json({ success: true, message: 'Configuration format valid' });
    }
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
