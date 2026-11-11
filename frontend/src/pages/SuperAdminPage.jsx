import { useState, useEffect } from 'react';
import {
  Shield, Building2, Users, MessageSquare, Phone, Package, Plus,
  Settings, CheckCircle2, XCircle, AlertCircle, RefreshCw, LogIn,
  Sliders, Lock, Unlock, Database, Cpu, Megaphone, KanbanSquare,
  Zap, FileText, Image, Search, ChevronRight, X
} from 'lucide-react';
import { api } from '../api.js';
import { C, FONT } from '../constants.js';

export default function SuperAdminPage({ user, onOrgSwitch }) {
  const [stats, setStats] = useState(null);
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [showOnboardModal, setShowOnboardModal] = useState(false);
  const [showSwitchboardModal, setShowSwitchboardModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // New client form state
  const [newOrgForm, setNewOrgForm] = useState({
    name: '',
    plan: 'starter',
    contactEmail: '',
    contactPhone: '',
    adminUsername: '',
    adminPassword: '',
    modules: {
      chats: true,
      contacts: true,
      pipelines: false,
      broadcasts: false,
      templates: true,
      chatbots: false,
      agents: false,
      media: true,
      orders: false,
    },
    features: {
      allow_export: false,
      allow_byok_ai: false,
      allow_wa_config: false,
    },
    quotas: {
      max_users: 5,
      max_wa_numbers: 1,
      max_broadcasts: 1000,
      max_ai_tokens: 50000,
    },
  });

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewRes, orgsRes] = await Promise.all([
        api.organizations.getSuperAdminOverview().catch(() => ({ stats: {} })),
        api.organizations.list().catch(() => ({ organizations: [] })),
      ]);
      setStats(overviewRes.stats || {});
      setOrgs(orgsRes.organizations || []);
    } catch (err) {
      setError(err.message || 'Failed to load Super Admin dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleOpenSwitchboard = (org) => {
    setSelectedOrg({
      ...org,
      settings: org.settings || {},
      modules: {
        chats: org.settings?.modules?.chats !== false,
        contacts: org.settings?.modules?.contacts !== false,
        pipelines: !!org.settings?.modules?.pipelines,
        broadcasts: !!org.settings?.modules?.broadcasts,
        templates: org.settings?.modules?.templates !== false,
        chatbots: !!org.settings?.modules?.chatbots,
        agents: !!org.settings?.modules?.agents,
        media: org.settings?.modules?.media !== false,
        orders: !!org.settings?.modules?.orders,
      },
      features: {
        allow_export: !!org.settings?.features?.allow_export,
        allow_byok_ai: !!org.settings?.features?.allow_byok_ai,
        allow_wa_config: !!org.settings?.features?.allow_wa_config,
      },
      quotas: {
        max_users: org.settings?.quotas?.max_users || 5,
        max_wa_numbers: org.settings?.quotas?.max_wa_numbers || 1,
        max_broadcasts: org.settings?.quotas?.max_broadcasts || 1000,
        max_ai_tokens: org.settings?.quotas?.max_ai_tokens || 50000,
      },
    });
    setShowSwitchboardModal(true);
  };

  const handleSaveSwitchboard = async () => {
    if (!selectedOrg) return;
    setSaving(true);
    try {
      await api.organizations.updateClientModules(selectedOrg.id, {
        modules: selectedOrg.modules,
        features: selectedOrg.features,
        quotas: selectedOrg.quotas,
        plan: selectedOrg.plan,
        is_active: selectedOrg.isActive,
      });
      setSuccessMsg(`Features updated for ${selectedOrg.name}`);
      setShowSwitchboardModal(false);
      loadData();
      if (onOrgSwitch) onOrgSwitch(selectedOrg.id);
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setError(err.message || 'Failed to update features');
    } finally {
      setSaving(false);
    }
  };

  const handleOnboardSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.organizations.onboardClient(newOrgForm);
      setSuccessMsg(`Client '${newOrgForm.name}' onboarded successfully!`);
      setShowOnboardModal(false);
      // Reset form
      setNewOrgForm({
        name: '',
        plan: 'starter',
        contactEmail: '',
        contactPhone: '',
        adminUsername: '',
        adminPassword: '',
        modules: {
          chats: true,
          contacts: true,
          pipelines: false,
          broadcasts: false,
          templates: true,
          chatbots: false,
          agents: false,
          media: true,
          orders: false,
        },
        features: {
          allow_export: false,
          allow_byok_ai: false,
          allow_wa_config: false,
        },
        quotas: {
          max_users: 5,
          max_wa_numbers: 1,
          max_broadcasts: 1000,
          max_ai_tokens: 50000,
        },
      });
      loadData();
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setError(err.message || 'Failed to onboard client');
    } finally {
      setSaving(false);
    }
  };

  const handleImpersonate = async (orgId) => {
    try {
      await api.organizations.switch(orgId);
      if (onOrgSwitch) onOrgSwitch(orgId);
      window.location.hash = '#/home';
      window.location.reload();
    } catch (err) {
      setError(err.message || 'Failed to switch to organization');
    }
  };

  const filteredOrgs = orgs.filter(o =>
    (o.name || '').toLowerCase().includes(search.toLowerCase()) ||
    (o.slug || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ fontFamily: FONT, background: C.pageBg, minHeight: '100%', padding: '24px 32px' }}>
      {/* Top Banner */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 38, height: 38, borderRadius: 10,
              background: '#0ea5e9', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff'
            }}>
              <Shield size={22} />
            </div>
            <div>
              <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: C.textPrimary }}>
                Universal Super Admin Panel
              </h1>
              <p style={{ margin: 0, fontSize: 13, color: C.textMuted }}>
                Master control center for all multi-tenant client organizations, modules & quotas
              </p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={loadData}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
              borderRadius: 8, border: `1px solid ${C.border}`, background: '#fff',
              fontSize: 13, fontWeight: 500, cursor: 'pointer', color: C.textPrimary
            }}
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
          </button>
          <button
            onClick={() => setShowOnboardModal(true)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
              borderRadius: 8, border: 'none', background: C.primary, color: '#fff',
              fontSize: 13, fontWeight: 600, cursor: 'pointer'
            }}
          >
            <Plus size={16} /> Manual Onboard Client
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div style={{
          padding: '12px 16px', borderRadius: 8, background: '#fef2f2', border: '1px solid #fecaca',
          color: '#b91c1c', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18
        }}>
          <AlertCircle size={16} /> {error}
        </div>
      )}
      {successMsg && (
        <div style={{
          padding: '12px 16px', borderRadius: 8, background: '#f0fdf4', border: '1px solid #bbf7d0',
          color: '#15803d', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18
        }}>
          <CheckCircle2 size={16} /> {successMsg}
        </div>
      )}

      {/* Platform Overview Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 28 }}>
        {[
          { label: 'Total Clients', value: stats?.total_orgs ?? orgs.length, icon: Building2, color: '#6366f1' },
          { label: 'Active Clients', value: stats?.active_orgs ?? orgs.filter(o => o.isActive).length, icon: CheckCircle2, color: '#10b981' },
          { label: 'Active WABAs', value: stats?.total_wa_accounts ?? '-', icon: Phone, color: '#0ea5e9' },
          { label: 'Total Contacts', value: stats?.total_contacts ?? '-', icon: Users, color: '#f59e0b' },
          { label: 'Messages Routed', value: stats?.total_messages ?? '-', icon: MessageSquare, color: '#ec4899' },
          { label: 'Total Orders', value: stats?.total_orders ?? '-', icon: Package, color: '#8b5cf6' },
        ].map((card, idx) => {
          const Icon = card.icon;
          return (
            <div key={idx} style={{
              background: '#fff', borderRadius: 12, padding: '16px 20px',
              border: `1px solid ${C.border}`, boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 12, color: C.textMuted, fontWeight: 500 }}>{card.label}</span>
                <div style={{ width: 28, height: 28, borderRadius: 6, background: `${card.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: card.color }}>
                  <Icon size={16} />
                </div>
              </div>
              <div style={{ fontSize: 24, fontWeight: 700, color: C.textPrimary }}>
                {card.value}
              </div>
            </div>
          );
        })}
      </div>

      {/* Client Directory Header & Search */}
      <div style={{
        background: '#fff', borderRadius: 12, border: `1px solid ${C.border}`,
        overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
      }}>
        <div style={{
          padding: '16px 20px', borderBottom: `1px solid ${C.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between'
        }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: C.textPrimary }}>Client Organizations ({filteredOrgs.length})</h3>
            <span style={{ fontSize: 12, color: C.textMuted }}>Click "Switchboard" to toggle client modules or "Impersonate" to log in as client</span>
          </div>
          <div style={{ position: 'relative', width: 260 }}>
            <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: C.textMuted }} />
            <input
              type="text"
              placeholder="Search clients by name or slug..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: '100%', padding: '7px 10px 7px 32px', borderRadius: 8,
                border: `1px solid ${C.border}`, fontSize: 13, outline: 'none'
              }}
            />
          </div>
        </div>

        {/* Clients Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f8fafc', borderBottom: `1px solid ${C.border}`, color: C.textMuted, fontWeight: 600 }}>
                <th style={{ padding: '12px 18px' }}>Client Organization</th>
                <th style={{ padding: '12px 14px' }}>Slug</th>
                <th style={{ padding: '12px 14px' }}>Plan</th>
                <th style={{ padding: '12px 14px' }}>Status</th>
                <th style={{ padding: '12px 14px' }}>Phone Numbers</th>
                <th style={{ padding: '12px 14px' }}>Members</th>
                <th style={{ padding: '12px 18px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrgs.map(org => {
                const s = org.settings || {};
                const enabledModulesCount = Object.values(s.modules || {}).filter(Boolean).length;
                return (
                  <tr key={org.id} style={{ borderBottom: `1px solid ${C.border}` }}>
                    <td style={{ padding: '14px 18px', fontWeight: 600, color: C.textPrimary }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Building2 size={16} color={C.primary} />
                        <div>
                          <div>{org.name}</div>
                          <div style={{ fontSize: 11, color: C.textMuted, fontWeight: 400 }}>
                            {enabledModulesCount ? `${enabledModulesCount} modules enabled` : 'Default modules'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '14px 14px', fontFamily: 'monospace', color: C.textMuted }}>
                      {org.slug}
                    </td>
                    <td style={{ padding: '14px 14px' }}>
                      <span style={{
                        padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
                        background: org.plan === 'enterprise' ? '#fdf2f8' : org.plan === 'pro' ? '#eff6ff' : '#f1f5f9',
                        color: org.plan === 'enterprise' ? '#db2777' : org.plan === 'pro' ? '#2563eb' : '#475569'
                      }}>
                        {org.plan}
                      </span>
                    </td>
                    <td style={{ padding: '14px 14px' }}>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: 5, padding: '3px 8px',
                        borderRadius: 6, fontSize: 12, fontWeight: 500,
                        background: org.isActive ? '#ecfdf5' : '#fef2f2',
                        color: org.isActive ? '#059669' : '#dc2626'
                      }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: org.isActive ? '#10b981' : '#ef4444' }} />
                        {org.isActive ? 'Active' : 'Suspended'}
                      </span>
                    </td>
                    <td style={{ padding: '14px 14px', color: C.textPrimary }}>
                      {org.waCount || 0} / {s.quotas?.max_wa_numbers || 1}
                    </td>
                    <td style={{ padding: '14px 14px', color: C.textPrimary }}>
                      {org.memberCount || 1} / {s.quotas?.max_users || 5}
                    </td>
                    <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8 }}>
                        <button
                          onClick={() => handleOpenSwitchboard(org)}
                          title="Open Client Feature Switchboard"
                          style={{
                            display: 'flex', alignItems: 'center', gap: 5, padding: '6px 12px',
                            borderRadius: 6, border: `1px solid ${C.border}`, background: '#fff',
                            fontSize: 12, fontWeight: 600, cursor: 'pointer', color: C.textPrimary
                          }}
                        >
                          <Sliders size={13} /> Switchboard
                        </button>
                        <button
                          onClick={() => handleImpersonate(org.id)}
                          title="Log in to client workspace"
                          style={{
                            display: 'flex', alignItems: 'center', gap: 5, padding: '6px 12px',
                            borderRadius: 6, border: 'none', background: '#0284c7',
                            fontSize: 12, fontWeight: 600, cursor: 'pointer', color: '#fff'
                          }}
                        >
                          <LogIn size={13} /> Impersonate
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── CLIENT FEATURE SWITCHBOARD MODAL ───────────────────────────────── */}
      {showSwitchboardModal && selectedOrg && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20
        }}>
          <div style={{
            background: '#fff', borderRadius: 14, width: '100%', maxWidth: 720,
            maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)'
          }}>
            {/* Modal Header */}
            <div style={{
              padding: '20px 24px', borderBottom: `1px solid ${C.border}`,
              display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, background: '#fff', zIndex: 1
            }}>
              <div>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: C.textPrimary }}>
                  Feature Switchboard: {selectedOrg.name}
                </h2>
                <span style={{ fontSize: 12, color: C.textMuted }}>Toggle modules, security permissions, and quotas for this client</span>
              </div>
              <button
                onClick={() => setShowSwitchboardModal(false)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: C.textMuted }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ padding: '20px 24px' }}>
              {/* Client Status & Plan */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6, color: C.textPrimary }}>Account Status</label>
                  <select
                    value={selectedOrg.isActive ? 'active' : 'suspended'}
                    onChange={(e) => setSelectedOrg({ ...selectedOrg, isActive: e.target.value === 'active' })}
                    style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: `1px solid ${C.border}`, fontSize: 13 }}
                  >
                    <option value="active">Active (Access Allowed)</option>
                    <option value="suspended">Suspended (Access Blocked)</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6, color: C.textPrimary }}>Subscription Plan</label>
                  <select
                    value={selectedOrg.plan}
                    onChange={(e) => setSelectedOrg({ ...selectedOrg, plan: e.target.value })}
                    style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: `1px solid ${C.border}`, fontSize: 13 }}
                  >
                    <option value="starter">Starter Plan</option>
                    <option value="pro">Pro Plan</option>
                    <option value="enterprise">Enterprise Plan</option>
                  </select>
                </div>
              </div>

              {/* Module Toggles */}
              <div style={{ marginBottom: 24 }}>
                <h4 style={{ fontSize: 14, fontWeight: 700, color: C.textPrimary, margin: '0 0 12px 0' }}>
                  Client Accessible Modules
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 }}>
                  {[
                    { key: 'chats', label: 'Shared Team Inbox', icon: MessageSquare },
                    { key: 'contacts', label: 'Contacts & CRM', icon: Users },
                    { key: 'pipelines', label: 'Sales Deals Pipeline', icon: KanbanSquare },
                    { key: 'broadcasts', label: 'Bulk Broadcasts', icon: Megaphone },
                    { key: 'templates', label: 'Template Builder', icon: FileText },
                    { key: 'chatbots', label: 'Flow Automations', icon: Zap },
                    { key: 'agents', label: 'Autonomous AI Agents', icon: Cpu },
                    { key: 'media', label: 'Media Library', icon: Image },
                    { key: 'orders', label: 'Orders & Tracking', icon: Package },
                  ].map(mod => {
                    const Icon = mod.icon;
                    const isEnabled = !!selectedOrg.modules[mod.key];
                    return (
                      <div
                        key={mod.key}
                        onClick={() => setSelectedOrg({
                          ...selectedOrg,
                          modules: { ...selectedOrg.modules, [mod.key]: !isEnabled }
                        })}
                        style={{
                          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                          padding: '10px 14px', borderRadius: 8, cursor: 'pointer',
                          border: `1px solid ${isEnabled ? '#22c55e' : C.border}`,
                          background: isEnabled ? '#f0fdf4' : '#f8fafc',
                          transition: 'all .15s ease'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <Icon size={16} color={isEnabled ? '#16a34a' : C.textMuted} />
                          <span style={{ fontSize: 12, fontWeight: 600, color: isEnabled ? '#15803d' : C.textPrimary }}>
                            {mod.label}
                          </span>
                        </div>
                        <input
                          type="checkbox"
                          checked={isEnabled}
                          readOnly
                          style={{ cursor: 'pointer' }}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Security & Capability Flags */}
              <div style={{ marginBottom: 24 }}>
                <h4 style={{ fontSize: 14, fontWeight: 700, color: C.textPrimary, margin: '0 0 12px 0' }}>
                  Security & Capability Guardrails
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderRadius: 8, border: `1px solid ${C.border}`, background: '#f8fafc' }}>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary }}>Allow Contact CSV Exports</div>
                      <div style={{ fontSize: 11, color: C.textMuted }}>If disabled, client users cannot download customer contact spreadsheets</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={selectedOrg.features.allow_export}
                      onChange={(e) => setSelectedOrg({
                        ...selectedOrg,
                        features: { ...selectedOrg.features, allow_export: e.target.checked }
                      })}
                    />
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderRadius: 8, border: `1px solid ${C.border}`, background: '#f8fafc' }}>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary }}>Allow Custom AI Model Keys (BYOK)</div>
                      <div style={{ fontSize: 11, color: C.textMuted }}>Allow client to input their own OpenAI/Anthropic API keys</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={selectedOrg.features.allow_byok_ai}
                      onChange={(e) => setSelectedOrg({
                        ...selectedOrg,
                        features: { ...selectedOrg.features, allow_byok_ai: e.target.checked }
                      })}
                    />
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderRadius: 8, border: `1px solid ${C.border}`, background: '#f8fafc' }}>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary }}>Allow WhatsApp Credentials Edit</div>
                      <div style={{ fontSize: 11, color: C.textMuted }}>If disabled, WhatsApp API tokens and Webhook configs are locked</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={selectedOrg.features.allow_wa_config}
                      onChange={(e) => setSelectedOrg({
                        ...selectedOrg,
                        features: { ...selectedOrg.features, allow_wa_config: e.target.checked }
                      })}
                    />
                  </label>
                </div>
              </div>

              {/* Resource Quotas */}
              <div>
                <h4 style={{ fontSize: 14, fontWeight: 700, color: C.textPrimary, margin: '0 0 12px 0' }}>
                  Resource Quotas & Caps
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 500, marginBottom: 4, color: C.textMuted }}>Max Team Member Seats</label>
                    <input
                      type="number"
                      value={selectedOrg.quotas.max_users}
                      onChange={(e) => setSelectedOrg({
                        ...selectedOrg,
                        quotas: { ...selectedOrg.quotas, max_users: parseInt(e.target.value, 10) || 1 }
                      })}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: `1px solid ${C.border}`, fontSize: 13 }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 500, marginBottom: 4, color: C.textMuted }}>Max WhatsApp Phone Numbers</label>
                    <input
                      type="number"
                      value={selectedOrg.quotas.max_wa_numbers}
                      onChange={(e) => setSelectedOrg({
                        ...selectedOrg,
                        quotas: { ...selectedOrg.quotas, max_wa_numbers: parseInt(e.target.value, 10) || 1 }
                      })}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: `1px solid ${C.border}`, fontSize: 13 }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 500, marginBottom: 4, color: C.textMuted }}>Monthly Broadcast Limit</label>
                    <input
                      type="number"
                      value={selectedOrg.quotas.max_broadcasts}
                      onChange={(e) => setSelectedOrg({
                        ...selectedOrg,
                        quotas: { ...selectedOrg.quotas, max_broadcasts: parseInt(e.target.value, 10) || 0 }
                      })}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: `1px solid ${C.border}`, fontSize: 13 }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 500, marginBottom: 4, color: C.textMuted }}>Monthly AI Token Allowance</label>
                    <input
                      type="number"
                      value={selectedOrg.quotas.max_ai_tokens}
                      onChange={(e) => setSelectedOrg({
                        ...selectedOrg,
                        quotas: { ...selectedOrg.quotas, max_ai_tokens: parseInt(e.target.value, 10) || 0 }
                      })}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: `1px solid ${C.border}`, fontSize: 13 }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div style={{
              padding: '16px 24px', borderTop: `1px solid ${C.border}`, background: '#f8fafc',
              display: 'flex', justifyContent: 'flex-end', gap: 10, borderRadius: '0 0 14px 14px'
            }}>
              <button
                onClick={() => setShowSwitchboardModal(false)}
                style={{
                  padding: '8px 16px', borderRadius: 8, border: `1px solid ${C.border}`,
                  background: '#fff', fontSize: 13, fontWeight: 500, cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveSwitchboard}
                disabled={saving}
                style={{
                  padding: '8px 20px', borderRadius: 8, border: 'none',
                  background: C.primary, color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer'
                }}
              >
                {saving ? 'Saving Changes...' : 'Save Features & Quotas'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MANUAL ONBOARDING MODAL ───────────────────────────────────────── */}
      {showOnboardModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20
        }}>
          <div style={{
            background: '#fff', borderRadius: 14, width: '100%', maxWidth: 640,
            maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)'
          }}>
            <form onSubmit={handleOnboardSubmit}>
              <div style={{
                padding: '20px 24px', borderBottom: `1px solid ${C.border}`,
                display: 'flex', alignItems: 'center', justifyContent: 'space-between'
              }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: C.textPrimary }}>
                    Manual Onboard Client
                  </h2>
                  <span style={{ fontSize: 12, color: C.textMuted }}>Provision new client organization, owner credentials & initial modules</span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowOnboardModal(false)}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: C.textMuted }}
                >
                  <X size={20} />
                </button>
              </div>

              <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 5, color: C.textPrimary }}>Business / Organization Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Apex Health Clinic"
                    value={newOrgForm.name}
                    onChange={(e) => setNewOrgForm({ ...newOrgForm, name: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: `1px solid ${C.border}`, fontSize: 13 }}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 5, color: C.textPrimary }}>Client Contact Email *</label>
                    <input
                      type="email"
                      required
                      placeholder="owner@apexhealth.com"
                      value={newOrgForm.contactEmail}
                      onChange={(e) => setNewOrgForm({ ...newOrgForm, contactEmail: e.target.value })}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: `1px solid ${C.border}`, fontSize: 13 }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 5, color: C.textPrimary }}>Contact Phone</label>
                    <input
                      type="text"
                      placeholder="+91 98765 43210"
                      value={newOrgForm.contactPhone}
                      onChange={(e) => setNewOrgForm({ ...newOrgForm, contactPhone: e.target.value })}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: `1px solid ${C.border}`, fontSize: 13 }}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 5, color: C.textPrimary }}>Initial Admin Username</label>
                    <input
                      type="text"
                      placeholder="admin_apex"
                      value={newOrgForm.adminUsername}
                      onChange={(e) => setNewOrgForm({ ...newOrgForm, adminUsername: e.target.value })}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: `1px solid ${C.border}`, fontSize: 13 }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 5, color: C.textPrimary }}>Initial Password</label>
                    <input
                      type="password"
                      placeholder="••••••••"
                      value={newOrgForm.adminPassword}
                      onChange={(e) => setNewOrgForm({ ...newOrgForm, adminPassword: e.target.value })}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: `1px solid ${C.border}`, fontSize: 13 }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 5, color: C.textPrimary }}>Initial Plan</label>
                  <select
                    value={newOrgForm.plan}
                    onChange={(e) => setNewOrgForm({ ...newOrgForm, plan: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: `1px solid ${C.border}`, fontSize: 13 }}
                  >
                    <option value="starter">Starter</option>
                    <option value="pro">Pro</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </div>
              </div>

              <div style={{
                padding: '16px 24px', borderTop: `1px solid ${C.border}`, background: '#f8fafc',
                display: 'flex', justifyContent: 'flex-end', gap: 10, borderRadius: '0 0 14px 14px'
              }}>
                <button
                  type="button"
                  onClick={() => setShowOnboardModal(false)}
                  style={{
                    padding: '8px 16px', borderRadius: 8, border: `1px solid ${C.border}`,
                    background: '#fff', fontSize: 13, fontWeight: 500, cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  style={{
                    padding: '8px 20px', borderRadius: 8, border: 'none',
                    background: C.primary, color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer'
                  }}
                >
                  {saving ? 'Provisioning...' : 'Provision Client'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
