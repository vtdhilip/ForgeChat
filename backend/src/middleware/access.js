// Role / permission enforcement and audit logging.
//
// The JWT only carries { id, username, displayName, role } — for permission
// checks against the optional per-user overrides we re-load the row.

const pool = require('../db');
const { isAdmin, hasPermission } = require('../permissions');

function adminOnly(req, res, next) {
  if (!isAdmin(req.user)) {
    return res.status(403).json({ error: 'Admin access required' });
  }
  next();
}

// requirePermission(page): gates a route on whether the current user can
// reach `page`. Loads the user row fresh so per-user overrides are honoured.
function requirePermission(page) {
  return async (req, res, next) => {
    try {
      if (isAdmin(req.user)) return next();
      const { rows } = await pool.query(
        `SELECT role, permissions FROM coexistence.forgecrm_users WHERE id = $1`,
        [req.user.id]
      );
      const u = rows[0];
      if (!u) return res.status(401).json({ error: 'User not found' });
      if (!hasPermission({ role: u.role, permissions: u.permissions }, page)) {
        return res.status(403).json({ error: 'Forbidden' });
      }
      next();
    } catch (err) {
      console.error('[access] requirePermission error:', err.message);
      res.status(500).json({ error: 'Permission check failed' });
    }
  };
}

// Look up the WA numbers a user is allowed to see. Admin gets null
// (meaning "no scoping needed"). Non-admins get the array — may be empty.
async function userWaNumbers(userId) {
  const { rows } = await pool.query(
    `SELECT wa_number FROM coexistence.user_wa_assignments WHERE user_id = $1`,
    [userId]
  );
  return rows.map(r => r.wa_number);
}

// Build a SQL fragment + params to scope a query to "rows visible to req.user".
// Used by read endpoints (messages, contacts, numbers). The fragment is a
// boolean expression; the caller injects it into their WHERE.
//
//   const scope = await buildWaScope(req, '{table_alias}', paramIndex);
//   if (scope.sql) { whereClauses.push(scope.sql); params.push(...scope.params); }
//
// `tableAlias.wa_number` and `tableAlias.contact_number` must exist on the
// table being scoped (true for chat_history, contacts, and the derived
// messages/numbers/contact-names queries).
//
// Returns { sql, params }. `sql` is empty string when scoping is unnecessary
// (admin, or non-scopable route).
async function buildWaScope(req, tableAlias, startParamIndex) {
  if (isAdmin(req.user)) return { sql: '', params: [] };
  const waNumbers = await userWaNumbers(req.user.id);
  if (waNumbers.length === 0) {
    // BDA with no assignments → see nothing
    return { sql: 'FALSE', params: [] };
  }
  // Scope: row's wa_number is in the user's list,
  //   OR the contact has an explicit assigned_user_id matching this user
  //      (handled via subquery against the contacts table).
  const waParam = `$${startParamIndex}`;
  const userParam = `$${startParamIndex + 1}`;
  const sql = `(
    ${tableAlias}.wa_number = ANY(${waParam}::text[])
    OR EXISTS (
      SELECT 1 FROM coexistence.contacts c
       WHERE c.wa_number = ${tableAlias}.wa_number
         AND c.contact_number = ${tableAlias}.contact_number
         AND c.assigned_user_id = ${userParam}
    )
  )`;
  return { sql, params: [waNumbers, req.user.id] };
}

// Convenience: assert the current user has access to a specific wa_number.
// Scoped to tenant organization if req.orgId is set.
async function assertWaAccess(req, res, waNumber) {
  const clean = String(waNumber || '').replace(/\D/g, '');
  const params = [clean];
  let orgClause = '';
  if (req.orgId) {
    params.push(req.orgId);
    orgClause = `AND (org_id = $${params.length} OR org_id IS NULL)`;
  }

  // Account check: ensure the WhatsApp account belongs to caller's org
  if (req.orgId) {
    const { rows: accRows } = await pool.query(
      `SELECT 1 FROM coexistence.whatsapp_accounts
        WHERE regexp_replace(display_phone_number, '[^0-9]', '', 'g') = $1
          AND (org_id = $2 OR org_id IS NULL) LIMIT 1`,
      [clean, req.orgId]
    );
    if (accRows.length === 0) {
      res.status(403).json({ error: 'You do not have access to this WhatsApp number' });
      return false;
    }
  }

  if (isAdmin(req.user) || req.orgRole === 'owner' || req.orgRole === 'admin') return true;

  params.push(req.user.id);
  const { rows } = await pool.query(
    `SELECT 1 FROM coexistence.contacts
      WHERE wa_number = $1 ${orgClause} AND assigned_user_id = $${params.length} LIMIT 1`,
    params
  );
  if (rows.length === 0) {
    res.status(403).json({ error: 'You do not have access to this WhatsApp number' });
    return false;
  }
  return true;
}

// Per-conversation access: the (wa_number, contact_number) pair must belong to
// the caller's active tenant and assigned user (if non-admin).
async function assertContactAccess(req, res, waNumber, contactNumber) {
  const cleanWa = String(waNumber || '').replace(/\D/g, '');
  const cleanContact = String(contactNumber || '').replace(/\D/g, '');
  const params = [cleanWa, cleanContact];
  let orgClause = '';
  if (req.orgId) {
    params.push(req.orgId);
    orgClause = `AND (org_id = $${params.length} OR org_id IS NULL)`;
  }

  // If org admin / global admin: must still belong to tenant's org if req.orgId is active
  if (isAdmin(req.user) || req.orgRole === 'owner' || req.orgRole === 'admin') {
    if (!req.orgId) return true;
    const { rows } = await pool.query(
      `SELECT 1 FROM coexistence.contacts
        WHERE wa_number = $1 AND contact_number = $2 ${orgClause} LIMIT 1`,
      params
    );
    if (rows.length === 0) {
      const { rows: anyRows } = await pool.query(
        `SELECT 1 FROM coexistence.contacts WHERE wa_number = $1 AND contact_number = $2 LIMIT 1`,
        [cleanWa, cleanContact]
      );
      if (anyRows.length > 0) {
        res.status(403).json({ error: 'You do not have access to this conversation' });
        return false;
      }
    }
    return true;
  }

  params.push(req.user.id);
  const { rows } = await pool.query(
    `SELECT 1 FROM coexistence.contacts
      WHERE wa_number = $1 AND contact_number = $2 ${orgClause} AND assigned_user_id = $${params.length} LIMIT 1`,
    params
  );
  if (rows.length === 0) {
    res.status(403).json({ error: 'You do not have access to this conversation' });
    return false;
  }
  return true;
}

// Append-only audit log of admin-sensitive actions.
async function auditLog({ actor, action, targetType = null, targetId = null, payload = null }) {
  try {
    await pool.query(
      `INSERT INTO coexistence.user_audit_log
         (actor_user_id, actor_username, action, target_type, target_id, payload)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [
        actor?.id || null,
        actor?.username || null,
        action,
        targetType,
        targetId != null ? String(targetId) : null,
        payload ? JSON.stringify(payload) : null,
      ]
    );
  } catch (err) {
    // Audit logging must never break the calling request
    console.error('[audit] write failed:', err.message);
  }
}

module.exports = {
  adminOnly,
  requirePermission,
  userWaNumbers,
  buildWaScope,
  assertWaAccess,
  assertContactAccess,
  auditLog,
};
