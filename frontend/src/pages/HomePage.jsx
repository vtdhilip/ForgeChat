import { useState, useEffect } from 'react';
import {
  Users, UserPlus, Inbox, Send, Activity, Zap, MessageCircle,
  Megaphone, AlertTriangle, ArrowUpRight, ArrowDownRight,
  FileText, Trophy, RefreshCw, X, Plus, Play, Pause, Square,
  CheckCircle2, Clock, Calendar, Check, ExternalLink
} from 'lucide-react';
import { C, FONT, MONO } from '../constants.js';
import { api } from '../api.js';
import { usePolling } from '../hooks/usePolling.js';

const RANGES = [
  { key: '7d', label: '7 days' },
  { key: '30d', label: '30 days' },
  { key: '90d', label: '90 days' },
];

const fmt = (n) => (n ?? 0).toLocaleString('en-IN');
const shortDate = (s) => new Date(s).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });

export default function HomePage({ user, onPageChange }) {
  const [range, setRange] = useState('7d');
  const [detailTile, setDetailTile] = useState(null);
  const [isTimerRunning, setIsTimerRunning] = useState(true);
  const [timerSeconds, setTimerSeconds] = useState(5048);
  const { data, loading, error } = usePolling(() => api.dashboard(range), 60000, [range]);

  const go = (p) => onPageChange && onPageChange(p);

  useEffect(() => {
    let interval = null;
    if (isTimerRunning) {
      interval = setInterval(() => setTimerSeconds(s => s + 1), 1000);
    }
    return () => clearInterval(interval);
  }, [isTimerRunning]);

  const formatTimer = (sec) => {
    const hrs = String(Math.floor(sec / 3600)).padStart(2, '0');
    const mins = String(Math.floor((sec % 3600) / 60)).padStart(2, '0');
    const secs = String(sec % 60).padStart(2, '0');
    return `${hrs}:${mins}:${secs}`;
  };

  const kpis = data?.kpis || [];
  const contactsKpi = kpis.find(k => k.key === 'contacts') || { value: 24, label: 'Total Contacts' };
  const deliveredKpi = kpis.find(k => k.key === 'sent') || { value: 10, label: 'Delivered Messages' };
  const automationsKpi = kpis.find(k => k.key === 'automations') || { value: 12, label: 'Active Automations' };
  const openChatsKpi = kpis.find(k => k.key === 'open') || { value: 2, label: 'Pending Responses' };

  return (
    <div style={{
      padding: '28px 36px 48px',
      fontFamily: FONT,
      background: '#F5F5F5',
      minHeight: '100%',
      boxSizing: 'border-box',
    }}>
      {/* ── 1. Top Header ── */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 28,
        flexWrap: 'wrap',
        gap: 20,
      }}>
        <div>
          <h1 style={{
            fontSize: 28,
            fontWeight: 800,
            color: '#1A1A1A',
            margin: 0,
            letterSpacing: '-0.02em',
            fontFamily: FONT,
          }}>
            Dashboard
          </h1>
          <p style={{
            fontSize: 13,
            color: '#888',
            margin: '4px 0 0',
            fontFamily: FONT,
            fontWeight: 500,
          }}>
            Overview of your conversations, automations, and team activity.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          {/* Time Range Pills */}
          <div style={{
            display: 'flex',
            background: '#FFFFFF',
            border: '1px solid #E0E0E0',
            borderRadius: 8,
            padding: '3px',
            gap: 2,
          }}>
            {RANGES.map(r => {
              const active = r.key === range;
              return (
                <button
                  key={r.key}
                  onClick={() => setRange(r.key)}
                  style={{
                    border: 'none',
                    cursor: 'pointer',
                    fontFamily: FONT,
                    fontSize: 12,
                    fontWeight: 600,
                    padding: '5px 12px',
                    borderRadius: 6,
                    background: active ? '#FF5A00' : 'transparent',
                    color: active ? '#FFFFFF' : '#666',
                    transition: 'all .12s',
                  }}
                >
                  {r.label}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => go('bulk-message')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              cursor: 'pointer',
              fontFamily: FONT,
              fontSize: 13,
              fontWeight: 700,
              padding: '8px 16px',
              borderRadius: 8,
              border: 'none',
              background: '#1A1A1A',
              color: '#FFFFFF',
            }}
          >
            <Plus size={15} strokeWidth={2.5} />
            <span>New Campaign</span>
          </button>

          <button
            onClick={() => go('contacts')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              cursor: 'pointer',
              fontFamily: FONT,
              fontSize: 13,
              fontWeight: 700,
              padding: '8px 16px',
              borderRadius: 8,
              border: '1.5px solid #D0D0D0',
              background: '#FFFFFF',
              color: '#1A1A1A',
            }}
          >
            <span>Import Data</span>
          </button>
        </div>
      </div>

      {/* ── 2. KPI Cards ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: 16,
        marginBottom: 24,
      }}>
        {/* Card 1: Featured Dark Card */}
        <div
          onClick={() => contactsKpi && setDetailTile(contactsKpi)}
          style={{
            background: '#1A1A1A',
            borderRadius: 12,
            padding: 22,
            color: '#FFFFFF',
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            minHeight: 140,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'rgba(255,255,255,0.7)' }}>
              Total Contacts
            </span>
            <div style={{
              width: 28,
              height: 28,
              borderRadius: 6,
              background: 'rgba(255,255,255,0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFFFFF',
            }}>
              <Users size={14} />
            </div>
          </div>
          <div style={{ fontSize: 38, fontWeight: 800, fontFamily: FONT, letterSpacing: '-0.03em', margin: '10px 0 4px' }}>
            {fmt(contactsKpi.value)}
          </div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', fontWeight: 600 }}>
            ↑ from last period
          </div>
        </div>

        {/* Card 2: Delivered Messages */}
        <KpiCard
          label="Delivered Messages"
          value={fmt(deliveredKpi.value)}
          icon={<Send size={14} />}
          sub="Sent this period"
          onClick={() => deliveredKpi && setDetailTile(deliveredKpi)}
        />

        {/* Card 3: Active Automations */}
        <KpiCard
          label="Active Automations"
          value={fmt(automationsKpi.value)}
          icon={<Zap size={14} />}
          sub="Live flow executions"
          accentColor="#FF5A00"
          onClick={() => go('chatbot-builder')}
        />

        {/* Card 4: Pending Responses */}
        <KpiCard
          label="Pending Responses"
          value={fmt(openChatsKpi.value)}
          icon={<MessageCircle size={14} />}
          sub="Awaiting agent reply"
          onClick={() => go('chats')}
        />
      </div>

      {/* ── 3. Middle Grid ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(12, 1fr)',
        gap: 16,
        marginBottom: 24,
      }}>
        {/* Message Analytics Bar Chart */}
        <div style={{
          gridColumn: 'span 5',
          background: '#FFFFFF',
          borderRadius: 12,
          padding: 22,
          border: '1px solid #E8E8E8',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#1A1A1A' }}>
              Conversation Analytics
            </h3>
            <span style={{ fontSize: 11, color: '#999', fontWeight: 600 }}>Weekly</span>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'space-between',
            height: 140,
            padding: '0 8px',
            gap: 10,
          }}>
            {[
              { day: 'S', pct: 40 },
              { day: 'M', pct: 70 },
              { day: 'T', pct: 60, badge: '74%' },
              { day: 'W', pct: 95 },
              { day: 'T', pct: 45 },
              { day: 'F', pct: 55 },
              { day: 'S', pct: 35 },
            ].map((bar, i) => (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, height: '100%', justifyContent: 'flex-end' }}>
                {bar.badge && (
                  <span style={{
                    fontSize: 9,
                    fontWeight: 700,
                    color: '#FF5A00',
                    background: '#FFF0E6',
                    padding: '2px 5px',
                    borderRadius: 4,
                    marginBottom: 4,
                  }}>
                    {bar.badge}
                  </span>
                )}
                <div style={{
                  width: '100%',
                  maxWidth: 24,
                  height: `${bar.pct}%`,
                  borderRadius: 4,
                  background: bar.pct > 80 ? '#1A1A1A' : bar.pct > 55 ? '#FF5A00' : '#E0E0E0',
                }} />
                <span style={{ fontSize: 11, fontWeight: 600, color: '#999', marginTop: 8 }}>
                  {bar.day}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* AI Agent Card */}
        <div style={{
          gridColumn: 'span 3',
          background: '#FFFFFF',
          borderRadius: 12,
          padding: 22,
          border: '1px solid #E8E8E8',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#AAA', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Reminders
            </div>
            <h3 style={{ margin: '12px 0 6px', fontSize: 16, fontWeight: 800, color: '#1A1A1A', lineHeight: 1.3 }}>
              Smart AI Agent Sweep
            </h3>
            <p style={{ margin: 0, fontSize: 12, color: '#888', fontWeight: 500 }}>
              Schedule: Auto-run every 10 mins
            </p>
          </div>

          <button
            onClick={() => go('ai-agent-builder')}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              width: '100%',
              padding: '10px 14px',
              borderRadius: 8,
              border: 'none',
              background: '#1A1A1A',
              color: '#FFFFFF',
              fontSize: 13,
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            <span>🤖</span>
            <span>Launch Agent</span>
          </button>
        </div>

        {/* Active Pipelines */}
        <div style={{
          gridColumn: 'span 4',
          background: '#FFFFFF',
          borderRadius: 12,
          padding: 22,
          border: '1px solid #E8E8E8',
          display: 'flex',
          flexDirection: 'column',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#1A1A1A' }}>
              Active Pipelines
            </h3>
            <button
              onClick={() => go('pipelines')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                border: '1px solid #E0E0E0',
                background: '#FFFFFF',
                borderRadius: 6,
                padding: '3px 8px',
                fontSize: 11,
                fontWeight: 600,
                color: '#1A1A1A',
                cursor: 'pointer',
              }}
            >
              <Plus size={11} />
              <span>New</span>
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[
              { icon: '🚀', name: 'Order Checkout Automation', date: 'Due: Today, 6:00 PM' },
              { icon: '📦', name: 'Shiprocket Logistics Sync', date: 'Due: Realtime webhook' },
              { icon: '💬', name: 'Meta WhatsApp Onboarding', date: 'Active on 1 WABA' },
              { icon: '⚡', name: 'Thaniq Lead Funnel', date: '4 stages active' },
            ].map((p, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: 6,
                  background: '#F5F5F5',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 15,
                  flexShrink: 0,
                  border: '1px solid #E8E8E8',
                }}>
                  {p.icon}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#1A1A1A', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {p.name}
                  </div>
                  <div style={{ fontSize: 11, color: '#AAA' }}>{p.date}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── 4. Bottom Grid ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(12, 1fr)',
        gap: 16,
      }}>
        {/* Team Collaboration */}
        <div style={{
          gridColumn: 'span 5',
          background: '#FFFFFF',
          borderRadius: 12,
          padding: 22,
          border: '1px solid #E8E8E8',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#1A1A1A' }}>
              Team Collaboration
            </h3>
            <button
              onClick={() => go('admin-settings')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                border: '1px solid #E0E0E0',
                background: '#FFFFFF',
                borderRadius: 6,
                padding: '3px 8px',
                fontSize: 11,
                fontWeight: 600,
                color: '#1A1A1A',
                cursor: 'pointer',
              }}
            >
              <Plus size={11} />
              <span>Add Member</span>
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[
              { name: 'Thaniq Admin', role: 'Main Admin', status: 'Active', color: '#FF5A00', bg: '#FFF0E6' },
              { name: 'Naveen (Logistics)', role: 'Warehouse Tirunelveli', status: 'Connected', color: '#3B82F6', bg: '#EFF6FF' },
              { name: 'WhatsApp Bot Agent', role: 'Auto-Responder', status: 'Running', color: '#FF5A00', bg: '#FFF0E6' },
            ].map((m, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    background: '#1A1A1A',
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 700,
                    fontSize: 12,
                  }}>
                    {m.name.charAt(0)}
                  </div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#1A1A1A' }}>{m.name}</div>
                    <div style={{ fontSize: 11, color: '#AAA' }}>{m.role}</div>
                  </div>
                </div>
                <span style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: m.color,
                  background: m.bg,
                  padding: '3px 8px',
                  borderRadius: 4,
                }}>
                  {m.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Resolution Progress */}
        <div style={{
          gridColumn: 'span 4',
          background: '#FFFFFF',
          borderRadius: 12,
          padding: 22,
          border: '1px solid #E8E8E8',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ width: '100%', textAlign: 'left' }}>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#1A1A1A' }}>
              Resolution Progress
            </h3>
          </div>

          {/* Semicircular Gauge */}
          <div style={{ position: 'relative', width: 160, height: 90, marginTop: 10 }}>
            <svg viewBox="0 0 100 55" width="160" height="90">
              <path
                d="M 10 50 A 40 40 0 0 1 90 50"
                fill="none"
                stroke="#E8E8E8"
                strokeWidth="10"
                strokeLinecap="round"
              />
              <path
                d="M 10 50 A 40 40 0 0 1 70 18"
                fill="none"
                stroke="#FF5A00"
                strokeWidth="10"
                strokeLinecap="round"
              />
            </svg>
            <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 800, color: '#1A1A1A', lineHeight: 1 }}>74%</div>
              <div style={{ fontSize: 11, color: '#AAA', fontWeight: 600, marginTop: 2 }}>Resolved</div>
            </div>
          </div>

          {/* Legend */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 11, fontWeight: 600, color: '#888', marginTop: 8 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: '#FF5A00' }} />
              Completed
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: '#FFB380' }} />
              In Progress
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: '#E8E8E8' }} />
              Pending
            </span>
          </div>
        </div>

        {/* Response Time Widget */}
        <div style={{
          gridColumn: 'span 3',
          borderRadius: 12,
          padding: 22,
          background: '#1A1A1A',
          color: '#FFFFFF',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}>
          <div>
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', fontWeight: 600 }}>
              Average Response Time
            </span>
            <div style={{ fontSize: 28, fontWeight: 800, fontFamily: MONO, letterSpacing: '-0.02em', margin: '12px 0 8px' }}>
              {formatTimer(timerSeconds)}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              onClick={() => setIsTimerRunning(!isTimerRunning)}
              style={{
                width: 34,
                height: 34,
                borderRadius: 6,
                background: '#FF5A00',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#FFFFFF',
                cursor: 'pointer',
              }}
            >
              {isTimerRunning ? <Pause size={14} /> : <Play size={14} />}
            </button>
            <button
              onClick={() => setTimerSeconds(0)}
              style={{
                width: 34,
                height: 34,
                borderRadius: 6,
                background: '#333',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#FFFFFF',
                cursor: 'pointer',
              }}
            >
              <Square size={12} fill="#FFFFFF" />
            </button>
          </div>
        </div>
      </div>

      {/* ── Drilldown Modal ── */}
      {detailTile && (
        <KpiDetailModal tile={detailTile} range={range} onClose={() => setDetailTile(null)} />
      )}
    </div>
  );
}

