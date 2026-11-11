import { useState } from 'react';
import {
  MessageSquare, Bot, KanbanSquare, Megaphone, Zap,
  CheckCircle2, ArrowRight, ShieldCheck, Sparkles, Database, FileSpreadsheet
} from 'lucide-react';
import { C, FONT, MONO } from '../../constants.js';

export default function FeaturesPage({ onNavigate, onOpenDemo }) {
  const [activeTab, setActiveTab] = useState('inbox');

  const features = {
    inbox: {
      title: 'Shared Team Inbox & Multi-Agent Collaboration',
      badge: 'Zero-Collision Inbox',
      color: '#2563EB',
      bgLight: '#EFF6FF',
      description: 'Multiple sales and customer support reps can respond from the same WhatsApp Business numbers without stepping on each other.',
      points: [
        'Real-time typing awareness and collision indicators when multiple agents view a chat.',
        'One-click conversation assignment to team members or specific sales queues.',
        'Internal notes visible only to your team, attached directly to the message timeline.',
        'Pre-approved quick replies and canned responses for lightning-fast replies.',
        'Support for rich media: Ogg voice notes (transcoded to MP3 for Safari), images, PDFs, and documents.',
      ],
      previewSnippet: 'Unified Inbox · 12 Agents Active · 0 Collision',
    },
    agents: {
      title: 'Autonomous AI Agents with Tool Calling (BYOK)',
      badge: 'Autonomous Intelligence',
      color: C.primary,
      bgLight: '#FCEBEB',
      description: 'Deploy 24/7 AI agents that behave like your best support specialists. Bring Your Own Keys (BYOK) for OpenAI, Anthropic, Gemini, or DeepSeek.',
      points: [
        'Custom system prompts and business personality instructions customized per channel.',
        'Native tool calling: Query live product catalog, calculate order delivery status, or fetch inventory.',
        'Automated Google Sheets sync: Log qualified customer leads in real time.',
        'Intelligent human escalation: Automatically detects frustration or complex inquiries and hands off to human staff.',
        'Model flexibility: Switch between GPT-4o, Claude 3.5 Sonnet, and local models seamlessly.',
      ],
      previewSnippet: 'Agent "Atlas" · Active · 94.2% Resolution Without Human Takeover',
    },
    pipelines: {
      title: 'Visual Deals & Sales CRM Pipelines',
      badge: 'Lead Conversion',
      color: '#16a34a',
      bgLight: '#F0FDF4',
      description: 'Manage sales deals directly from WhatsApp chats on an interactive drag-and-drop Kanban board.',
      points: [
        'Custom pipeline stages: New Lead, Qualified, Demo Scheduled, Proposal Sent, Won, Lost.',
        'Deal monetary value tracking with currency formatting and conversion rates.',
        'Click directly into the chat history from any deal card on the board.',
        'Automatic stage advancement triggered by keyword replies or bot decisions.',
        'Filtering by sales representative, date ranges, and custom tags.',
      ],
      previewSnippet: 'Active Pipeline · ₹1,15,00,000 Deal Pipeline Volume',
    },
    templates: {
      title: 'Meta Approved Template Builder & Bulk Broadcasts',
      badge: 'Official WhatsApp API',
      color: '#9333EA',
      bgLight: '#FAF5FF',
      description: 'Draft, validate, and broadcast official Meta Cloud WhatsApp message templates with complete compliance.',
      points: [
        'Support for Header types: None, Text, Image, Video, and Document headers.',
        'Dynamic placeholder variables {{1}}, {{2}} with real-time live WhatsApp preview.',
        'Call-to-Action (CTA) and Quick Reply buttons with custom URLs and phone call triggers.',
        'Segmented CSV bulk message delivery with rate-limiting and anti-ban safeguards.',
        'Delivery, read-receipt, and failure analytics tracked in real time.',
      ],
      previewSnippet: 'Meta Approved · Category: Marketing / Utility · 98.4% Delivery',
    },
    automations: {
      title: 'Visual Flow Automations & Decision Trees',
      badge: 'Visual Workflow Builder',
      color: '#D97706',
      bgLight: '#FFFBEB',
      description: 'Create multi-step conversational flows without writing code. Automate FAQs, lead scoring, and routing.',
      points: [
        'Visual block canvas with Trigger, Condition, Action, and Delay nodes.',
        'Interactive list messages and multi-button menus sent directly via WhatsApp.',
        'Time-based follow-up sequences for abandoned carts and re-engagement.',
        'Webhook triggers to initiate flows from Stripe, Shopify, or external CRM webhooks.',
        'Comprehensive step-by-step execution logs with pausing, retry, and error inspection.',
      ],
      previewSnippet: 'Workflow: "New Inbound Qualification" · 1,480 Runs Completed',
    },
  };

  const current = features[activeTab];

  return (
    <div style={{ fontFamily: FONT, background: C.pageBg, color: C.text, paddingBottom: 80 }}>
      {/* Header */}
      <section style={{ padding: '60px 24px 40px', maxWidth: 1000, margin: '0 auto', textAlign: 'center' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: '#FEE2E2', color: C.primary, padding: '5px 14px', borderRadius: 20, fontSize: 12, fontWeight: 700, marginBottom: 16 }}>
          <Sparkles size={14} /> Full Platform Overview
        </div>
        <h1 style={{ fontSize: 'clamp(32px, 4.5vw, 48px)', fontWeight: 800, letterSpacing: '-0.02em', margin: '0 0 16px' }}>
          Engineered for high-volume WhatsApp customer engagement
        </h1>
        <p style={{ fontSize: 16, color: C.textSecondary, lineHeight: 1.6, maxWidth: 620, margin: '0 auto' }}>
          Explore the tools and capabilities built into Synaptic Chat that empower modern teams to drive revenue and resolve support inquiries automatically.
        </p>
      </section>

      {/* Tabs Switcher */}
      <section style={{ maxWidth: 1100, margin: '0 auto 36px', padding: '0 24px' }}>
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: 8,
            paddingBottom: 12,
            borderBottom: `1px solid ${C.border}`,
          }}
        >
          {[
            { key: 'inbox', label: 'Shared Inbox', icon: MessageSquare },
            { key: 'agents', label: 'AI Agents (BYOK)', icon: Bot },
            { key: 'pipelines', label: 'Deals & Pipelines', icon: KanbanSquare },
            { key: 'templates', label: 'Templates & Broadcasts', icon: Megaphone },
            { key: 'automations', label: 'Flow Automations', icon: Zap },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '10px 16px',
                  borderRadius: 10,
                  border: active ? `1px solid ${C.borderDark}` : '1px solid transparent',
                  background: active ? '#ffffff' : 'transparent',
                  color: active ? C.text : C.textSecondary,
                  fontSize: 13.5,
                  fontWeight: active ? 700 : 500,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  boxShadow: active ? C.shadowSm : 'none',
                  transition: 'all .15s',
                }}
              >
                <Icon size={16} color={active ? C.primary : C.textMuted} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </section>

      {/* Active Tab Deep-Dive Feature Card */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '0 24px' }}>
        <div
          style={{
            background: '#ffffff',
            borderRadius: 20,
            border: `1px solid ${C.border}`,
            padding: '40px',
            boxShadow: '0 10px 30px rgba(0, 0, 0, 0.05)',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: 40,
            alignItems: 'center',
          }}
        >
          <div>
            <div
              style={{
                display: 'inline-block',
                padding: '4px 10px',
                borderRadius: 6,
                background: current.bgLight,
                color: current.color,
                fontSize: 12,
                fontWeight: 700,
                marginBottom: 14,
              }}
            >
              {current.badge}
            </div>
            <h2 style={{ fontSize: 26, fontWeight: 800, margin: '0 0 14px', lineHeight: 1.25 }}>
              {current.title}
            </h2>
            <p style={{ fontSize: 15, color: C.textSecondary, lineHeight: 1.6, margin: '0 0 24px' }}>
              {current.description}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 32 }}>
              {current.points.map((pt, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 13.5, color: C.text, lineHeight: 1.5 }}>
                  <CheckCircle2 size={18} color="#16a34a" style={{ flexShrink: 0, marginTop: 2 }} />
                  <span>{pt}</span>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 12 }}>
              <button
                onClick={() => onNavigate('login')}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '11px 22px',
                  borderRadius: 8,
                  background: C.primary,
                  color: '#fff',
                  border: 'none',
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Try It Live <ArrowRight size={15} />
              </button>
              <button
                onClick={onOpenDemo}
                style={{
                  padding: '11px 20px',
                  borderRadius: 8,
                  border: `1px solid ${C.border}`,
                  background: '#fff',
                  color: C.text,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Request Walkthrough
              </button>
            </div>
          </div>

          {/* Right Visual Snippet Frame */}
          <div
            style={{
              background: '#0F0F10',
              borderRadius: 16,
              padding: '24px',
              color: '#ffffff',
              boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
              border: '1px solid rgba(255,255,255,0.1)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: 12, marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: 6 }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#EF4444' }} />
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#F59E0B' }} />
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#10B981' }} />
              </div>
              <span style={{ fontSize: 11, fontFamily: MONO, color: '#A1A1AA' }}>synaptic-engine.v2</span>
            </div>

            <div style={{ fontFamily: MONO, fontSize: 13, lineHeight: 1.7, color: '#E4E4E7' }}>
              <div style={{ color: '#10B981', marginBottom: 8 }}>✓ Synaptic Engine Ready</div>
              <div style={{ color: '#93C5FD' }}>&gt; Module: {activeTab.toUpperCase()}</div>
              <div style={{ color: '#A1A1AA' }}>&gt; Status: {current.previewSnippet}</div>
              <div style={{ color: '#FCD34D', marginTop: 12 }}>&gt; Handshake: Meta WhatsApp Cloud API (v21.0)</div>
              <div style={{ color: '#E4E4E7' }}>&gt; Encryption: AES-256-GCM Session Tokens</div>
              <div style={{ color: '#34D399', marginTop: 12 }}>● All systems operational</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
