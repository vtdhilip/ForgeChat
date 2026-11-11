import {
  ShoppingBag, Stethoscope, Building2, GraduationCap, TrendingUp,
  Layers, ArrowRight, CheckCircle2, Sparkles, Clock, MessageSquare
} from 'lucide-react';
import { C, FONT, MONO } from '../../constants.js';

export default function SolutionsPage({ onNavigate, onOpenDemo }) {
  const industries = [
    {
      title: 'E-Commerce & D2C Brands',
      icon: ShoppingBag,
      tag: 'Order Velocity & Retention',
      color: '#EA580C',
      bgLight: '#FFF7ED',
      description: 'Turn WhatsApp into your primary revenue driver with automated abandoned cart recovery, shipment notifications, and instant catalog queries.',
      outcomes: ['+34% Abandoned Cart Recovery Rate', '80% Reduction in WISMO ("Where is my order") tickets', 'Instant Razorpay & Shopify payment links in chat'],
      workflow: 'Customer drops cart → WhatsApp template sent at 30 mins with 1-click discount button → AI Agent answers product sizing questions → Order completed.',
    },
    {
      title: 'Healthcare, Dental & Clinics',
      icon: Stethoscope,
      tag: 'Patient Booking & Care',
      color: '#0284C7',
      bgLight: '#F0F9FF',
      description: 'Automate doctor appointment scheduling, reduce clinic no-shows, and deliver prescription reminders with HIPAA/data-conscious isolation.',
      outcomes: ['-52% Appointment No-Shows via WhatsApp Reminders', 'Automated symptom intake triage', 'Secure direct doctor-patient messaging handoff'],
      workflow: 'Patient texts clinic number → Automated bot offers available doctor slots → Appointment confirmed on Google Calendar → WhatsApp reminder sent 2 hours before.',
    },
    {
      title: 'Real Estate & Property Developers',
      icon: Building2,
      tag: 'High-Ticket Lead Qualification',
      color: '#16A34A',
      bgLight: '#F0FDF4',
      description: 'Capture high-intent property inquiries from Meta & Google Ads. Qualify buyers by budget and location before booking in-person site visits.',
      outcomes: ['3x Increase in scheduled site visits', 'Instant property brochure PDFs delivered via WhatsApp', 'Kanban deal pipelines synced with property sales teams'],
      workflow: 'Buyer clicks WhatsApp Ad → AI Agent inquires budget & preferred BHK → Brochure PDF sent → Qualified deal card created on Kanban → Sales rep assigned.',
    },
    {
      title: 'Education, EdTech & Universities',
      icon: GraduationCap,
      tag: 'Admissions & Student Success',
      color: '#9333EA',
      bgLight: '#FAF5FF',
      description: 'Engage prospective students on their favorite communication channel. Automate course syllabus delivery, counseling sessions, and fee deadlines.',
      outcomes: ['45% Faster application completion rate', '24/7 Course FAQ and curriculum advisor agent', 'Automated fee reminder broadcasts with high open rates'],
      workflow: 'Student requests syllabus → Bot delivers PDF curriculum → Asks if they want academic counseling → Books 1-on-1 Zoom call directly in chat.',
    },
    {
      title: 'B2B & High-Velocity Sales Teams',
      icon: TrendingUp,
      tag: 'Pipeline Acceleration',
      color: C.primary,
      bgLight: '#FCEBEB',
      description: 'Accelerate the sales cycle from weeks to hours. Engage inbound decision-makers immediately when buying intent is peak.',
      outcomes: ['<60-second response time to inbound inbound leads', 'Direct two-way sync with Google Sheets & CRM', 'Multi-rep shared inbox with collision prevention'],
      workflow: 'Lead submits contact form → Synaptic Chat immediately initiates WhatsApp outreach → AI qualifies company size → Transfers to live rep with deal history.',
    },
    {
      title: 'Digital Marketing Agencies & Resellers',
      icon: Layers,
      tag: 'Multi-Tenant Client Management',
      color: '#0F172A',
      bgLight: '#F8FAFC',
      description: 'Manage dozens of distinct client accounts from a single deployment. Toggle feature access per client with the Super Admin Switchboard.',
      outcomes: ['Zero cross-client data leakage via coexistence schema', 'Granular quota caps (seats, AI tokens, WhatsApp lines)', 'High-margin client retainer revenue model'],
      workflow: 'Agency provisions new client organization in 30 seconds → Selects allowed modules in Switchboard → Client team logs in with dedicated workspace access.',
    },
  ];

  return (
    <div style={{ fontFamily: FONT, background: C.pageBg, color: C.text, paddingBottom: 80 }}>
      {/* Header */}
      <section style={{ padding: '60px 24px 44px', maxWidth: 1000, margin: '0 auto', textAlign: 'center' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: '#FEE2E2', color: C.primary, padding: '5px 14px', borderRadius: 20, fontSize: 12, fontWeight: 700, marginBottom: 16 }}>
          <Sparkles size={14} /> Industry Solutions
        </div>
        <h1 style={{ fontSize: 'clamp(32px, 4.5vw, 48px)', fontWeight: 800, letterSpacing: '-0.02em', margin: '0 0 16px' }}>
          Proven WhatsApp workflows for every business vertical
        </h1>
        <p style={{ fontSize: 16, color: C.textSecondary, lineHeight: 1.6, maxWidth: 640, margin: '0 auto' }}>
          Discover how organizations across retail, healthcare, real estate, and B2B sales leverage Synaptic Chat to drive measurable revenue and streamline operations.
        </p>
      </section>

      {/* Grid of Solutions */}
      <section style={{ maxWidth: 1200, margin: '0 auto', padding: '0 24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 24 }}>
          {industries.map((ind, i) => {
            const Icon = ind.icon;
            return (
              <div
                key={i}
                style={{
                  background: '#ffffff',
                  borderRadius: 18,
                  border: `1px solid ${C.border}`,
                  padding: '32px 28px',
                  boxShadow: C.shadowSm,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                    <div
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: 12,
                        background: ind.bgLight,
                        color: ind.color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Icon size={22} />
                    </div>
                    <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 8px', borderRadius: 6, background: '#f8fafc', color: C.textSecondary, border: `1px solid ${C.border}` }}>
                      {ind.tag}
                    </span>
                  </div>

                  <h3 style={{ fontSize: 20, fontWeight: 700, margin: '0 0 10px', color: C.text }}>
                    {ind.title}
                  </h3>

                  <p style={{ fontSize: 13.5, color: C.textSecondary, lineHeight: 1.6, margin: '0 0 20px' }}>
                    {ind.description}
                  </p>

                  <div style={{ marginBottom: 20 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: C.text, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 8 }}>
                      Key Measurable Outcomes:
                    </div>
                    {ind.outcomes.map((out, oi) => (
                      <div key={oi} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#15803d', fontWeight: 600, marginBottom: 5 }}>
                        <CheckCircle2 size={15} color="#16a34a" /> {out}
                      </div>
                    ))}
                  </div>

                  <div style={{ background: '#f8fafc', padding: '12px 14px', borderRadius: 10, border: `1px solid ${C.border}`, marginBottom: 24 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: C.textSecondary, textTransform: 'uppercase', marginBottom: 4 }}>
                      Example Automation Flow:
                    </div>
                    <div style={{ fontSize: 12.5, color: C.text, lineHeight: 1.5 }}>
                      {ind.workflow}
                    </div>
                  </div>
                </div>

                <button
                  onClick={onOpenDemo}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    width: '100%',
                    padding: '11px',
                    borderRadius: 8,
                    border: `1px solid ${C.borderDark}`,
                    background: '#ffffff',
                    color: C.text,
                    fontSize: 13.5,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Schedule Solution Walkthrough <ArrowRight size={14} />
                </button>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
