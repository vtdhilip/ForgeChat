import { useState, useEffect } from 'react';
import { X, CheckCircle2, Calendar, Sparkles } from 'lucide-react';
import { C, FONT } from '../../constants.js';

export default function DemoBookingModal({ isOpen, onClose }) {
  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    company: '',
    teamSize: '5-20',
    interest: 'AI Autonomous Agents & WhatsApp CRM',
    notes: '',
  });
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  // Close on Escape key press
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.phone.trim()) {
      setError('Please provide your name, email, and WhatsApp phone number.');
      return;
    }
    if (!form.email.includes('@') || !form.email.includes('.')) {
      setError('Please enter a valid work email address.');
      return;
    }

    setError('');
    setSubmitted(true);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="demo-modal-title"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(15, 15, 16, 0.7)',
        backdropFilter: 'blur(6px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
        fontFamily: FONT,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#ffffff',
          borderRadius: 16,
          width: '100%',
          maxWidth: 540,
          maxHeight: '90vh',
          overflowY: 'auto',
          boxShadow: '0 24px 60px rgba(0, 0, 0, 0.2)',
          border: `1px solid ${C.border}`,
          position: 'relative',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: `1px solid ${C.border}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: C.primaryLight,
                color: C.primary,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Calendar size={18} />
            </div>
            <div>
              <h3 id="demo-modal-title" style={{ margin: 0, fontSize: 18, fontWeight: 700, color: C.text }}>
                Schedule a 1-on-1 Product Demo
              </h3>
              <p style={{ margin: 0, fontSize: 12.5, color: C.textSecondary }}>
                See how Synaptic Chat automates customer operations on WhatsApp
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            style={{
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              color: C.textMuted,
              display: 'flex',
              padding: 4,
            }}
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        {submitted ? (
          <div style={{ padding: '40px 24px', textAlign: 'center' }}>
            <div
              style={{
                width: 60,
                height: 60,
                borderRadius: '50%',
                background: '#E8F5E9',
                color: '#2E7D32',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
              }}
            >
              <CheckCircle2 size={32} />
            </div>
            <h4 style={{ fontSize: 20, fontWeight: 700, color: C.text, margin: '0 0 8px' }}>
              Demo Request Received!
            </h4>
            <p style={{ fontSize: 14, color: C.textSecondary, lineHeight: 1.5, margin: '0 0 24px' }}>
              Thank you, <strong>{form.name}</strong>. Our enterprise solutions specialist will reach out on WhatsApp at <strong>{form.phone}</strong> and via email within 2 business hours.
            </p>
            <button
              onClick={() => {
                setSubmitted(false);
                onClose();
              }}
              style={{
                padding: '10px 24px',
                borderRadius: 8,
                background: C.primary,
                color: '#fff',
                border: 'none',
                fontSize: 14,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Close Window
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ padding: '22px 24px' }}>
            {error && (
              <div
                style={{
                  background: C.primaryLight,
                  color: '#A32D2D',
                  padding: '10px 14px',
                  borderRadius: 8,
                  fontSize: 13,
                  marginBottom: 16,
                }}
              >
                {error}
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Alex Johnson"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: 8,
                    border: `1px solid ${C.borderDark}`,
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>
                  Work Email *
                </label>
                <input
                  type="email"
                  required
                  placeholder="alex@company.com"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: 8,
                    border: `1px solid ${C.borderDark}`,
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>
                  WhatsApp Number *
                </label>
                <input
                  type="tel"
                  required
                  placeholder="+1 (555) 000-0000"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: 8,
                    border: `1px solid ${C.borderDark}`,
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>
                  Company Name
                </label>
                <input
                  type="text"
                  placeholder="Acme Corp"
                  value={form.company}
                  onChange={(e) => setForm({ ...form, company: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: 8,
                    border: `1px solid ${C.borderDark}`,
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>
                  Team Size
                </label>
                <select
                  value={form.teamSize}
                  onChange={(e) => setForm({ ...form, teamSize: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: 8,
                    border: `1px solid ${C.borderDark}`,
                    fontSize: 13,
                    background: '#fff',
                  }}
                >
                  <option value="1-5">1-5 members</option>
                  <option value="5-20">5-20 members</option>
                  <option value="20-100">20-100 members</option>
                  <option value="100+">100+ Enterprise</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>
                  Primary Interest
                </label>
                <select
                  value={form.interest}
                  onChange={(e) => setForm({ ...form, interest: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: 8,
                    border: `1px solid ${C.borderDark}`,
                    fontSize: 13,
                    background: '#fff',
                  }}
                >
                  <option value="AI Autonomous Agents & WhatsApp CRM">AI Autonomous Agents</option>
                  <option value="Shared Team Inbox & Multi-Agent">Shared Team Inbox</option>
                  <option value="Bulk Broadcasts & Templates">Bulk Broadcasts & Templates</option>
                  <option value="Sales Pipelines & CRM Sync">Sales Deals & CRM Sync</option>
                  <option value="Enterprise White-Label Multi-Tenant">Enterprise Multi-Tenant</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>
                How can we help your business? (Optional)
              </label>
              <textarea
                rows={3}
                placeholder="Tell us about your current customer support or sales volume on WhatsApp..."
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: 8,
                  border: `1px solid ${C.borderDark}`,
                  fontSize: 13,
                  outline: 'none',
                  resize: 'vertical',
                }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10 }}>
              <button
                type="button"
                onClick={onClose}
                style={{
                  padding: '9px 16px',
                  borderRadius: 8,
                  border: `1px solid ${C.border}`,
                  background: '#fff',
                  color: C.text,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '9px 20px',
                  borderRadius: 8,
                  border: 'none',
                  background: C.primary,
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <Sparkles size={15} /> Request Personalized Demo
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
