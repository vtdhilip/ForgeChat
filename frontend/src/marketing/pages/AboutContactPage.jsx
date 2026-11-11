import { useState } from 'react';
import {
  ShieldCheck, Lock, Server, Heart, Mail, MessageCircle, MapPin,
  Send, CheckCircle2, Sparkles, Building
} from 'lucide-react';
import { C, FONT } from '../../constants.js';

export default function AboutContactPage({ onNavigate }) {
  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    subject: 'General Inquiry',
    message: '',
  });
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleContactSubmit = (e) => {
    e.preventDefault();
    if (!form.name || !form.email || !form.message) {
      setError('Please fill in all required fields.');
      return;
    }
    setError('');
    setSent(true);
  };

  return (
    <div style={{ fontFamily: FONT, background: C.pageBg, color: C.text, paddingBottom: 80 }}>
      {/* Header */}
      <section style={{ padding: '60px 24px 36px', maxWidth: 900, margin: '0 auto', textAlign: 'center' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: '#FEE2E2', color: C.primary, padding: '5px 14px', borderRadius: 20, fontSize: 12, fontWeight: 700, marginBottom: 16 }}>
          <Sparkles size={14} /> Mission & Security
        </div>
        <h1 style={{ fontSize: 'clamp(32px, 4.5vw, 48px)', fontWeight: 800, letterSpacing: '-0.02em', margin: '0 0 16px' }}>
          Building the future of business communication on WhatsApp
        </h1>
        <p style={{ fontSize: 16, color: C.textSecondary, lineHeight: 1.6, maxWidth: 620, margin: '0 auto' }}>
          Developed by Synaptic Info, Synaptic Chat was founded with a singular purpose: to empower businesses to deliver lightning-fast, high-converting customer experiences using autonomous AI and human collaboration.
        </p>
      </section>

      {/* Security & Compliance Highlights */}
      <section style={{ maxWidth: 1100, margin: '0 auto 60px', padding: '0 24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20 }}>
          <div style={{ background: '#ffffff', borderRadius: 16, border: `1px solid ${C.border}`, padding: '28px 24px', boxShadow: C.shadowSm }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: '#F0FDF4', color: '#16a34a', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
              <ShieldCheck size={20} />
            </div>
            <h3 style={{ fontSize: 17, fontWeight: 700, margin: '0 0 8px' }}>Official Meta Cloud API</h3>
            <p style={{ fontSize: 13, color: C.textSecondary, lineHeight: 1.6, margin: 0 }}>
              Direct integration with Meta’s Graph API (v21.0). Zero reliance on risky unofficial WhatsApp web automation or device scraping.
            </p>
          </div>

          <div style={{ background: '#ffffff', borderRadius: 16, border: `1px solid ${C.border}`, padding: '28px 24px', boxShadow: C.shadowSm }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: '#EFF6FF', color: '#2563EB', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
              <Lock size={20} />
            </div>
            <h3 style={{ fontSize: 17, fontWeight: 700, margin: '0 0 8px' }}>Encrypted Credentials & Isolation</h3>
            <p style={{ fontSize: 13, color: C.textSecondary, lineHeight: 1.6, margin: 0 }}>
              All WhatsApp tokens and API secrets are encrypted at rest with AES-256-GCM. Multi-tenant database schemas ensure complete customer data isolation.
            </p>
          </div>

          <div style={{ background: '#ffffff', borderRadius: 16, border: `1px solid ${C.border}`, padding: '28px 24px', boxShadow: C.shadowSm }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: '#FAF5FF', color: '#9333EA', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
              <Server size={20} />
            </div>
            <h3 style={{ fontSize: 17, fontWeight: 700, margin: '0 0 8px' }}>Docker Self-Hostable</h3>
            <p style={{ fontSize: 13, color: C.textSecondary, lineHeight: 1.6, margin: 0 }}>
              Full sovereignty over your customer data. Deploy on your own AWS, GCP, Azure, or on-premise hardware with our production Docker compose harness.
            </p>
          </div>
        </div>
      </section>

      {/* Contact Form & Office Grid */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '0 24px' }}>
        <div
          style={{
            background: '#ffffff',
            borderRadius: 20,
            border: `1px solid ${C.border}`,
            padding: '40px',
            boxShadow: C.shadowSm,
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: 40,
          }}
        >
          {/* Left Info Column */}
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 800, margin: '0 0 12px' }}>
              Get in Touch with our Team
            </h2>
            <p style={{ fontSize: 14, color: C.textSecondary, lineHeight: 1.6, margin: '0 0 28px' }}>
              Have questions regarding custom enterprise plans, multi-tenant white labeling, or data residency? Our solutions engineering team is here to assist.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 14 }}>
                <div style={{ width: 36, height: 36, borderRadius: 8, background: '#f8fafc', border: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.primary }}>
                  <Mail size={16} />
                </div>
                <div>
                  <div style={{ fontSize: 12, color: C.textMuted }}>Direct Inquiries</div>
                  <strong style={{ color: C.text }}>support@synapticchat.com</strong>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 14 }}>
                <div style={{ width: 36, height: 36, borderRadius: 8, background: '#f8fafc', border: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#16a34a' }}>
                  <MessageCircle size={16} />
                </div>
                <div>
                  <div style={{ fontSize: 12, color: C.textMuted }}>WhatsApp Sales Channel</div>
                  <strong style={{ color: C.text }}>+1 (555) 019-2834</strong>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 14 }}>
                <div style={{ width: 36, height: 36, borderRadius: 8, background: '#f8fafc', border: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#534AB7' }}>
                  <Building size={16} />
                </div>
                <div>
                  <div style={{ fontSize: 12, color: C.textMuted }}>Company & Headquarters</div>
                  <strong style={{ color: C.text, display: 'block', fontSize: 13.5 }}>Synaptic Info</strong>
                  <span style={{ color: C.textSecondary, fontSize: 13 }}>Enterprise Tech Park, California & Bengaluru</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Contact Form */}
          <div>
            {sent ? (
              <div style={{ padding: '36px 20px', textAlign: 'center', background: '#F0FDF4', borderRadius: 12, border: '1px solid #BBF7D0' }}>
                <CheckCircle2 size={36} color="#16a34a" style={{ margin: '0 auto 12px' }} />
                <h4 style={{ fontSize: 18, fontWeight: 700, color: '#15803d', margin: '0 0 6px' }}>
                  Message Sent Successfully!
                </h4>
                <p style={{ fontSize: 13, color: '#166534', margin: 0 }}>
                  Thank you for reaching out. A solutions architect will reply to your inquiry shortly.
                </p>
              </div>
            ) : (
              <form onSubmit={handleContactSubmit}>
                {error && (
                  <div style={{ background: C.primaryLight, color: '#A32D2D', padding: '10px 12px', borderRadius: 8, fontSize: 13, marginBottom: 14 }}>
                    {error}
                  </div>
                )}

                <div style={{ marginBottom: 14 }}>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 5 }}>
                    Your Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Full Name"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    style={{ width: '100%', padding: '9px 12px', borderRadius: 8, border: `1px solid ${C.borderDark}`, fontSize: 13, outline: 'none' }}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 5 }}>
                      Work Email *
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="you@company.com"
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: 8, border: `1px solid ${C.borderDark}`, fontSize: 13, outline: 'none' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 5 }}>
                      Phone / WhatsApp
                    </label>
                    <input
                      type="tel"
                      placeholder="+1 (555) 000-0000"
                      value={form.phone}
                      onChange={(e) => setForm({ ...form, phone: e.target.value })}
                      style={{ width: '100%', padding: '9px 12px', borderRadius: 8, border: `1px solid ${C.borderDark}`, fontSize: 13, outline: 'none' }}
                    />
                  </div>
                </div>

                <div style={{ marginBottom: 14 }}>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 5 }}>
                    Inquiry Subject
                  </label>
                  <select
                    value={form.subject}
                    onChange={(e) => setForm({ ...form, subject: e.target.value })}
                    style={{ width: '100%', padding: '9px 12px', borderRadius: 8, border: `1px solid ${C.borderDark}`, fontSize: 13, background: '#fff' }}
                  >
                    <option value="General Inquiry">General Product Inquiry</option>
                    <option value="Enterprise SLA">Enterprise SLAs & Custom Quotas</option>
                    <option value="White Label Agency">White-Label Agency Reselling</option>
                    <option value="Data Residency">Data Residency & On-Premise Docker</option>
                  </select>
                </div>

                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 5 }}>
                    Message *
                  </label>
                  <textarea
                    rows={4}
                    required
                    placeholder="Tell us about your team size, expected WhatsApp conversation volume, and requirements..."
                    value={form.message}
                    onChange={(e) => setForm({ ...form, message: e.target.value })}
                    style={{ width: '100%', padding: '9px 12px', borderRadius: 8, border: `1px solid ${C.borderDark}`, fontSize: 13, outline: 'none', resize: 'vertical' }}
                  />
                </div>

                <button
                  type="submit"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    width: '100%',
                    padding: '11px',
                    borderRadius: 8,
                    border: 'none',
                    background: C.primary,
                    color: '#fff',
                    fontSize: 14,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <Send size={15} /> Submit Message
                </button>
              </form>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
