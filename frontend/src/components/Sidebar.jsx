import {
  LayoutDashboard, Zap, LayoutTemplate, MessageSquare, Users,
  Send, Image as ImageIcon, Info, Kanban, Bot, Settings,
  ChevronLeft, ChevronRight,
} from 'lucide-react';
import { C, FONT } from '../constants.js';

const NAV_GROUPS = [
  {
    title: 'MENU',
    items: [
      { id: 'home', label: 'Dashboard', Icon: LayoutDashboard },
      { id: 'chats', label: 'Chats', Icon: MessageSquare },
      { id: 'contacts', label: 'Contacts', Icon: Users },
      { id: 'pipelines', label: 'Pipelines', Icon: Kanban },
    ]
  },
  {
    title: 'AUTOMATION & AI',
    items: [
      { id: 'chatbot-builder', label: 'Automations', Icon: Zap },
      { id: 'ai-agent-builder', label: 'AI Agents', Icon: Bot },
      { id: 'template-builder', label: 'Templates', Icon: LayoutTemplate },
    ]
  },
  {
    title: 'CAMPAIGNS',
    items: [
      { id: 'bulk-message', label: 'Broadcasts', Icon: Send },
      { id: 'media-library', label: 'Media Library', Icon: ImageIcon },
    ]
  },
  {
    title: 'GENERAL',
    items: [
      { id: 'admin-settings', label: 'Settings', Icon: Settings },
      { id: 'about', label: 'About Us', Icon: Info },
    ]
  }
];

export default function Sidebar({ activePage, onPageChange, collapsed, setCollapsed, user }) {
  const isAllowed = (itemId) => {
    if (user?.role === 'admin' || !Array.isArray(user?.pages)) return true;
    if (itemId === 'admin-settings') {
      return user.pages.some(p => p.startsWith('admin-settings'));
    }
    return user.pages.includes(itemId);
  };

  return (
    <div style={{
      width: collapsed ? 72 : 240,
      minHeight: '100%',
      background: C.sidebarBg,
      borderRight: `1px solid ${C.sidebarBorder}`,
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      transition: 'width .22s cubic-bezier(0.4, 0, 0.2, 1)',
      overflow: 'hidden',
      position: 'relative',
      userSelect: 'none',
    }}>
      {/* Nav Groups */}
      <div style={{ padding: collapsed ? '16px 8px' : '16px 12px', flex: 1, overflowY: 'auto' }}>
        {NAV_GROUPS.map((group, gIdx) => {
          const visibleGroupItems = group.items.filter(it => isAllowed(it.id));
          if (visibleGroupItems.length === 0) return null;

          return (
            <div key={group.title} style={{ marginBottom: collapsed ? 12 : 20 }}>
              {!collapsed && (
                <div style={{
                  fontSize: 10,
                  fontWeight: 800,
                  letterSpacing: '0.08em',
                  color: '#9CA3AF',
                  textTransform: 'uppercase',
                  padding: '0 12px 6px',
                  fontFamily: FONT,
                }}>
                  {group.title}
                </div>
              )}

              {visibleGroupItems.map(item => {
                const active = activePage === item.id || (item.id === 'admin-settings' && activePage.startsWith('admin-settings'));
                return (
                  <div
                    key={item.id}
                    onClick={() => onPageChange(item.id)}
                    title={collapsed ? item.label : ''}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: collapsed ? 0 : 12,
                      padding: collapsed ? '11px 0' : '10px 14px',
                      borderRadius: 12,
                      cursor: 'pointer',
                      transition: 'all .15s ease',
                      marginBottom: 3,
                      background: active ? '#FF5A00' : 'transparent',
                      color: active ? '#FFFFFF' : '#4B5563',
                      boxShadow: active ? '0 4px 14px rgba(255, 90, 0, 0.28)' : 'none',
                      justifyContent: collapsed ? 'center' : 'flex-start',
                      fontFamily: FONT,
                      fontSize: 13,
                      fontWeight: active ? 700 : 500,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                    }}
                    onMouseEnter={e => {
                      if (!active) {
                        e.currentTarget.style.background = '#F3F4F6';
                        e.currentTarget.style.color = '#111827';
                      }
                    }}
                    onMouseLeave={e => {
                      if (!active) {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = '#4B5563';
                      }
                    }}
                  >
                    <span style={{
                      width: 20,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      color: active ? '#FFFFFF' : '#6B7280',
                    }}>
                      <item.Icon size={18} strokeWidth={active ? 2.5 : 2} />
                    </span>
                    {!collapsed && (
                      <span style={{ letterSpacing: '-0.01em', flex: 1 }}>
                        {item.label}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>

      {/* Collapse button */}
      <div style={{ borderTop: `1px solid ${C.sidebarBorder}`, padding: '8px 12px 14px' }}>
        <div
          onClick={() => setCollapsed(p => !p)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: collapsed ? '10px 0' : '10px 12px',
            borderRadius: 10,
            cursor: 'pointer',
            justifyContent: collapsed ? 'center' : 'flex-start',
            transition: 'background .15s',
            color: '#6B7280',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = '#F3F4F6'; e.currentTarget.style.color = '#111827'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#6B7280'; }}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <span style={{ display: 'flex', alignItems: 'center' }}>
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </span>
          {!collapsed && (
            <span style={{ fontSize: 13, fontWeight: 600, fontFamily: FONT }}>
              Collapse Sidebar
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
