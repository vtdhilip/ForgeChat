import { Shield } from 'lucide-react';
import { C, FONT } from '../constants.js';

const linkBtnStyle = {
  background: 'none',
  border: 'none',
  padding: 0,
  color: '#A1A1AA',
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontSize: 13,
  textAlign: 'left',
};

export default function MarketingFooter({ onNavigate, onOpenDemo }) {
  return (
    <footer
      style={{
        background: '#0F0F10',
        color: '#E5E5E0',
        padding: '56px 24px 32px',
        borderTop: '1px solid rgba(255, 255, 255, 0.12)',
        fontFamily: FONT,
      }}
    >
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 40,
            marginBottom: 48,
          }}
        >
          {/* Column 1: Brand & Overview */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
              <img
                src="/synaptic-logo.svg"
                alt="Synaptic Chat"
                style={{ width: 28, height: 28, objectFit: 'contain' }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <span style={{ fontSize: 18, fontWeight: 800, color: '#ffffff', letterSpacing: '-0.02em' }}>
                Synaptic Chat
              </span>
            </div>
            <p style={{ fontSize: 13, color: '#A1A1AA', lineHeight: 1.6, margin: '0 0 16px' }}>
              The multi-tenant WhatsApp CRM platform by Synaptic Info, combining autonomous AI agents, shared team inboxes, deal pipelines, and Meta Cloud API automations.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#25D366' }}>
              <Shield size={14} /> Official Meta Cloud API Architecture
            </div>
          </div>

          {/* Column 2: Platform Capabilities */}
          <div>
            <h4 style={{ fontSize: 14, fontWeight: 700, color: '#ffffff', margin: '0 0 14px' }}>
              Capabilities
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13, alignItems: 'flex-start' }}>
              <button type="button" onClick={() => onNavigate('features')} style={linkBtnStyle}>
                Shared Team Inbox
              </button>
              <button type="button" onClick={() => onNavigate('features')} style={linkBtnStyle}>
                Autonomous AI Agents (BYOK)
              </button>
              <button type="button" onClick={() => onNavigate('features')} style={linkBtnStyle}>
                Visual Flow Automations
              </button>
              <button type="button" onClick={() => onNavigate('features')} style={linkBtnStyle}>
                Sales Pipelines & Kanban
              </button>
              <button type="button" onClick={() => onNavigate('features')} style={linkBtnStyle}>
                Bulk Broadcast Campaigns
              </button>
            </div>
          </div>

          {/* Column 3: Industries */}
          <div>
            <h4 style={{ fontSize: 14, fontWeight: 700, color: '#ffffff', margin: '0 0 14px' }}>
              Solutions
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13, alignItems: 'flex-start' }}>
              <button type="button" onClick={() => onNavigate('solutions')} style={linkBtnStyle}>
                D2C & E-Commerce Orders
              </button>
              <button type="button" onClick={() => onNavigate('solutions')} style={linkBtnStyle}>
                Healthcare & Clinic Appointments
              </button>
              <button type="button" onClick={() => onNavigate('solutions')} style={linkBtnStyle}>
                Real Estate & Lead Qualification
              </button>
              <button type="button" onClick={() => onNavigate('solutions')} style={linkBtnStyle}>
                Agencies & Multi-Tenant White Label
              </button>
            </div>
          </div>

          {/* Column 4: Resources & Enterprise */}
          <div>
            <h4 style={{ fontSize: 14, fontWeight: 700, color: '#ffffff', margin: '0 0 14px' }}>
              Enterprise & Pricing
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13, alignItems: 'flex-start' }}>
              <button type="button" onClick={() => onNavigate('pricing')} style={linkBtnStyle}>
                Pricing Plans & Calculator
              </button>
              <button type="button" onClick={() => onNavigate('about')} style={linkBtnStyle}>
                Security & Data Residency
              </button>
              <button type="button" onClick={onOpenDemo} style={linkBtnStyle}>
                Book Enterprise Demo
              </button>
              <button type="button" onClick={() => onNavigate('login')} style={linkBtnStyle}>
                Customer Portal Sign In
              </button>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div
          style={{
            paddingTop: 24,
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 14,
            fontSize: 12,
            color: '#71717A',
          }}
        >
          <div>
            © {new Date().getFullYear()} Synaptic Info. All rights reserved.
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
            <button type="button" onClick={() => onNavigate('privacy-policy')} style={{ ...linkBtnStyle, fontSize: 12, color: '#71717A' }}>
              Privacy Policy
            </button>
            <button type="button" onClick={() => onNavigate('terms')} style={{ ...linkBtnStyle, fontSize: 12, color: '#71717A' }}>
              Terms of Service
            </button>
            <button type="button" onClick={() => onNavigate('data-deletion')} style={{ ...linkBtnStyle, fontSize: 12, color: '#71717A' }}>
              Data Deletion
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
}
