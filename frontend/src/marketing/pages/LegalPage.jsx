import { Shield, FileText, Trash2, ArrowLeft } from 'lucide-react';
import { C, FONT } from '../../constants.js';

const LEGAL_DOCS = {
  'privacy-policy': {
    badge: 'Privacy & Data Protection',
    title: 'Privacy Policy',
    updatedAt: 'November 11, 2026',
    icon: Shield,
    intro:
      'Synaptic Info ("we", "our", "us") operates the Synaptic Chat platform. This Privacy Policy explains how we collect, use, store, and protect information when businesses connect their WhatsApp Business Accounts via the official Meta WhatsApp Cloud API and interact with end users through Synaptic Chat.',
    sections: [
      {
        heading: '1. Information We Collect',
        bullets: [
          'Account & Workspace Information: organization name, administrator and team member names, email addresses, role permissions, and workspace settings.',
          'WhatsApp Business & Messaging Data: WhatsApp Business Account IDs (WABA ID), Phone Number IDs, recipient/sender phone numbers, display/profile names, message content, templates, delivery/read status receipts, and media attachments exchanged through connected WhatsApp Business numbers.',
          'Integration Credentials (Encrypted): permanent Meta System User access tokens, optional third-party AI provider keys (BYOK), and Google OAuth/Sheets tokens stored encrypted at rest using AES-256-GCM.',
          'Operational Logs: webhook delivery events, automation execution logs, and API request metadata needed for security, troubleshooting, and reliability.',
        ],
      },
      {
        heading: '2. How We Use Information',
        bullets: [
          'Deliver, receive, and display WhatsApp Cloud API messages, templates, broadcasts, and status updates inside your organization’s shared inbox.',
          'Execute workspace automations, CRM pipelines, order tracking updates, and optional AI agent responses configured by your workspace administrators.',
          'Authenticate users, enforce multi-tenant organization isolation, detect abuse, and verify Meta webhook signatures.',
          'Provide customer support and fulfill legal or regulatory obligations.',
        ],
      },
      {
        heading: '3. Data Sharing & Third-Party Processors',
        bullets: [
          'Meta Platforms, Inc. (WhatsApp Cloud API): outbound messages, templates, and media are transmitted to Meta to deliver WhatsApp conversations.',
          'Customer-Configured Integrations: if an organization connects OpenAI, Anthropic, Google Sheets, Shopify, Razorpay, or Shiprocket, only the data required to run that configured integration is sent to the selected provider.',
          'We do not sell, rent, or trade personal data or WhatsApp conversation records to third-party data brokers or advertisers.',
        ],
      },
      {
        heading: '4. Multi-Tenant Isolation, Security & Retention',
        bullets: [
          'Each client organization is logically isolated by organization ID across contacts, chat history, templates, pipelines, and WhatsApp credentials.',
          'Access tokens and API secrets are encrypted at rest with AES-256-GCM and transmitted exclusively over HTTPS/TLS.',
          'We retain workspace and conversation data for as long as the workspace account remains active or as instructed by the workspace administrator, after which records are purged or anonymized upon deletion request.',
        ],
      },
      {
        heading: '5. Your Rights & Contact Information',
        bullets: [
          'End users and workspace administrators may request access, correction, export, or deletion of personal data at any time.',
          'For privacy inquiries or data protection requests, contact Synaptic Info at support@synapticchat.com or via our Contact page.',
        ],
      },
    ],
  },
  terms: {
    badge: 'Platform Terms',
    title: 'Terms of Service',
    updatedAt: 'November 11, 2026',
    icon: FileText,
    intro:
      'These Terms of Service govern your access to and use of Synaptic Chat, operated by Synaptic Info. By creating a workspace or connecting a WhatsApp Business Account, you agree to comply with these terms.',
    sections: [
      {
        heading: '1. Meta & WhatsApp Policy Compliance',
        bullets: [
          'You are responsible for ensuring all messages, templates, and broadcasts sent through your connected WhatsApp Business Account comply with Meta’s WhatsApp Business Messaging Policy, Commerce Policy, and applicable anti-spam/opt-in laws.',
          'You must obtain clear end-user opt-in consent before sending proactive marketing or utility template messages.',
        ],
      },
      {
        heading: '2. Workspace Accounts & API Credentials',
        bullets: [
          'Workspace owners are responsible for safeguarding user credentials, System User access tokens, and any Bring-Your-Own-Key (BYOK) AI provider keys configured inside their organization.',
          'Do not share unauthorized access across organizations or attempt to bypass tenant isolation or Feature Switchboard quotas.',
        ],
      },
      {
        heading: '3. Acceptable Use',
        bullets: [
          'You may not use Synaptic Chat to transmit unlawful content, phishing, unsolicited spam, malware, or automated traffic designed to disrupt platform availability or Meta Graph API rate limits.',
        ],
      },
      {
        heading: '4. Service Availability & Liability',
        bullets: [
          'Synaptic Chat integrates with external APIs including Meta WhatsApp Cloud API, payment gateways, and AI providers; delivery speed and uptime depend in part on those upstream services.',
          'To the maximum extent permitted by law, Synaptic Info provides the service on an "as-is" and "as-available" basis.',
        ],
      },
      {
        heading: '5. Contact',
        bullets: [
          'Questions about these Terms can be sent to support@synapticchat.com.',
        ],
      },
    ],
  },
  'data-deletion': {
    badge: 'Meta Platform Compliance',
    title: 'User Data Deletion Instructions',
    updatedAt: 'November 11, 2026',
    icon: Trash2,
    intro:
      'In accordance with Meta Platform Terms, end users and workspace administrators may request permanent deletion of WhatsApp messaging data, contact records, media attachments, and connected account credentials stored in Synaptic Chat.',
    sections: [
      {
        heading: '1. Self-Service Removal for Workspace Administrators',
        bullets: [
          'Log in to your Synaptic Chat workspace and remove connected WhatsApp Business Accounts, contacts, templates, or uploaded media directly from Settings and Contacts.',
          'To revoke Meta API access immediately, remove Synaptic Chat’s System User or partner asset permissions inside Meta Business Settings.',
        ],
      },
      {
        heading: '2. Submitting a Full Data Deletion Request',
        bullets: [
          'Email support@synapticchat.com with the subject line "Data Deletion Request".',
          'Include your organization name (or WhatsApp phone number / WABA ID) and the specific contact number or account records to be deleted.',
        ],
      },
      {
        heading: '3. Verification & Completion Timeline',
        bullets: [
          'We verify requester ownership before deleting tenant or end-user data to prevent unauthorized removal.',
          'Verified deletion requests are processed across active database tables and media storage within 7 business days, and confirmation is sent to the requester’s email address.',
        ],
      },
    ],
  },
};