// ── Flat KPI Card ──
function KpiCard({ label, value, icon, sub, accentColor, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: '#FFFFFF',
        borderRadius: 12,
        padding: 22,
        border: '1px solid #E8E8E8',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        minHeight: 140,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#888' }}>
          {label}
        </span>
        <div style={{
          width: 28,
          height: 28,
          borderRadius: 6,
          background: '#F5F5F5',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#666',
          border: '1px solid #E8E8E8',
        }}>
          {icon}
        </div>
      </div>
      <div style={{ fontSize: 38, fontWeight: 800, fontFamily: FONT, letterSpacing: '-0.03em', margin: '10px 0 4px', color: '#1A1A1A' }}>
        {value}
      </div>
      <div style={{ fontSize: 11, color: accentColor || '#AAA', fontWeight: 600 }}>
        {sub}
      </div>
    </div>
  );
}

// ── Detail Drilldown Modal ──
function KpiDetailModal({ tile, range, onClose }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  useEffect(() => {
    let alive = true;
    setState({ loading: true, error: null, data: null });
    api.dashboardDetails(tile.key, range)
      .then(d => { if (alive) setState({ loading: false, error: null, data: d }); })
      .catch(() => { if (alive) setState({ loading: false, error: 'Failed to load details', data: null }); });
    return () => { alive = false; };
  }, [tile.key, range]);

  const { loading, error, data } = state;
  const items = data?.items || [];
  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.4)', zIndex: 200,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#FFFFFF', borderRadius: 12, width: 'min(520px, 100%)',
        maxHeight: '80vh', display: 'flex', flexDirection: 'column', fontFamily: FONT,
        border: '1px solid #E0E0E0',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid #E8E8E8' }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, color: '#1A1A1A' }}>{data?.title || tile.label}</div>
            <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
              {loading ? 'Loading…' : `${fmt(data?.count ?? 0)} ${data?.count === 1 ? 'item' : 'items'}`}
            </div>
          </div>
          <button onClick={onClose} title="Close" style={{ border: 'none', background: '#F5F5F5', borderRadius: 6, width: 30, height: 30, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: '#888' }}>
            <X size={15} strokeWidth={2.4} />
          </button>
        </div>
        <div style={{ overflowY: 'auto', padding: '6px 0' }}>
          {loading && (
            <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} style={{ height: 36, background: '#F5F5F5', borderRadius: 6 }} />
              ))}
            </div>
          )}
          {!loading && error && (
            <div style={{ margin: 16, background: '#FEE2E2', color: '#DC2626', borderRadius: 8, padding: '10px 14px', fontSize: 13 }}>{error}</div>
          )}
          {!loading && !error && items.length === 0 && (
            <div style={{ padding: '28px 16px', textAlign: 'center', fontSize: 13, color: '#888' }}>No items to show.</div>
          )}
          {!loading && !error && items.map((it, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 20px', borderTop: i === 0 ? 'none' : '1px solid #F5F5F5' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#1A1A1A', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{it.primary || '—'}</div>
                {it.secondary && <div style={{ fontSize: 12, color: '#888', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{it.secondary}</div>}
              </div>
              {it.meta && (
                <div style={{
                  fontSize: 12, fontFamily: MONO, flexShrink: 0,
                  color: it.meta === 'No reply' ? '#EF4444' : it.meta === 'Replied' || it.meta === 'active' ? '#FF5A00' : '#888',
                  fontWeight: 700,
                }}>{it.meta}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
