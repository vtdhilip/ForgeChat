import { useState, useEffect } from 'react';
import { AlertTriangle, ArrowUpRight, ArrowDownRight, Info, RefreshCw, X } from 'lucide-react';
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

const CARD = {
  background: C.cardBg,
  border: `1px solid ${C.border}`,
  borderRadius: 12,
  boxShadow: C.shadowSm,
  padding: 18,
};

const LINK_BTN = {
  border: 'none',
  background: 'none',
  padding: 0,
  color: C.primary,
  cursor: 'pointer',
  fontSize: 12.5,
  fontWeight: 600,
  fontFamily: FONT,
};

// ── Small tooltip for KPI info icons ───────────────────────────────────
function InfoIcon({ text }) {
  const [show, setShow] = useState(false);
  return (
    <span
      style={{ position: 'relative', display: 'inline-flex', marginLeft: 5 }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      <Info size={13} strokeWidth={2.5} aria-label={text} style={{ color: C.textMuted, cursor: 'help' }} />
      {show && (
        <span role="tooltip" style={{
          position: 'absolute', bottom: '150%', left: '50%', transform: 'translateX(-50%)',
          background: C.headerBg, color: C.headerText, fontSize: 11.5, lineHeight: 1.45,
          padding: '7px 9px', borderRadius: 7, width: 210, zIndex: 60,
          boxShadow: C.shadowMd, fontFamily: FONT, fontWeight: 500,
          pointerEvents: 'none', textAlign: 'left',
        }}>{text}</span>
      )}
    </span>
  );
}

function SectionTitle({ children, right }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
      <h2 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: C.text, fontFamily: FONT }}>{children}</h2>
      {right}
    </div>
  );
}

// ── KPI card: label, value (click to drill down), change ───────────────
function KpiCard({ tile, onSelect }) {
  const value = tile.unit === '%' ? `${tile.value}%` : fmt(tile.value);
  const hasDelta = tile.delta != null;
  const up = hasDelta && tile.delta >= 0;
  return (
    <div style={{ ...CARD, padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', fontSize: 13, fontWeight: 600, color: C.textSecondary, fontFamily: FONT }}>
        {tile.label}
        {tile.tooltip && <InfoIcon text={tile.tooltip} />}
      </div>
      <button
        onClick={() => onSelect(tile)}
        title={`View ${tile.label.toLowerCase()} details`}
        style={{
          border: 'none', background: 'none', padding: 0, cursor: 'pointer',
          fontSize: 26, fontWeight: 600, color: C.text, fontFamily: MONO,
          margin: '12px 0 6px', letterSpacing: '-.01em', display: 'block',
          textAlign: 'left', borderRadius: 4,
        }}
        onMouseEnter={e => { e.currentTarget.style.color = C.primary; }}
        onMouseLeave={e => { e.currentTarget.style.color = C.text; }}
      >
        {value}
      </button>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minHeight: 18 }}>
        {hasDelta && (
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 2,
            fontSize: 12, fontWeight: 600, fontFamily: MONO,
            color: up ? C.green : C.primary,
          }}>
            {up ? <ArrowUpRight size={13} strokeWidth={2.5} /> : <ArrowDownRight size={13} strokeWidth={2.5} />}
            {Math.abs(tile.delta)}%
          </span>
        )}
        {tile.sub && <span style={{ fontSize: 12, color: C.textMuted, fontFamily: FONT }}>{tile.sub}</span>}
      </div>
    </div>
  );
}

