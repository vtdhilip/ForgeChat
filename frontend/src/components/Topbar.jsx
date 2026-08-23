import { useState, useRef, useEffect } from 'react';
import {
  Info, LogOut, Settings, AlertTriangle, Star, Github,
  Search, Bell, Mail,
} from 'lucide-react';
import { C, FONT } from '../constants.js';
import { api } from '../api.js';

// This project's GitHub repo — powers the star counter in the header.
const GITHUB_REPO = 'Forgemind-git/ForgeChat';
const GITHUB_REPO_URL = `https://github.com/${GITHUB_REPO}`;

export default function Topbar({ user, onLogout, onNavigate }) {
  const [userOpen, setUserOpen] = useState(false);
  const [unhealthyAccounts, setUnhealthyAccounts] = useState([]);
  const [stars, setStars] = useState(null);
  const ref = useRef(null);

  // Fetch the repo's live star count from the public GitHub API.
  useEffect(() => {
    let cancelled = false;
    fetch(`https://api.github.com/repos/${GITHUB_REPO}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (!cancelled && d && typeof d.stargazers_count === 'number') setStars(d.stargazers_count); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setUserOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      api.whatsappAccounts.list()
        .then(accs => { if (!cancelled) setUnhealthyAccounts(accs.filter(a => a.healthStatus === 'invalid_token')); })
        .catch(() => {});
    };
    check();
    const t = setInterval(check, 60000);
    return () => { cancelled = true; clearInterval(t); };
  }, []);

  return (
    <>
    {unhealthyAccounts.length > 0 && (
      <div
        onClick={() => onNavigate('admin-settings')}
        style={{
          background: '#FF5A00', color: '#fff', padding: '8px 16px',
          fontSize: 12, fontFamily: FONT, display: 'flex', alignItems: 'center',
          justifyContent: 'center', gap: 8, cursor: 'pointer', fontWeight: 600,
        }}
      >
        <AlertTriangle size={14} />
        <span>
          Access token expired for {unhealthyAccounts.map(a => a.displayName).join(', ')} — click to update in Settings → WhatsApp Accounts
        </span>
      </div>
    )}
    <div style={{
      height: 64,
      background: '#FFFFFF',
      display: 'flex',
      alignItems: 'center',
      paddingLeft: 0,
      paddingRight: 24,
      borderBottom: `1px solid ${C.headerBorder}`,
      flexShrink: 0,
      zIndex: 100,
      position: 'relative',
    }}>
      {/* Logo area — aligns with sidebar */}
      <button
        onClick={() => onNavigate('home')}
        style={{
          width: 240,
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          paddingLeft: 20,
          gap: 10,
          borderRight: `1px solid ${C.headerBorder}`,
          height: '100%',
          background: 'transparent',
          border: 'none',
          borderRightWidth: 1,
          borderRightStyle: 'solid',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <div style={{
          width: 34,
          height: 34,
          borderRadius: 10,
          background: '#FF5A00',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#FFFFFF',
          fontWeight: 900,
          fontSize: 18,
          boxShadow: '0 4px 12px rgba(255, 90, 0, 0.28)',
        }}>
          ⚡
        </div>
        <div style={{ lineHeight: 1.1 }}>
          <div style={{
            fontSize: 16,
            fontWeight: 800,
            color: '#111827',
            fontFamily: FONT,
            letterSpacing: '-0.02em',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
          }}>
            Synaptic
            <span style={{
              background: '#FFF0E6',
              color: '#FF5A00',
              padding: '2px 7px',
              borderRadius: 6,
              fontSize: 11,
              fontWeight: 800,
              letterSpacing: '0.04em',
              display: 'inline-block',
            }}>CHAT</span>
          </div>
        </div>
      </button>

      {/* Tenant / Organization Switcher */}
      <OrgSwitcher user={user} onNavigate={onNavigate} />

      {/* Center Search bar matching reference image */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        background: '#F8F9FA',
        border: '1px solid #E5E7EB',
        borderRadius: 12,
        padding: '7px 14px',
        gap: 10,
        width: 320,
        marginLeft: 24,
      }}>
        <Search size={16} color="#9CA3AF" />
        <input
          type="text"
          placeholder="Search task, chat, or contact..."
          style={{
            border: 'none',
            background: 'transparent',
            fontSize: 13,
            color: '#111827',
            outline: 'none',
            width: '100%',
            fontFamily: FONT,
          }}
        />
        <span style={{
          fontSize: 11,
          fontWeight: 700,
          color: '#9CA3AF',
          background: '#FFFFFF',
          border: '1px solid #E5E7EB',
          borderRadius: 6,
          padding: '2px 6px',
          fontFamily: FONT,
          flexShrink: 0,
        }}>⌘ F</span>
      </div>

      <div style={{ flex: 1 }} />

      {/* Right controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {/* GitHub stars pill */}
        <button
          onClick={() => window.open(GITHUB_REPO_URL, '_blank', 'noopener,noreferrer')}
          title="Star Synaptic Chat on GitHub"
          style={{
            height: 38, borderRadius: 10, padding: '0 12px',
            background: '#F8F9FA', border: `1px solid #E5E7EB`,
            cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 7,
            color: '#374151', fontFamily: FONT, fontSize: 13, fontWeight: 600,
          }}
        >
          <Github size={16} color="#374151" />
          <Star size={14} color="#F59E0B" fill="#F59E0B" />
          <span style={{ minWidth: 8, textAlign: 'left' }}>{stars == null ? '—' : stars}</span>
        </button>

        {/* Circular icon buttons matching image */}
        <button
          onClick={() => onNavigate('chats')}
          title="Messages"
          style={{
            width: 38,
            height: 38,
            borderRadius: '50%',
            background: '#F8F9FA',
            border: `1px solid #E5E7EB`,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#4B5563',
            transition: 'background 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.background = '#F3F4F6'}
          onMouseLeave={e => e.currentTarget.style.background = '#F8F9FA'}
        >
          <Mail size={16} />
        </button>

        <button
          onClick={() => onNavigate('about')}
          title="About Us"
          style={{
            width: 38,
            height: 38,
            borderRadius: '50%',
            background: '#F8F9FA',
            border: `1px solid #E5E7EB`,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#4B5563',
            transition: 'background 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.background = '#F3F4F6'}
          onMouseLeave={e => e.currentTarget.style.background = '#F8F9FA'}
        >
          <Bell size={16} />
        </button>

        {/* User profile pill matching top right of reference image */}
        <div ref={ref} style={{ position: 'relative' }}>
          <div
            onClick={() => setUserOpen(p => !p)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              cursor: 'pointer',
              padding: '4px 10px 4px 6px',
              borderRadius: 12,
              background: userOpen ? '#F3F4F6' : 'transparent',
              border: `1px solid ${userOpen ? '#E5E7EB' : 'transparent'}`,
              transition: 'all .15s',
            }}
            onMouseEnter={e => { if (!userOpen) e.currentTarget.style.background = '#F8F9FA'; }}
            onMouseLeave={e => { if (!userOpen) e.currentTarget.style.background = 'transparent'; }}
          >
            <div style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              background: '#FF5A00',
              color: '#FFFFFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 15,
              fontWeight: 800,
              fontFamily: FONT,
              boxShadow: '0 2px 8px rgba(255, 90, 0, 0.2)',
            }}>
              {(user.displayName || user.username).charAt(0).toUpperCase()}
            </div>
            <div style={{ textAlign: 'left', lineHeight: 1.25 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#111827', fontFamily: FONT }}>
                {user.displayName || user.username}
              </div>
              <div style={{ fontSize: 11, color: '#6B7280', fontFamily: FONT }}>
                {user.email || 'admin@synaptic.chat'}
              </div>
            </div>
          </div>

          {userOpen && (
            <div style={{
              position: 'absolute',
              top: 50,
              right: 0,
              background: '#FFFFFF',
              border: `1px solid ${C.border}`,
              borderRadius: 12,
              boxShadow: C.shadowLg,
              padding: 6,
              minWidth: 200,
              zIndex: 200,
              fontFamily: FONT,
            }}>
              <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, marginBottom: 4 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: C.text }}>
                  {user.displayName || user.username}
                </div>
                <div style={{ fontSize: 11, color: '#FF5A00', fontWeight: 600, marginTop: 2 }}>
                  {user.role === 'admin' ? 'Administrator' : user.role}
                </div>
              </div>
              <button
                onClick={() => { setUserOpen(false); onNavigate('admin-settings'); }}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '9px 12px',
                  borderRadius: 8,
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  color: C.text,
                  fontSize: 13,
                  fontWeight: 500,
                  fontFamily: FONT,
                }}
                onMouseEnter={e => e.currentTarget.style.background = '#F3F4F6'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <Settings size={15} />
                Settings
              </button>
              <button
                onClick={() => { setUserOpen(false); onLogout(); }}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '9px 12px',
                  borderRadius: 8,
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#EF4444',
                  fontSize: 13,
                  fontWeight: 600,
                  fontFamily: FONT,
                }}
                onMouseEnter={e => e.currentTarget.style.background = '#FEF2F2'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <LogOut size={15} />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
    </>
  );
}

function OrgSwitcher({ user, onNavigate }) {
  const [open, setOpen] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [newOrgPrefix, setNewOrgPrefix] = useState('');
  const [loading, setLoading] = useState(false);
  const ref = useRef(null);

  const orgs = user?.organizations || [];
  const activeOrg = user?.activeOrg || orgs[0] || { name: 'LINNDEN' };

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleSwitch = async (orgId) => {
    try {
      await api.organizations.switch(orgId);
      window.location.reload();
    } catch (err) {
      alert('Failed to switch organization: ' + err.message);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newOrgName.trim()) return;
    setLoading(true);
    try {
      const res = await api.organizations.create(newOrgName.trim(), 'starter', {
        order_prefix: (newOrgPrefix.trim() || newOrgName.slice(0, 3).toUpperCase()) + '-',
        currency: 'INR',
      });
      if (res.organization?.id) {
        await api.organizations.switch(res.organization.id);
        window.location.reload();
      }
    } catch (err) {
      alert('Error creating organization: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div ref={ref} style={{ position: 'relative', marginLeft: 16 }}>
      <button
        onClick={() => setOpen(p => !p)}
        style={{
          height: 36,
          borderRadius: 8,
          padding: '0 12px',
          background: open ? C.headerSurface : 'rgba(255,255,255,0.06)',
          border: `1.5px solid ${open ? C.primary : C.headerBorder}`,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          color: C.headerText,
          fontFamily: FONT,
          fontSize: 13,
          fontWeight: 600,
          transition: 'all 0.15s ease',
        }}
      >
        <span style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: '#FF5A00',
          display: 'inline-block',
        }} />
        <span style={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {activeOrg.name}
        </span>
        <span style={{
          fontSize: 10,
          background: 'rgba(255,255,255,0.1)',
          padding: '2px 6px',
          borderRadius: 4,
          textTransform: 'uppercase',
          fontWeight: 700,
          color: '#9CA3AF',
        }}>
          {activeOrg.role || 'Admin'}
        </span>
        <span style={{ fontSize: 10, opacity: 0.6, marginLeft: 2 }}>▾</span>
      </button>

      {open && (
        <div style={{
          position: 'absolute',
          top: 44,
          left: 0,
          width: 260,
          background: C.cardBg,
          border: `1px solid ${C.border}`,
          borderRadius: 10,
          boxShadow: '0 8px 30px rgba(0,0,0,0.18)',
          zIndex: 200,
          padding: 8,
          fontFamily: FONT,
        }}>
          <div style={{
            fontSize: 11,
            fontWeight: 700,
            color: C.textMuted,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            padding: '6px 10px',
          }}>
            Organizations / Tenants
          </div>

          <div style={{ maxHeight: 200, overflowY: 'auto' }}>
            {orgs.map(org => {
              const isCurrent = org.id === activeOrg.id;
              return (
                <button
                  key={org.id}
                  onClick={() => { setOpen(false); if (!isCurrent) handleSwitch(org.id); }}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 10px',
                    borderRadius: 6,
                    background: isCurrent ? 'rgba(79, 70, 229, 0.08)' : 'transparent',
                    border: 'none',
                    cursor: isCurrent ? 'default' : 'pointer',
                    color: isCurrent ? C.primary : C.text,
                    fontSize: 13,
                    fontWeight: isCurrent ? 700 : 500,
                    fontFamily: FONT,
                    textAlign: 'left',
                    transition: 'background 0.12s',
                  }}
                  onMouseEnter={e => { if (!isCurrent) e.currentTarget.style.background = C.hoverBg; }}
                  onMouseLeave={e => { if (!isCurrent) e.currentTarget.style.background = 'transparent'; }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                    <span style={{ fontSize: 15 }}>🏢</span>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {org.name}
                    </span>
                  </div>
                  {isCurrent && <span style={{ color: C.primary, fontWeight: 800, fontSize: 13 }}>✓</span>}
                </button>
              );
            })}
          </div>

          <div style={{ height: 1, background: C.border, margin: '6px 0' }} />

          <button
            onClick={() => { setOpen(false); setShowCreateModal(true); }}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 10px',
              borderRadius: 6,
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: C.primary,
              fontSize: 13,
              fontWeight: 600,
              fontFamily: FONT,
              textAlign: 'left',
            }}
            onMouseEnter={e => e.currentTarget.style.background = C.hoverBg}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <span>➕</span>
            <span>New Organization</span>
          </button>
        </div>
      )}

      {/* Create Organization Modal */}
      {showCreateModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            background: C.cardBg,
            borderRadius: 14,
            width: 420,
            padding: 24,
            border: `1px solid ${C.border}`,
            boxShadow: '0 20px 40px rgba(0,0,0,0.3)',
            fontFamily: FONT,
          }}>
            <h3 style={{ margin: '0 0 6px 0', fontSize: 18, color: C.text, fontWeight: 700 }}>
              Create New Organization
            </h3>
            <p style={{ margin: '0 0 20px 0', fontSize: 13, color: C.textMuted }}>
              Each organization has its own isolated WhatsApp numbers, contacts, orders, and team members.
            </p>

            <form onSubmit={handleCreate}>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>
                  Organization / Brand Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Acme Brands"
                  value={newOrgName}
                  onChange={e => setNewOrgName(e.target.value)}
                  required
                  autoFocus
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: `1px solid ${C.border}`,
                    background: C.inputBg,
                    color: C.text,
                    fontSize: 14,
                    fontFamily: FONT,
                    outline: 'none',
                  }}
                />
              </div>

              <div style={{ marginBottom: 24 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>
                  Order Prefix (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. ACM-"
                  value={newOrgPrefix}
                  onChange={e => setNewOrgPrefix(e.target.value)}
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: `1px solid ${C.border}`,
                    background: C.inputBg,
                    color: C.text,
                    fontSize: 14,
                    fontFamily: FONT,
                    outline: 'none',
                  }}
                />
                <span style={{ fontSize: 11, color: C.textMuted, marginTop: 4, display: 'block' }}>
                  Orders will be numbered sequentially: e.g. {newOrgPrefix ? newOrgPrefix.toUpperCase() : 'ACM-'}1001, {newOrgPrefix ? newOrgPrefix.toUpperCase() : 'ACM-'}1002
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  style={{
                    padding: '9px 16px',
                    borderRadius: 8,
                    border: `1px solid ${C.border}`,
                    background: 'transparent',
                    color: C.text,
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: 'pointer',
                    fontFamily: FONT,
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !newOrgName.trim()}
                  style={{
                    padding: '9px 20px',
                    borderRadius: 8,
                    border: 'none',
                    background: C.primary,
                    color: '#fff',
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    fontFamily: FONT,
                    opacity: loading || !newOrgName.trim() ? 0.6 : 1,
                  }}
                >
                  {loading ? 'Creating...' : 'Create Organization'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
