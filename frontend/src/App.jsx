import { useState, useEffect } from 'react';
import { api } from './api.js';
import { C, FONT } from './constants.js';
import { useHashRoute } from './hooks/useHashRoute.js';
import LoginGate from './components/LoginGate.jsx';
import SetupWizard from './components/SetupWizard.jsx';
import Topbar from './components/Topbar.jsx';
import Sidebar from './components/Sidebar.jsx';
import ChatsPage from './components/ChatsPage.jsx';
import HomePage from './pages/HomePage.jsx';
import ChatbotBuilderPage from './pages/ChatbotBuilderPage.jsx';
import TemplateBuilderPage from './pages/TemplateBuilderPage.jsx';
import ContactsPage from './pages/ContactsPage.jsx';
import BulkMessagePage from './pages/BulkMessagePage.jsx';
import AdminSettingsPage from './pages/AdminSettingsPage.jsx';
import MediaLibraryPage from './pages/MediaLibraryPage.jsx';
import PipelinesPage from './pages/PipelinesPage.jsx';
import AiAgentBuilderPage from './pages/AiAgentBuilderPage.jsx';
import SuperAdminPage from './pages/SuperAdminPage.jsx';

const VALID_PAGES = new Set([
  'home', 'chatbot-builder', 'template-builder', 'chats',
  'contacts', 'pipelines', 'bulk-message', 'admin-settings', 'media-library',
  'ai-agent-builder', 'super-admin',
]);

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [setupRequired, setSetupRequired] = useState(false);
  const [routeParts, navigate, replaceRoute] = useHashRoute();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const page = VALID_PAGES.has(routeParts[0]) ? routeParts[0] : 'home';
  const subParts = routeParts.slice(1);
  const setPage = (p) => navigate(p);

  // Normalize empty hash to #/home so reload always shows a valid URL
  useEffect(() => {
    if (!routeParts[0]) replaceRoute('home');
  }, [routeParts, replaceRoute]);

  // Page guard: non-admins cannot access super-admin and can only reach pages granted to them.
  useEffect(() => {
    if (!user) return;
    if (page === 'super-admin' && user.role !== 'admin') {
      setPage('home');
      return;
    }
    if (user.role === 'admin' || !Array.isArray(user.pages)) return;

    // Check client module gate if active
    const orgModules = user?.activeOrg?.settings?.modules;
    if (orgModules) {
      if (page === 'ai-agent-builder' && orgModules.agents === false) return setPage('home');
      if (page === 'bulk-message' && orgModules.broadcasts === false) return setPage('home');
      if (page === 'pipelines' && orgModules.pipelines === false) return setPage('home');
      if (page === 'chatbot-builder' && orgModules.chatbots === false) return setPage('home');
    }

    const allowed = page === 'admin-settings'
      ? user.pages.some(p => p.startsWith('admin-settings'))
      : user.pages.includes(page);
    if (!allowed) setPage('home');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, user]);

  useEffect(() => {
    // Collapse main sidebar by default on automation builder page
    if (page === 'chatbot-builder') {
      setSidebarCollapsed(true);
    }
  }, [page]);

  useEffect(() => {
    // First check whether the instance needs first-run setup (no users yet).
    // If so, show the setup wizard; otherwise resume the normal session check.
    api.auth.status()
      .then(({ setupRequired: needed }) => {
        if (needed) { setSetupRequired(true); setChecking(false); return null; }
        return api.auth.me()
          .then(({ user }) => setUser(user))
          .catch(() => setUser(null))
          .finally(() => setChecking(false));
      })
      .catch(() => {
        // status unavailable (DB warming) — fall back to a normal session check.
        api.auth.me()
          .then(({ user }) => setUser(user))
          .catch(() => setUser(null))
          .finally(() => setChecking(false));
      });
  }, []);

  const handleLogout = async () => {
    await api.auth.logout().catch(() => {});
    setUser(null);
    setPage('home');
  };

  if (checking) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: FONT,
        background: C.pageBg,
      }}>
        <div style={{ fontSize: 13, color: C.textMuted, fontWeight: 500 }}>Loading…</div>
      </div>
    );
  }

  if (setupRequired && !user) {
    return <SetupWizard onComplete={(u) => { setSetupRequired(false); setUser(u); }} />;
  }

  if (!user) {
    return <LoginGate onLogin={setUser} />;
  }

  const renderPage = () => {
    switch (page) {
      case 'home': return <HomePage user={user} onPageChange={setPage} />;
      case 'chats': return <ChatsPage subParts={subParts} navigate={navigate} user={user} />;
      case 'contacts': return <ContactsPage user={user} onNavigate={navigate} />;
      case 'pipelines': return <PipelinesPage user={user} />;
      case 'template-builder': return <TemplateBuilderPage subParts={subParts} navigate={navigate} />;
      case 'media-library': return <MediaLibraryPage />;
      case 'bulk-message': return <BulkMessagePage onNavigate={navigate} />;
      case 'chatbot-builder': return <ChatbotBuilderPage subParts={subParts} navigate={navigate} />;
      case 'ai-agent-builder': return <AiAgentBuilderPage user={user} navigate={navigate} />;
      case 'super-admin': return <SuperAdminPage user={user} onOrgSwitch={() => api.auth.me().then(({ user }) => setUser(user))} />;
      case 'admin-settings': return <AdminSettingsPage onLogout={handleLogout} onNavigate={setPage} subParts={subParts} navigate={navigate} user={user} />;
      default: return <HomePage user={user} onPageChange={setPage} />;
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      fontFamily: FONT,
      background: C.pageBg,
    }}>
      <Topbar user={user} onLogout={handleLogout} onNavigate={setPage} />
      {user?.role === 'admin' && user?.activeOrg && page !== 'super-admin' && (
        <div style={{
          background: '#0284c7', color: '#fff', padding: '6px 20px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          fontSize: 12, fontWeight: 500
        }}>
          <div>
            Active Workspace: <strong>{user.activeOrg.name}</strong> ({user.activeOrg.slug}) — Plan: <strong>{user.activeOrg.plan?.toUpperCase()}</strong>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <span
              onClick={() => setPage('super-admin')}
              style={{ cursor: 'pointer', textDecoration: 'underline', fontWeight: 600 }}
            >
              ⚙ Open Super Admin Switchboard
            </span>
          </div>
        </div>
      )}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {page !== 'admin-settings' && (
          <Sidebar
            activePage={page}
            onPageChange={setPage}
            collapsed={sidebarCollapsed}
            setCollapsed={setSidebarCollapsed}
            user={user}
          />
        )}
        <div style={{ flex: 1, overflow: 'auto', background: C.pageBg, display: 'flex', flexDirection: 'column' }}>
          {renderPage()}
        </div>
      </div>
    </div>
  );
}