// ── KPI drill-down modal: lists the items behind a KPI number ───────────
function KpiDetailModal({ tile, range, onClose }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    let alive = true;
    setState({ loading: true, error: null, data: null });
    api.dashboardDetails(tile.key, range)
      .then(d => { if (alive) setState({ loading: false, error: null, data: d }); })
      .catch(() => { if (alive) setState({ loading: false, error: 'Couldn’t load these details.', data: null }); });
    return () => { alive = false; };
  }, [tile.key, range]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const { loading, error, data } = state;
  const items = data?.items || [];
  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.35)', zIndex: 200,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <div role="dialog" aria-modal="true" aria-label={data?.title || tile.label} onClick={e => e.stopPropagation()} style={{
        background: C.cardBg, borderRadius: 14, boxShadow: C.shadowLg, width: 'min(540px, 100%)',
        maxHeight: '82vh', display: 'flex', flexDirection: 'column', fontFamily: FONT,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 18px', borderBottom: `1px solid ${C.border}` }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: C.text }}>{data?.title || tile.label}</div>
            <div style={{ fontSize: 12, color: C.textMuted, marginTop: 2 }}>
              {loading ? 'Loading…' : `${fmt(data?.count ?? 0)} ${data?.count === 1 ? 'item' : 'items'}`}
            </div>
          </div>
          <button onClick={onClose} aria-label="Close" style={{ border: 'none', background: C.pageBg, borderRadius: 8, width: 30, height: 30, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: C.textSecondary }}>
            <X size={16} strokeWidth={2.4} />
          </button>
        </div>
        <div style={{ overflowY: 'auto', padding: '6px 0' }}>
          {loading && (
            <div style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} style={{ height: 38, background: C.pageBg, borderRadius: 8, opacity: 0.7 }} />
              ))}
            </div>
          )}
          {!loading && error && (
            <div role="alert" style={{ margin: 18, background: C.primaryLight, color: '#A32D2D', borderRadius: 10, padding: '12px 14px', fontSize: 13 }}>{error}</div>
          )}
          {!loading && !error && items.length === 0 && (
            <div style={{ padding: '32px 18px', textAlign: 'center', fontSize: 13, color: C.textMuted }}>Nothing to show for this range.</div>
          )}
          {!loading && !error && items.map((it, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 18px', borderTop: i === 0 ? 'none' : `1px solid ${C.border}` }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: C.text, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{it.primary || '—'}</div>
                {it.secondary && <div style={{ fontSize: 12, color: C.textMuted, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{it.secondary}</div>}
              </div>
              {it.meta && (
                <div style={{
                  fontSize: 12, fontFamily: MONO, flexShrink: 0,
                  color: it.meta === 'No reply' ? C.primary : it.meta === 'Replied' || it.meta === 'active' ? C.green : C.textSecondary,
                  fontWeight: it.meta === 'No reply' || it.meta === 'active' ? 700 : 500,
                }}>{it.meta}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Lead stages (horizontal bars) ──────────────────────────────────────
function FunnelBars({ funnel }) {
  const stages = funnel.stages || [];
  const max = Math.max(1, ...stages.map(s => s.count));
  if (stages.length === 0) {
    return <div style={{ fontSize: 13, color: C.textMuted, fontFamily: FONT, padding: '12px 0' }}>
      No tagged contacts yet. Tag contacts to see your pipeline here.
    </div>;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {stages.map((s, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 120, fontSize: 13, color: C.textSecondary, fontFamily: FONT, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={s.name}>{s.name}</div>
          <div style={{ flex: 1, height: 8, background: C.pageBg, borderRadius: 4, overflow: 'hidden' }}>
            <div title={`${s.name}: ${fmt(s.count)} contacts`} style={{
              width: `${(s.count / max) * 100}%`, height: '100%', background: s.color || C.primary,
              borderRadius: 4, minWidth: s.count > 0 ? 4 : 0, transition: 'width .3s ease',
            }} />
          </div>
          <div style={{ width: 44, textAlign: 'right', fontSize: 13, fontWeight: 600, fontFamily: MONO, color: C.text }}>{fmt(s.count)}</div>
        </div>
      ))}
    </div>
  );
}

// ── Tag distribution donut ─────────────────────────────────────────────
function polar(cx, cy, r, a) { return [cx + r * Math.sin(a), cy - r * Math.cos(a)]; }
function arcPath(cx, cy, R, r, a0, a1) {
  const large = (a1 - a0) > Math.PI ? 1 : 0;
  const [x0, y0] = polar(cx, cy, R, a0), [x1, y1] = polar(cx, cy, R, a1);
  const [x2, y2] = polar(cx, cy, r, a1), [x3, y3] = polar(cx, cy, r, a0);
  return `M${x0},${y0} A${R},${R} 0 ${large} 1 ${x1},${y1} L${x2},${y2} A${r},${r} 0 ${large} 0 ${x3},${y3} Z`;
}
function TagDonut({ data }) {
  const [hover, setHover] = useState(-1);
  const total = data.reduce((s, d) => s + d.count, 0);
  if (total === 0) {
    return <div style={{ fontSize: 13, color: C.textMuted, fontFamily: FONT, padding: '12px 0' }}>No tags applied yet.</div>;
  }
  const cx = 80, cy = 80, R = 74, r = 48;
  let acc = 0;
  const segs = data.map((d, i) => {
    const a0 = (acc / total) * 2 * Math.PI; acc += d.count;
    const a1 = (acc / total) * 2 * Math.PI;
    return { ...d, a0, a1, i };
  });
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
      <svg viewBox="0 0 160 160" width="140" height="140" style={{ flexShrink: 0 }}>
        {data.length === 1 ? (
          <circle cx={cx} cy={cy} r={(R + r) / 2} fill="none" stroke={data[0].color || C.primary} strokeWidth={R - r}>
            <title>{`${data[0].name}: ${fmt(data[0].count)} (100%)`}</title>
          </circle>
        ) : segs.map((s) => (
          <path key={s.i} d={arcPath(cx, cy, R, r, s.a0, s.a1)} fill={s.color || C.primary}
            opacity={hover === -1 || hover === s.i ? 1 : 0.38}
            onMouseEnter={() => setHover(s.i)} onMouseLeave={() => setHover(-1)}
            style={{ transition: 'opacity .15s', cursor: 'default' }}>
            <title>{`${s.name}: ${fmt(s.count)} (${Math.round((s.count / total) * 100)}%)`}</title>
          </path>
        ))}
        <text x={cx} y={cy - 4} textAnchor="middle" fontSize="22" fontWeight="600" fill={C.text} fontFamily="DM Mono">{fmt(total)}</text>
        <text x={cx} y={cy + 14} textAnchor="middle" fontSize="10" fill={C.textMuted} fontFamily="DM Sans">tagged</text>
      </svg>
      <div style={{ flex: 1, minWidth: 140, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {data.map((d, i) => (
          <div key={i} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(-1)}
            style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontFamily: FONT, opacity: hover === -1 || hover === i ? 1 : 0.5, transition: 'opacity .15s' }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: d.color || C.primary, flexShrink: 0 }} />
            <span style={{ color: C.textSecondary, flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={d.name}>{d.name}</span>
            <span style={{ color: C.text, fontFamily: MONO, fontWeight: 600 }}>{fmt(d.count)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Automation performance ─────────────────────────────────────────────
function AutomationStat({ label, value, color }) {
  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ fontSize: 18, fontWeight: 600, fontFamily: MONO, color: color || C.text }}>{value}</div>
      <div style={{ fontSize: 12, color: C.textMuted, fontFamily: FONT, marginTop: 2 }}>{label}</div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────
export default function HomePage({ user, onPageChange }) {
  const [range, setRange] = useState('7d');
  const [detailTile, setDetailTile] = useState(null);
  const { data, loading, error } = usePolling(() => api.dashboard(range), 60000, [range]);

  const go = (p) => onPageChange && onPageChange(p);
  const isAdmin = true; // single-owner system: the owner sees everything
  const orgModules = user?.activeOrg?.settings?.modules || {};
  const greeting = user?.displayName || user?.username || 'there';
  const rangeLabel = RANGES.find(r => r.key === range)?.label;

  const allActions = [
    { label: 'Open chats', page: 'chats', primary: true, moduleKey: 'chats' },
    { label: 'Contacts', page: 'contacts', moduleKey: 'contacts' },
    { label: 'New broadcast', page: 'bulk-message', moduleKey: 'broadcasts' },
    { label: 'New automation', page: 'chatbot-builder', moduleKey: 'chatbots' },
    { label: 'New template', page: 'template-builder', moduleKey: 'templates' },
  ];
  const quickActions = allActions.filter(a => !a.moduleKey || orgModules[a.moduleKey] !== false);

  return (
    <div style={{ padding: '28px 32px 40px', fontFamily: FONT, width: '100%', maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: C.text, margin: 0, letterSpacing: '-.02em', fontFamily: FONT }}>
            Welcome back, {greeting}
          </h1>
          <p style={{ fontSize: 13, color: C.textMuted, margin: '4px 0 0', fontFamily: FONT }}>
            {isAdmin ? 'Org-wide overview' : 'Your activity overview'}, last {rangeLabel}
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <div role="group" aria-label="Date range" style={{ display: 'flex', border: `1px solid ${C.border}`, borderRadius: 8, padding: 2, background: C.cardBg }}>
            {RANGES.map(r => {
              const active = r.key === range;
              return (
                <button key={r.key} onClick={() => setRange(r.key)} aria-pressed={active} style={{
                  border: 'none', cursor: 'pointer', fontFamily: FONT, fontSize: 12.5, fontWeight: 600,
                  padding: '5px 10px', borderRadius: 6,
                  background: active ? C.text : 'transparent', color: active ? C.cardBg : C.textSecondary,
                  transition: 'background .15s, color .15s',
                }}>{r.label}</button>
              );
            })}
          </div>
          {quickActions.map(a => (
            <button key={a.label} onClick={() => go(a.page)} style={{
              cursor: 'pointer', fontFamily: FONT, fontSize: 13, fontWeight: 600,
              padding: '7px 12px', borderRadius: 8,
              border: a.primary ? 'none' : `1px solid ${C.border}`,
              background: a.primary ? C.primary : C.cardBg,
              color: a.primary ? '#fff' : C.text,
            }}>
              {a.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div role="alert" style={{ background: C.primaryLight, color: '#A32D2D', borderRadius: 10, padding: '12px 14px', fontSize: 13, fontFamily: FONT, marginBottom: 16 }}>
          Couldn’t load the dashboard. Try again in a moment.
        </div>
      )}

      {/* Loading skeleton */}
      {loading && !data && (
        <div aria-busy="true">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 16 }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} style={{ height: 108, background: C.cardBg, border: `1px solid ${C.border}`, borderRadius: 12, opacity: 0.6 }} />
            ))}
          </div>
          <div style={{ height: 260, background: C.cardBg, border: `1px solid ${C.border}`, borderRadius: 12, opacity: 0.6 }} />
        </div>
      )}

      {data && (
        <>
          {data.alerts && data.alerts.length > 0 && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
              {data.alerts.map((al, i) => {
                const warn = al.level === 'warn';
                return (
                  <button key={i} onClick={() => go(al.page)} style={{
                    display: 'inline-flex', alignItems: 'center', gap: 7, cursor: 'pointer', fontFamily: FONT,
                    fontSize: 13, fontWeight: 600, padding: '6px 11px', borderRadius: 8,
                    border: `1px solid ${warn ? '#F3C9C9' : C.border}`,
                    background: warn ? C.primaryLight : C.cardBg,
                    color: warn ? '#A32D2D' : C.textSecondary,
                  }}>
                    <AlertTriangle size={13} strokeWidth={2.4} style={{ color: warn ? C.primary : C.textMuted }} />
                    {al.label}
                    <span style={{ fontFamily: MONO, fontWeight: 700 }}>{fmt(al.count)}</span>
                  </button>
                );
              })}
            </div>
          )}

          {/* KPIs */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 12, marginBottom: 16 }}>
            {data.kpis.map(t => <KpiCard key={t.key} tile={t} onSelect={setDetailTile} />)}
          </div>

          {/* Lead stages + tags */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 12, marginBottom: 12 }}>
            <section style={CARD}>
              <SectionTitle>
                Lead stages{data.funnel?.categoryName ? `, ${data.funnel.categoryName}` : ''}
              </SectionTitle>
              <FunnelBars funnel={data.funnel || { stages: [] }} />
            </section>
            <section style={CARD}>
              <SectionTitle>Contacts by tag</SectionTitle>
              <TagDonut data={data.tagDistribution || []} />
            </section>
          </div>

          {/* Automations + broadcasts */}
          {((data.automations && orgModules.chatbots !== false) || (data.broadcasts && orgModules.broadcasts !== false)) && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 12, marginBottom: 16 }}>
              {data.automations && orgModules.chatbots !== false && (
                <section style={CARD}>
                  <SectionTitle right={
                    <button onClick={() => go('chatbot-builder')} style={LINK_BTN}>View all</button>
                  }>Automations</SectionTitle>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 16 }}>
                    <span style={{ fontSize: 26, fontWeight: 600, fontFamily: MONO, color: C.text }}>{data.automations.active}</span>
                    <span style={{ fontSize: 13, color: C.textMuted, fontFamily: FONT }}>of {data.automations.total} active</span>
                  </div>
                  <div style={{ display: 'flex', gap: 12, borderTop: `1px solid ${C.border}`, paddingTop: 14 }}>
                    <AutomationStat label={`Runs, ${rangeLabel}`} value={fmt(data.automations.runs.total)} />
                    <AutomationStat label="Success" value={data.automations.successRate == null ? '—' : `${data.automations.successRate}%`} color={C.green} />
                    <AutomationStat label="Waiting" value={fmt(data.automations.runs.paused)} color={C.amber} />
                    <AutomationStat label="Errors" value={fmt(data.automations.runs.error)} color={data.automations.runs.error > 0 ? C.primary : C.text} />
                  </div>
                </section>
              )}
              {data.broadcasts && orgModules.broadcasts !== false && (
                <section style={CARD}>
                  <SectionTitle right={
                    <button onClick={() => go('bulk-message')} style={LINK_BTN}>View all</button>
                  }>Recent broadcasts</SectionTitle>
                  {data.broadcasts.recent.length === 0 ? (
                    <div style={{ fontSize: 13, color: C.textMuted, fontFamily: FONT, padding: '12px 0' }}>No broadcasts yet.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      {data.broadcasts.recent.map(b => (
                        <div key={b.id} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, fontFamily: FONT }}>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontWeight: 600, color: C.text, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{b.name || `Broadcast #${b.id}`}</div>
                            <div style={{ fontSize: 12, color: C.textMuted }}>{shortDate(b.createdAt)} · {b.messageType}</div>
                          </div>
                          <div style={{ textAlign: 'right', fontFamily: MONO, fontSize: 12.5 }}>
                            <span style={{ color: C.green, fontWeight: 600 }}>{fmt(b.sent)}</span>
                            <span style={{ color: C.textMuted }}> / {fmt(b.recipients)}</span>
                            {b.failed > 0 && <span style={{ color: C.primary, fontWeight: 600 }}> · {fmt(b.failed)} failed</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              )}
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: C.textMuted, fontFamily: FONT }}>
            <RefreshCw size={11} strokeWidth={2.2} aria-hidden="true" />
            Refreshes every minute · updated {new Date(data.generatedAt).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })}
          </div>
        </>
      )}

      {detailTile && (
        <KpiDetailModal tile={detailTile} range={range} onClose={() => setDetailTile(null)} />
      )}
    </div>
  );
}
