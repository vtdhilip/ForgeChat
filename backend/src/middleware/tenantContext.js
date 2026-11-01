/**
 * Tenant Context Middleware
 *
 * Resolves and enforces the active organization (tenant) for every authenticated request.
 * Injects:
 *   - req.orgId: UUID of the active organization
 *   - req.orgRole: User's role inside this organization ('owner', 'admin', 'member', 'agent', 'viewer')
 *   - req.org: Full organization details & settings
 */

const pool = require('../db');

async function tenantContext(req, res, next) {
  // Skip if not authenticated or auth is handled elsewhere
  if (!req.user || !req.user.id) {
    return next();
  }

  try {
    const userId = req.user.id;
    const requestedOrgId = (
      req.headers['x-org-id'] ||
      req.headers['x-tenant-id'] ||
      req.cookies?.forgecrm_active_org ||
      req.query?.org_id ||
      ''
    ).trim();

    let query = `
      SELECT o.id, o.name, o.slug, o.plan, o.settings, o.is_active, om.role AS member_role
        FROM coexistence.organizations o
        JOIN coexistence.organization_members om ON om.org_id = o.id
       WHERE om.user_id = $1 AND o.is_active = true
    `;
    const params = [userId];

    if (requestedOrgId) {
      query += ` AND (o.id::text = $2 OR o.slug = $2)`;
      params.push(requestedOrgId);
    }

    query += ` ORDER BY o.created_at ASC LIMIT 1`;

    const { rows } = await pool.query(query, params);

    if (rows.length > 0) {
      const org = rows[0];
      req.orgId = org.id;
      req.orgRole = org.member_role;
      req.org = {
        id: org.id,
        name: org.name,
        slug: org.slug,
        plan: org.plan,
        settings: org.settings || {},
        role: org.member_role,
      };
    } else {
      // Fallback: If user has no org membership, check if any org exists or create default membership
      const { rows: fallbackRows } = await pool.query(
        `SELECT id, name, slug, plan, settings FROM coexistence.organizations ORDER BY created_at ASC LIMIT 1`
      );
      if (fallbackRows.length > 0) {
        const defaultOrg = fallbackRows[0];
        // Auto-assign user as member to default org
        await pool.query(
          `INSERT INTO coexistence.organization_members (org_id, user_id, role)
           VALUES ($1, $2, 'member')
           ON CONFLICT (org_id, user_id) DO NOTHING`,
          [defaultOrg.id, userId]
        );
        req.orgId = defaultOrg.id;
        req.orgRole = 'member';
        req.org = {
          id: defaultOrg.id,
          name: defaultOrg.name,
          slug: defaultOrg.slug,
          plan: defaultOrg.plan,
          settings: defaultOrg.settings || {},
          role: 'member',
        };
      }
    }

    next();
  } catch (err) {
    console.error('[tenantContext] Error resolving tenant context:', err.message);
    next();
  }
}

/**
 * Middleware to restrict route to specific organization roles (e.g. 'owner', 'admin')
 */
function requireOrgRole(...allowedRoles) {
  return (req, res, next) => {
    if (!req.user) return res.status(401).json({ error: 'Unauthorized' });
    
    // Super-admins bypass org role checks
    if (req.user.role === 'admin') return next();

    if (!req.orgRole || !allowedRoles.includes(req.orgRole)) {
      return res.status(403).json({ error: 'Forbidden: Insufficient organization permissions' });
    }
    next();
  };
}

module.exports = {
  tenantContext,
  requireOrgRole,
};
