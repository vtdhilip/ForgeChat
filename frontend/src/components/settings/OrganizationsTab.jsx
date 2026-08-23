import { useState, useEffect } from 'react';
import {
  Building2, Plus, Users, MessageSquare, ExternalLink,
  Check, Loader2, Edit3, Trash2, ArrowRight, ShieldCheck, Sparkles
} from 'lucide-react';
import { api } from '../../api.js';
import { C, FONT, MONO } from '../../constants.js';

export default function OrganizationsTab({ user, onNavigate }) {
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [switchingId, setSwitchingId] = useState(null);

  const [newName, setNewName] = useState('');
  const [newPlan, setNewPlan] = useState('growth');
  const [newOrderPrefix, setNewOrderPrefix] = useState('ORD-');

  const loadOrgs = async () => {
    setLoading(true);
    try {
      const { organizations: list } = await api.organizations.list();
      setOrganizations(list || []);
    } catch (err) {
      console.error('Failed to load organizations:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrgs();
  }, []);

  const handleSwitch = async (orgId) => {
    setSwitchingId(orgId);
    try {
      await api.organizations.switch(orgId);
      window.location.reload();
    } catch (err) {
      alert(`Switch failed: ${err.message}`);
      setSwitchingId(null);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await api.organizations.create(newName.trim(), newPlan, { order_prefix: newOrderPrefix });
      setShowCreateModal(false);
      setNewName('');
      await loadOrgs();
    } catch (err) {
      alert(`Failed to create organization: ${err.message}`);
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 40, display: 'flex', alignItems: 'center', gap: 10, color: C.textMuted, fontFamily: FONT }}>
        <Loader2 size={18} className="animate-spin" /> Loading tenant organizations…
      </div>
    );
  }

  return (
    <div style={{ flex: 1, padding: '32px 40px 60px', overflowY: 'auto', fontFamily: FONT, background: '#F8F9FB' }}>
      <div style={{ maxWidth: 960, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <h1 style={{ fontSize: 24, fontWeight: 800, color: '#111827', margin: 0, letterSpacing: '-0.02em' }}>
                Brand & Tenant Workspaces
              </h1>
              <span style={{
                background: '#FFF0E6', color: '#FF5A00', fontSize: 11, fontWeight: 800,
                padding: '3px 8px', borderRadius: 99, letterSpacing: '0.04em', textTransform: 'uppercase',
              }}>
                Super Admin
              </span>
            </div>
            <p style={{ fontSize: 13, color: '#6B7280', margin: '4px 0 0' }}>
              Manage multi-tenant brand accounts, switch workspaces in 1-click, and configure per-brand isolation.
            </p>
          </div>

          <button
            onClick={() => setShowCreateModal(true)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              background: '#1A1A1A',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: 10,
              padding: '10px 18px',
              fontSize: 13.5,
              fontWeight: 700,
              cursor: 'pointer',
              fontFamily: FONT,
            }}
          >
            <Plus size={16} />
            <span>Create New Brand</span>
          </button>
        </div>

        {/* Organizations Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 18 }}>
          {organizations.map(org => {
            const isCurrent = org.isCurrent;
            return (
              <div
                key={org.id}
                style={{
                  background: '#FFFFFF',
                  border: isCurrent ? '2px solid #FF5A00' : '1px solid #ECEEF1',
                  borderRadius: 16,
                  padding: 22,
                  boxShadow: isCurrent ? '0 8px 24px rgba(255, 90, 0, 0.12)' : '0 1px 3px rgba(0,0,0,0.02)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  position: 'relative',
                }}
              >
                {isCurrent && (
                  <span style={{
                    position: 'absolute', top: -10, right: 16,
                    background: '#FF5A00', color: '#FFFFFF', fontSize: 10, fontWeight: 800,
                    padding: '2px 8px', borderRadius: 99, letterSpacing: '0.04em', textTransform: 'uppercase',
                  }}>
                    Active Workspace
                  </span>
                )}

                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                    <div style={{
                      width: 40, height: 40, borderRadius: 10,
                      background: isCurrent ? '#FFF0E6' : '#F3F4F6',
                      color: isCurrent ? '#FF5A00' : '#4B5563',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 18, fontWeight: 800,
                    }}>
                      {org.name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#111827' }}>
                        {org.name}
                      </h3>
                      <div style={{ fontSize: 11, color: '#9CA3AF', fontFamily: MONO }}>
                        slug: {org.slug}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 12, margin: '14px 0', fontSize: 12, color: '#6B7280' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Users size={14} color="#9CA3AF" />
                      <span>{org.memberCount || 1} members</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <MessageSquare size={14} color="#9CA3AF" />
                      <span>{org.waCount || 0} numbers</span>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 8, marginTop: 14, borderTop: '1px solid #F3F4F6', paddingTop: 14 }}>
                  {isCurrent ? (
                    <button
                      disabled
                      style={{
                        flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #E5E7EB',
                        background: '#FFF0E6', color: '#FF5A00', fontSize: 12.5, fontWeight: 700,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                      }}
                    >
                      <Check size={14} strokeWidth={3} /> Currently Working Here
                    </button>
                  ) : (
                    <button
                      onClick={() => handleSwitch(org.id)}
                      disabled={switchingId === org.id}
                      style={{
                        flex: 1, padding: '8px 12px', borderRadius: 8, border: 'none',
                        background: '#FF5A00', color: '#FFFFFF', fontSize: 12.5, fontWeight: 700,
                        cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                        boxShadow: '0 2px 8px rgba(255, 90, 0, 0.2)',
                      }}
                    >
                      {switchingId === org.id ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                      <span>Switch to this Brand</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Create Organization Modal */}
      {showCreateModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 300,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
        }}>
          <div style={{
            background: '#FFFFFF', borderRadius: 20, width: 'min(480px, 100%)',
            padding: 28, boxShadow: '0 20px 40px rgba(0,0,0,0.2)', fontFamily: FONT,
          }}>
            <h2 style={{ margin: '0 0 6px', fontSize: 20, fontWeight: 800, color: '#111827' }}>
              Create Brand Workspace
            </h2>
            <p style={{ margin: '0 0 20px', fontSize: 13, color: '#6B7280' }}>
              Add a new multi-tenant organization. All WhatsApp accounts, chat history, contacts, and orders will be completely isolated.
            </p>

            <form onSubmit={handleCreate}>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                  Brand / Company Name
                </label>
                <input
                  type="text"
                  required
                  value={newName}
                  onChange={e => setNewName(e.target.value)}
                  placeholder="e.g. Acme Stores"
                  style={{
                    width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #D1D5DB',
                    fontSize: 14, color: '#111827', boxSizing: 'border-box', outline: 'none',
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 24 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                    Order Prefix
                  </label>
                  <input
                    type="text"
                    value={newOrderPrefix}
                    onChange={e => setNewOrderPrefix(e.target.value)}
                    placeholder="ACM-"
                    style={{
                      width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #D1D5DB',
                      fontSize: 14, color: '#111827', boxSizing: 'border-box', outline: 'none',
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                    Plan
                  </label>
                  <select
                    value={newPlan}
                    onChange={e => setNewPlan(e.target.value)}
                    style={{
                      width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #D1D5DB',
                      fontSize: 14, color: '#111827', boxSizing: 'border-box', outline: 'none', background: '#fff',
                    }}
                  >
                    <option value="starter">Starter</option>
                    <option value="growth">Growth</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  style={{
                    padding: '10px 18px', borderRadius: 10, border: '1px solid #E5E7EB',
                    background: '#F9FAFB', color: '#374151', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  style={{
                    padding: '10px 20px', borderRadius: 10, border: 'none',
                    background: '#FF5A00', color: '#FFFFFF', fontSize: 13, fontWeight: 700,
                    cursor: creating ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                  }}
                >
                  {creating && <Loader2 size={14} className="animate-spin" />}
                  <span>Create Workspace</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
