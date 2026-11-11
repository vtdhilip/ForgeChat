import { useState } from 'react';
import {
  Check, X, Sparkles, HelpCircle, ChevronDown, ChevronUp,
  ShieldCheck, ArrowRight, Zap
} from 'lucide-react';
import { C, FONT, MONO } from '../../constants.js';
import PricingCalculator from '../components/PricingCalculator.jsx';

export default function PricingPage({ onNavigate, onOpenDemo }) {
  const [billingCycle, setBillingCycle] = useState('monthly'); // 'monthly' | 'annual'
  const [openFaq, setOpenFaq] = useState(null);

  const plans = [
    {
      id: 'starter',
      name: 'Starter Community',
      badge: 'Solo & Small Teams',
      monthlyPrice: 2499,
      annualPrice: 1999,
      description: 'Essential shared WhatsApp inbox and core contact management for boutique teams.',
      features: [
        '1 Connected WhatsApp Business Number',
        'Up to 3 Team Member Seats',
        'Shared Team Inbox & Canned Replies',
        'Contacts & CRM with Custom Fields',
        'Standard Flow Automations',
        '1,000 Free Marketing Broadcasts / mo',
        'Community Forum Support',
      ],
      cta: 'Start 14-Day Free Trial',
      popular: false,
    },
    {
      id: 'pro',
      name: 'Professional Growth',
      badge: 'Most Popular Choice',
      monthlyPrice: 6499,
      annualPrice: 5199,
      description: 'Empower your sales & support teams with autonomous AI agents, deal pipelines, and advanced automations.',
      features: [
        'Up to 5 Connected WhatsApp Phone Numbers',
        'Up to 15 Team Member Seats',
        'Autonomous AI Agents (BYOK OpenAI & Anthropic)',
        'Native Tool Calling & Google Sheets Sync',
        'Visual Deals & Sales CRM Kanban Board',
        'Official Meta Template Builder & Variables',
        '25,000 Monthly Marketing Broadcasts',
        'Priority Chat & WhatsApp Support',
      ],
      cta: 'Get Started with Pro',
      popular: true,
    },
    {
      id: 'enterprise',
      name: 'Enterprise Scale',
      badge: 'Agencies & Enterprises',
      monthlyPrice: 16999,
      annualPrice: 13599,
      description: 'Full multi-tenant client isolation with Super Admin feature switchboards, dedicated instances, and custom quotas.',
      features: [
        'Unlimited WhatsApp Phone Numbers',
        'Unlimited Team Seats across Multi-Tenant Orgs',
        'Super Admin Feature Switchboard & Quotas',
        'Self-Hosted Docker or Dedicated Cloud Host',
        'Custom Fine-Tuned AI Models & Tools',
        'Dedicated Solutions Architect & SLA (99.9%)',
        'Custom Data Residency & Migration Support',
        'Custom Webhooks & External API Integrations',
      ],
      cta: 'Request Enterprise Demo',
      popular: false,
    },
  ];

  const faqs = [
    {
      q: 'Do I need an official WhatsApp Business API account to use Synaptic Chat?',
      a: 'Yes. Synaptic Chat integrates directly with Meta’s official WhatsApp Cloud API. This means zero third-party markups on messages, high message delivery rates, verified sender badge support, and no risk of account bans associated with unofficial web scrapers.',
    },
    {
      q: 'Can multiple customer service agents use the same phone number at the same time?',
      a: 'Absolutely! That is one of Synaptic Chat’s core superpowers. Multiple team members can log into the shared inbox simultaneously from their own devices and reply to incoming chats without collision.',
    },
    {
      q: 'How does Bring Your Own Key (BYOK) work for AI Agents?',
      a: 'You can provide your own OpenAI, Anthropic, or DeepSeek API keys in the settings. This ensures your conversation data never trains public models, and you only pay raw provider API rates without artificial markups.',
    },
    {
      q: 'Can we self-host Synaptic Chat on our own servers or cloud?',
      a: 'Yes. Synaptic Chat is built Docker-first. You can deploy the complete platform (Postgres, Redis, Python FastAPI backend, and Nginx frontend) with a single `docker compose up -d` command on any server or cloud VM.',
    },
    {
      q: 'Can I switch plans or cancel at any time?',
      a: 'Yes, all plans come with a 14-day free trial. You can upgrade, downgrade, or cancel your subscription at any time without long-term lock-in.',
    },
  ];

  const handleSelectPlan = (planKey) => {
    if (planKey === 'enterprise') {
      onOpenDemo();
    } else {
      onNavigate('login');
    }
  };

  return (
    <div style={{ fontFamily: FONT, background: C.pageBg, color: C.text, paddingBottom: 80 }}>
      {/* Header */}
      <section style={{ padding: '60px 24px 36px', maxWidth: 900, margin: '0 auto', textAlign: 'center' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: '#FEE2E2', color: C.primary, padding: '5px 14px', borderRadius: 20, fontSize: 12, fontWeight: 700, marginBottom: 16 }}>
          <Sparkles size={14} /> Transparent & Flexible Plans
        </div>
        <h1 style={{ fontSize: 'clamp(32px, 4.5vw, 48px)', fontWeight: 800, letterSpacing: '-0.02em', margin: '0 0 16px' }}>
          Simple pricing designed to scale with your conversation volume
        </h1>
        <p style={{ fontSize: 16, color: C.textSecondary, lineHeight: 1.6, maxWidth: 580, margin: '0 auto 28px' }}>
          Start with a 14-day free trial on any plan. Upgrade as your team and customer conversations grow.
        </p>

        {/* Billing Cycle Toggle */}
        <div style={{ display: 'inline-flex', alignItems: 'center', background: '#ffffff', padding: 4, borderRadius: 10, border: `1px solid ${C.border}`, gap: 4 }}>
          <button
            onClick={() => setBillingCycle('monthly')}
            style={{
              padding: '6px 16px',
              borderRadius: 8,
              border: 'none',
              background: billingCycle === 'monthly' ? C.primary : 'transparent',
              color: billingCycle === 'monthly' ? '#fff' : C.textSecondary,
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Monthly Billing
          </button>
          <button
            onClick={() => setBillingCycle('annual')}
            style={{
              padding: '6px 16px',
              borderRadius: 8,
              border: 'none',
              background: billingCycle === 'annual' ? C.primary : 'transparent',
              color: billingCycle === 'annual' ? '#fff' : C.textSecondary,
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            Annual Billing <span style={{ fontSize: 11, background: '#FEE2E2', color: C.primary, padding: '2px 6px', borderRadius: 6, fontWeight: 700 }}>Save 20%</span>
          </button>
        </div>
      </section>

      {/* Pricing Cards Grid */}
      <section style={{ maxWidth: 1200, margin: '0 auto 60px', padding: '0 24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24, alignItems: 'stretch' }}>
          {plans.map((p) => {
            const price = billingCycle === 'annual' ? p.annualPrice : p.monthlyPrice;
            return (
              <div
                key={p.id}
                style={{
                  background: '#ffffff',
                  borderRadius: 20,
                  border: p.popular ? `2px solid ${C.primary}` : `1px solid ${C.border}`,
                  padding: '36px 30px',
                  boxShadow: p.popular ? '0 16px 40px rgba(220, 38, 38, 0.12)' : C.shadowSm,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  position: 'relative',
                }}
              >
                {p.popular && (
                  <div
                    style={{
                      position: 'absolute',
                      top: -14,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      background: C.primary,
                      color: '#ffffff',
                      padding: '4px 14px',
                      borderRadius: 14,
                      fontSize: 11.5,
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                    }}
                  >
                    {p.badge}
                  </div>
                )}

                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: p.popular ? C.primary : C.textSecondary, textTransform: 'uppercase', marginBottom: 6 }}>
                    {p.badge}
                  </div>
                  <h3 style={{ fontSize: 22, fontWeight: 800, margin: '0 0 10px', color: C.text }}>
                    {p.name}
                  </h3>
                  <p style={{ fontSize: 13, color: C.textSecondary, lineHeight: 1.5, margin: '0 0 20px', minHeight: 40 }}>
                    {p.description}
                  </p>

                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 24, borderBottom: `1px solid ${C.border}`, paddingBottom: 20 }}>
                    <span style={{ fontSize: 40, fontWeight: 800, color: C.text, fontFamily: MONO }}>
                      ₹{price.toLocaleString('en-IN')}
                    </span>
                    <span style={{ fontSize: 14, color: C.textSecondary }}>/ month (INR)</span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 32 }}>
                    {p.features.map((feat, fi) => (
                      <div key={fi} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 13, color: C.text, lineHeight: 1.45 }}>
                        <Check size={16} color={p.popular ? C.primary : '#16a34a'} style={{ flexShrink: 0, marginTop: 2 }} />
                        <span>{feat}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <button
                  onClick={() => handleSelectPlan(p.id)}
                  style={{
                    width: '100%',
                    padding: '12px',
                    borderRadius: 10,
                    border: 'none',
                    background: p.popular ? C.primary : '#0F0F10',
                    color: '#ffffff',
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: 'pointer',
                    boxShadow: p.popular ? '0 6px 18px rgba(220, 38, 38, 0.3)' : 'none',
                  }}
                >
                  {p.cta}
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* Embedded ROI Calculator */}
      <section style={{ maxWidth: 1100, margin: '0 auto 70px', padding: '0 24px' }}>
        <PricingCalculator onSelectPlan={handleSelectPlan} />
      </section>

      {/* FAQ Accordion */}
      <section style={{ maxWidth: 840, margin: '0 auto', padding: '0 24px' }}>
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <h2 style={{ fontSize: 28, fontWeight: 800, margin: '0 0 10px' }}>
            Frequently Asked Questions
          </h2>
          <p style={{ fontSize: 14, color: C.textSecondary, margin: 0 }}>
            Everything you need to know about billing, Meta API compliance, and onboarding.
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {faqs.map((faq, idx) => {
            const isOpen = openFaq === idx;
            return (
              <div
                key={idx}
                style={{
                  background: '#ffffff',
                  borderRadius: 12,
                  border: `1px solid ${C.border}`,
                  overflow: 'hidden',
                }}
              >
                <button
                  type="button"
                  aria-expanded={isOpen}
                  onClick={() => setOpenFaq(isOpen ? null : idx)}
                  style={{
                    width: '100%',
                    padding: '18px 20px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    userSelect: 'none',
                    background: 'transparent',
                    border: 'none',
                    textAlign: 'left',
                    fontFamily: 'inherit',
                  }}
                >
                  <span style={{ fontSize: 15, fontWeight: 700, color: C.text }}>
                    {faq.q}
                  </span>
                  {isOpen ? <ChevronUp size={18} color={C.textMuted} /> : <ChevronDown size={18} color={C.textMuted} />}
                </button>
                {isOpen && (
                  <div
                    style={{
                      padding: '0 20px 18px',
                      fontSize: 13.5,
                      color: C.textSecondary,
                      lineHeight: 1.6,
                      borderTop: `1px solid ${C.border}`,
                      paddingTop: 14,
                    }}
                  >
                    {faq.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