export default function LegalPage({ page = 'privacy-policy', onNavigate }) {
  const doc = LEGAL_DOCS[page] || LEGAL_DOCS['privacy-policy'];
  const Icon = doc.icon;

  return (
    <div style={{ fontFamily: FONT, background: C.pageBg, color: C.text, paddingBottom: 80 }}>
      <section style={{ maxWidth: 860, margin: '0 auto', padding: '56px 24px 0' }}>
        <button
          type="button"
          onClick={() => onNavigate('landing')}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            background: 'none',
            border: 'none',
            padding: 0,
            color: C.textSecondary,
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            marginBottom: 24,
            fontFamily: 'inherit',
          }}
        >
          <ArrowLeft size={14} /> Back to Home
        </button>

        <div
          style={{
            background: '#ffffff',
            borderRadius: 20,
            border: `1px solid ${C.border}`,
            padding: '40px clamp(24px, 4vw, 48px)',
            boxShadow: C.shadowSm,
          }}
        >
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              background: '#FEE2E2',
              color: C.primary,
              padding: '5px 14px',
              borderRadius: 20,
              fontSize: 12,
              fontWeight: 700,
              marginBottom: 16,
            }}
          >
            <Icon size={14} /> {doc.badge}
          </div>

          <h1 style={{ fontSize: 'clamp(28px, 4vw, 40px)', fontWeight: 800, letterSpacing: '-0.02em', margin: '0 0 8px' }}>
            {doc.title}
          </h1>
          <div style={{ fontSize: 13, color: C.textMuted, marginBottom: 24 }}>
            Effective Date: {doc.updatedAt} · Synaptic Chat by Synaptic Info
          </div>

          <p style={{ fontSize: 15, color: C.textSecondary, lineHeight: 1.7, margin: '0 0 32px' }}>
            {doc.intro}
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
            {doc.sections.map((section) => (
              <div key={section.heading} style={{ borderTop: `1px solid ${C.border}`, paddingTop: 20 }}>
                <h2 style={{ fontSize: 18, fontWeight: 700, color: C.text, margin: '0 0 12px' }}>
                  {section.heading}
                </h2>
                <ul style={{ margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {section.bullets.map((item) => (
                    <li key={item} style={{ fontSize: 14, color: C.textSecondary, lineHeight: 1.65 }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div
            style={{
              marginTop: 36,
              paddingTop: 20,
              borderTop: `1px solid ${C.border}`,
              display: 'flex',
              flexWrap: 'wrap',
              gap: 16,
              fontSize: 13,
            }}
          >
            <button
              type="button"
              onClick={() => onNavigate('privacy-policy')}
              style={{ background: 'none', border: 'none', padding: 0, color: page === 'privacy-policy' ? C.primary : C.textSecondary, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}
            >
              Privacy Policy
            </button>
            <button
              type="button"
              onClick={() => onNavigate('terms')}
              style={{ background: 'none', border: 'none', padding: 0, color: page === 'terms' ? C.primary : C.textSecondary, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}
            >
              Terms of Service
            </button>
            <button
              type="button"
              onClick={() => onNavigate('data-deletion')}
              style={{ background: 'none', border: 'none', padding: 0, color: page === 'data-deletion' ? C.primary : C.textSecondary, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}
            >
              Data Deletion Instructions
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
