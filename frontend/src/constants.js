// Color tokens map to CSS variables (defined per-theme in index.css) so the
// whole app re-themes when <html data-theme> flips. Fallbacks = light values,
// so colors still render even if the stylesheet hasn't loaded.
export const C = {
  pageBg: 'var(--c-pageBg, #F8F9FB)',
  sidebarBg: 'var(--c-sidebarBg, #FFFFFF)',
  sidebarBorder: 'var(--c-sidebarBorder, #EAECEF)',
  headerBg: 'var(--c-headerBg, #FFFFFF)',
  headerText: 'var(--c-headerText, #111827)',
  headerMuted: 'var(--c-headerMuted, #6B7280)',
  headerBorder: 'var(--c-headerBorder, #EAECEF)',
  headerSurface: 'var(--c-headerSurface, #F3F4F6)',
  cardBg: 'var(--c-cardBg, #FFFFFF)',
  border: 'var(--c-border, #EAECEF)',
  borderDark: 'var(--c-borderDark, #D1D5DB)',
  text: 'var(--c-text, #111827)',
  textSecondary: 'var(--c-textSecondary, #6B7280)',
  textMuted: 'var(--c-textMuted, #9CA3AF)',
  primary: 'var(--c-primary, #FF5A00)',
  primaryHover: 'var(--c-primaryHover, #E64E00)',
  primaryLight: 'var(--c-primaryLight, #FFF2EB)',
  primaryText: 'var(--c-primaryText, #FFFFFF)',
  purple: 'var(--c-purple, #7C3AED)',
  green: 'var(--c-green, #FF5A00)',
  amber: 'var(--c-amber, #F59E0B)',
  shadowSm: 'var(--c-shadowSm, 0 1px 3px rgba(0,0,0,0.03))',
  shadowMd: 'var(--c-shadowMd, 0 4px 20px rgba(0,0,0,0.04))',
  shadowLg: 'var(--c-shadowLg, 0 14px 36px rgba(0,0,0,0.08))',
  waBg: 'var(--c-waBg, #e5ddd5)',
  surface: 'var(--c-surface, #FFFFFF)',
  surfaceAlt: 'var(--c-surfaceAlt, #F8F9FB)',
  hover: 'var(--c-hover, #F3F4F6)',
  waBgPattern: 'url("data:image/svg+xml,%3Csvg width=\'16\' height=\'16\' viewBox=\'0 0 16 16\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cpath d=\'M0 0h8v8H0z\' fill=\'%23d1d7db\' fill-opacity=\'0.15\'/%3E%3C/svg%3E")',
};

export const CHAT = {
  incomingBg: 'var(--c-incomingBg, #ffffff)',
  incomingText: 'var(--c-incomingText, #111b21)',
  outgoingBg: 'var(--c-outgoingBg, #d9fdd3)',
  outgoingText: 'var(--c-outgoingText, #111b21)',
  chatBg: 'var(--c-chatBg, #e5ddd5)',
  bubbleRadius: '7.5px',
  bubblePadding: '6px 7px 8px 9px',
  statusDelivered: 'var(--c-statusDelivered, #53bdeb)',
  statusRead: 'var(--c-statusRead, #53bdeb)',
  statusSent: 'var(--c-statusSent, #8696a0)',
};

export const FONT = "'DM Sans', system-ui, sans-serif";
export const MONO = "'DM Mono', monospace";

export function relativeTime(ts) {
  const d = new Date(ts);
  const now = new Date();
  const diff = Math.floor((now - d) / 1000);
  if (diff < 60) return 'now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

export function formatTime(ts) {
  const d = new Date(ts);
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
}

// Mask a phone number for display — keep the first 2 and last 3 digits, star the
// rest (e.g. "919487722330" -> "91*******330", "93xxxxx678" -> "93*****678").
// Used directly for non-interactive contexts (<option>, strings); the
// MaskedNumber component wraps this with click-to-reveal for JSX.
export function maskPhone(raw) {
  const s = String(raw ?? '');
  const digits = s.replace(/\D/g, '');
  if (digits.length <= 5) return s; // too short to meaningfully mask
  return digits.slice(0, 2) + '*'.repeat(digits.length - 5) + digits.slice(-3);
}

// Tag colors are stored as pale pastels (good as light fills, unreadable with
// the white chip text). Darken a hex color so a white label reads clearly while
// the tag keeps its own hue. Falls back to a dark slate for missing/invalid.
export function darkenColor(hex, factor = 0.5) {
  const m = /^#?([0-9a-fA-F]{6})$/.exec(hex || '');
  if (!m) return '#374151';
  const n = parseInt(m[1], 16);
  const r = Math.round(((n >> 16) & 255) * factor);
  const g = Math.round(((n >> 8) & 255) * factor);
  const b = Math.round((n & 255) * factor);
  return `rgb(${r}, ${g}, ${b})`;
}

// Trigger a client-side download of a JS object as a pretty-printed .json file.
export function downloadJson(filename, obj) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename.endsWith('.json') ? filename : `${filename}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Slugify a name into a safe filename fragment.
export function slugifyName(name) {
  return String(name || 'export').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'export';
}

export function formatDate(ts) {
  const d = new Date(ts);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  if (isToday) return 'Today';
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
}
