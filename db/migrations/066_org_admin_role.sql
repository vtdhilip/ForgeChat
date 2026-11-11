-- 066_org_admin_role.sql
-- Introduce 'org_admin' for manually onboarded tenant admins (full workspace admin
-- inside their own organization, without Platform Super Admin access) and promote
-- existing org owners/admins from 'bda_sales' to 'org_admin'.
ALTER TABLE coexistence.forgecrm_users
  DROP CONSTRAINT IF EXISTS forgecrm_users_role_check;

ALTER TABLE coexistence.forgecrm_users
  ADD CONSTRAINT forgecrm_users_role_check
  CHECK (role IN ('admin', 'org_admin', 'bda_sales', 'viewer'));

UPDATE coexistence.forgecrm_users u
SET role = 'org_admin', updated_at = NOW()
FROM coexistence.organization_members om
WHERE om.user_id = u.id
  AND om.role IN ('owner', 'admin')
  AND u.role = 'bda_sales';
