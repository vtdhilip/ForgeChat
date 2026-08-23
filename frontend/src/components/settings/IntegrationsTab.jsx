import { useState, useEffect, useCallback } from 'react';
import {
  ArrowLeft, ChevronRight, Loader2, CreditCard, Truck,
  Zap, FileSpreadsheet, Bot, Globe, Sliders
} from 'lucide-react';
import { api } from '../../api.js';
import { C, FONT } from '../../constants.js';
import GoogleIntegrationsTab from './GoogleIntegrationsTab.jsx';
import AiModelsTab from './AiModelsTab.jsx';
import IntegrationsConfigTab from './IntegrationsConfigTab.jsx';

export default function IntegrationsTab({ subParts = [], navigate }) {
  const selected = subParts[1] || null;
  const goCards = () => navigate && navigate('admin-settings', 'integrations');
  const goDetail = (key) => navigate && navigate('admin-settings', 'integrations', key);

  if (selected === 'google') {
    return <DetailShell title="Google OAuth" onBack={goCards}><GoogleIntegrationsTab /></DetailShell>;
  }
  if (selected === 'ai-models') {
    return <DetailShell title="AI Models" onBack={goCards}><AiModelsTab /></DetailShell>;
  }
  if (selected === 'config' || selected === 'razorpay' || selected === 'shiprocket' || selected === 'flows' || selected === 'sheets') {
    return <DetailShell title="Environment & Credentials" onBack={goCards}><IntegrationsConfigTab /></DetailShell>;
  }
  return <CardGrid onOpen={goDetail} />;
}

function DetailShell({ title, onBack, children }) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '14px 40px 0', flexShrink: 0, fontFamily: FONT,
      }}>
        <button onClick={onBack}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 10px', borderRadius: 8, border: 'none',
            background: 'transparent', cursor: 'pointer',
            fontSize: 13, fontWeight: 600, color: C.textSecondary, fontFamily: FONT,
          }}
          onMouseEnter={e => { e.currentTarget.style.background = '#f0f2f5'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
        >
          <ArrowLeft size={15} /> Integrations
        </button>
        <ChevronRight size={14} color={C.textMuted} />
        <span style={{ fontSize: 13, fontWeight: 700, color: C.text }}>{title}</span>
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        {children}
      </div>
    </div>
  );
}

function CardGrid({ onOpen }) {
  const [integrations, setIntegrations] = useState({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { organizations, activeOrgId } = await api.organizations.list();
      const orgId = activeOrgId || (organizations[0] && organizations[0].id);
      if (orgId) {
        const { integrations: config } = await api.organizations.getIntegrations(orgId);
        setIntegrations(config || {});
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const hasRzp = !!(integrations.razorpay_key_id && integrations.razorpay_key_secret);
  const hasShiprocket = !!(integrations.shiprocket_email || integrations.shiprocket_token);
  const hasSheets = !!integrations.google_sheet_webhook_url;
  const hasFlows = !!integrations.whatsapp_flow_id;
  const hasAi = !!(integrations.openai_api_key || integrations.anthropic_api_key);

  return (
    <div style={{ flex: 1, padding: '32px 40px', overflowY: 'auto', fontFamily: FONT }}>
      <div style={{ width: '100%', maxWidth: 960 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, color: C.text, margin: 0, letterSpacing: '-.02em' }}>
              Integrations & Environment
            </h1>
            <p style={{ fontSize: 13, color: C.textMuted, margin: '4px 0 0' }}>
              Manage credentials, payment gateways, logistics, Meta Flows, and webhook connections.
            </p>
          </div>
          <button
            onClick={() => onOpen('config')}
            style={{
              display: 'flex', alignItems: 'center', gap: 8, background: '#FF5A00',
              color: '#fff', border: 'none', padding: '9px 16px', borderRadius: 10,
              fontSize: 13, fontWeight: 700, cursor: 'pointer', fontFamily: FONT,
              boxShadow: '0 4px 12px rgba(255, 90, 0, 0.25)',
            }}
          >
            <Sliders size={15} />
            <span>Manage All Credentials</span>
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
          {/* Razorpay */}
          <IntegrationCard
            icon={<CreditCard size={20} color="#EA580C" />}
            iconBg="#FFF7ED"
            title="Razorpay Payment Gateway"
            desc="Automated order checkout & dynamic payment links in WhatsApp"
            status={hasRzp ? <Connected>Configured (Live)</Connected> : <Muted>Not configured</Muted>}
            onClick={() => onOpen('config')}
          />

          {/* Shiprocket */}
          <IntegrationCard
            icon={<Truck size={20} color="#2563EB" />}
            iconBg="#EFF6FF"
            title="Shiprocket Logistics"
            desc="Auto-creates shipments, courier pickups & AWB tracking"
            status={hasShiprocket ? <Connected>Connected</Connected> : <Muted>Not configured</Muted>}
            onClick={() => onOpen('config')}
          />

          {/* WhatsApp Meta Flows */}
          <IntegrationCard
            icon={<Zap size={20} color="#9333EA" />}
            iconBg="#FAF5FF"
            title="WhatsApp Meta Flows"
            desc="Native in-app delivery address capture form popups"
            status={hasFlows ? <Connected>Flow ID Active</Connected> : <Muted>Not set</Muted>}
            onClick={() => onOpen('config')}
          />

          {/* Google Sheets Sync */}
          <IntegrationCard
            icon={<FileSpreadsheet size={20} color="#FF5A00" />}
            iconBg="#FFF0E6"
            title="Google Sheets Sync"
            desc="Real-time order & lead row sync via Google Apps Script"
            status={hasSheets ? <Connected>Webhook Active</Connected> : <Muted>No webhook set</Muted>}
            onClick={() => onOpen('config')}
          />

          {/* AI Providers */}
          <IntegrationCard
            icon={<Bot size={20} color="#9333EA" />}
            iconBg="#FAF5FF"
            title="AI Providers (OpenAI & Anthropic)"
            desc="Powers autonomous AI chat agents and smart summarization"
            status={hasAi ? <Connected>API Keys Configured</Connected> : <Muted>No keys set</Muted>}
            onClick={() => onOpen('config')}
          />

          {/* Google OAuth */}
          <IntegrationCard
            icon={<Globe size={20} color="#4285F4" />}
            iconBg="#E8F0FE"
            title="Google OAuth Services"
            desc="Connect Gmail, Google Drive, and OAuth Google Sheets"
            status={<Muted>OAuth Client</Muted>}
            onClick={() => onOpen('google')}
          />
        </div>
      </div>
    </div>
  );
}

function IntegrationCard({ icon, iconBg, title, desc, status, onClick }) {
  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      style={{
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        padding: 20, borderRadius: 16, background: '#FFFFFF',
        border: `1px solid #ECEEF1`, cursor: 'pointer',
        transition: 'all .15s ease', fontFamily: FONT,
        minHeight: 140,
      }}
      onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 6px 20px rgba(0,0,0,0.06)'; e.currentTarget.style.transform = 'translateY(-2px)'; }}
      onMouseLeave={e => { e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.transform = 'translateY(0)'; }}
    >
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ width: 38, height: 38, borderRadius: 10, background: iconBg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {icon}
          </div>
          <ChevronRight size={16} color="#9CA3AF" />
        </div>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#111827' }}>{title}</div>
        <div style={{ fontSize: 12, color: '#6B7280', marginTop: 4, lineHeight: 1.4 }}>{desc}</div>
      </div>
      <div style={{ marginTop: 14, borderTop: '1px solid #F3F4F6', paddingTop: 12 }}>
        {status}
      </div>
    </div>
  );
}

function Connected({ children }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 6, background: '#FFF0E6', color: '#FF5A00' }}>
      ● {children}
    </span>
  );
}

function Muted({ children }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 6, background: '#F3F4F6', color: '#6B7280' }}>
      {children}
    </span>
  );
}
