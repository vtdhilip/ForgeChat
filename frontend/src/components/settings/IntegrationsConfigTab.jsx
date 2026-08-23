import { useState, useEffect } from 'react';
import {
  CreditCard, Truck, FileSpreadsheet, Bot, Key, Check,
  AlertTriangle, Loader2, Save, Eye, EyeOff, ExternalLink, RefreshCw, Zap
} from 'lucide-react';
import { api } from '../../api.js';
import { C, FONT, MONO } from '../../constants.js';

export default function IntegrationsConfigTab({ activeOrgId }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingType, setTestingType] = useState(null);
  const [testResult, setTestResult] = useState({});
  const [showSecrets, setShowSecrets] = useState({});
  const [savedMsg, setSavedMsg] = useState(false);

  const [form, setForm] = useState({
    razorpay_key_id: '',
    razorpay_key_secret: '',
    shiprocket_email: '',
    shiprocket_password: '',
    shiprocket_token: '',
    shiprocket_pickup_location: 'warehouse',
    google_sheet_webhook_url: '',
    whatsapp_flow_id: '',
    openai_api_key: '',
    anthropic_api_key: '',
    order_prefix: 'LN-',
    shipping_fee: 60,
  });

  const loadSettings = async () => {
    setLoading(true);
    try {
      // First get current org if not provided
      let orgId = activeOrgId;
      if (!orgId) {
        const { organizations, activeOrgId: currentId } = await api.organizations.list();
        orgId = currentId || (organizations[0] && organizations[0].id);
      }
      if (orgId) {
        const { integrations } = await api.organizations.getIntegrations(orgId);
        if (integrations) {
          setForm(prev => ({ ...prev, ...integrations }));
        }
      }
    } catch (err) {
      console.error('Failed to load integrations:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, [activeOrgId]);

  const toggleSecret = (field) => {
    setShowSecrets(p => ({ ...p, [field]: !p[field] }));
  };

  const handleChange = (field, val) => {
    setForm(p => ({ ...p, [field]: val }));
    setSavedMsg(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setSavedMsg(false);
    try {
      const { organizations, activeOrgId: currentId } = await api.organizations.list();
      const orgId = activeOrgId || currentId || (organizations[0] && organizations[0].id);
      if (!orgId) throw new Error('No active organization found');

      await api.organizations.updateIntegrations(orgId, form);
      setSavedMsg(true);
      setTimeout(() => setSavedMsg(false), 4000);
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (type) => {
    setTestingType(type);
    setTestResult(p => ({ ...p, [type]: null }));
    try {
      const { organizations, activeOrgId: currentId } = await api.organizations.list();
      const orgId = activeOrgId || currentId || (organizations[0] && organizations[0].id);
      const res = await api.organizations.testIntegration(orgId, type, form);
      setTestResult(p => ({ ...p, [type]: { success: true, message: res.message || 'Connected successfully!' } }));
    } catch (err) {
      setTestResult(p => ({ ...p, [type]: { success: false, message: err.message || 'Connection test failed' } }));
    } finally {
      setTestingType(null);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 40, display: 'flex', alignItems: 'center', gap: 10, color: C.textMuted, fontFamily: FONT }}>
        <Loader2 size={18} className="animate-spin" /> Loading environment & integration settings…
      </div>
    );
  }

  return (
    <div style={{ flex: 1, padding: '32px 40px 60px', overflowY: 'auto', fontFamily: FONT, background: '#F8F9FB' }}>
      <div style={{ maxWidth: 880, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, color: '#111827', margin: 0, letterSpacing: '-0.02em' }}>
              Environment & Integrations
            </h1>
            <p style={{ fontSize: 13, color: '#6B7280', margin: '4px 0 0' }}>
              Configure live API credentials for Razorpay, Shiprocket, Meta Flows, Google Sheets, and AI models directly on the web.
            </p>
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              background: '#FF5A00',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: 10,
              padding: '10px 20px',
              fontSize: 13.5,
              fontWeight: 700,
              cursor: saving ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 14px rgba(255, 90, 0, 0.25)',
              fontFamily: FONT,
            }}
          >
            {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
            <span>{saving ? 'Saving…' : 'Save Changes'}</span>
          </button>
        </div>

        {savedMsg && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, background: '#FFF0E6',
            border: '1px solid #FFCCA8', color: '#FF5A00', padding: '12px 16px',
            borderRadius: 12, fontSize: 13, fontWeight: 600, marginBottom: 20,
          }}>
            <Check size={16} strokeWidth={2.5} />
            <span>Settings saved successfully! Updated credentials take effect immediately without restarting the server.</span>
          </div>
        )}

        {/* ── 1. Razorpay Payment Gateway ────────────────────────── */}
        <div style={{ background: '#FFFFFF', border: '1px solid #ECEEF1', borderRadius: 16, padding: 24, marginBottom: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: '#FFF7ED', color: '#EA580C', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <CreditCard size={20} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#111827' }}>Razorpay Payments</h3>
                <p style={{ margin: 0, fontSize: 12, color: '#6B7280' }}>Powers automated payment links in WhatsApp chat & checkout</p>
              </div>
            </div>
            <button
              onClick={() => handleTest('razorpay')}
              disabled={testingType === 'razorpay'}
              style={{
                display: 'flex', alignItems: 'center', gap: 6, border: '1px solid #E5E7EB',
                background: '#F9FAFB', borderRadius: 8, padding: '6px 12px', fontSize: 12,
                fontWeight: 600, color: '#374151', cursor: 'pointer', fontFamily: FONT,
              }}
            >
              {testingType === 'razorpay' ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
              <span>Test Connection</span>
            </button>
          </div>

          {testResult.razorpay && (
            <div style={{
              padding: '8px 12px', borderRadius: 8, fontSize: 12, fontWeight: 600, marginBottom: 14,
              background: testResult.razorpay.success ? '#FFF0E6' : '#FEF2F2',
              color: testResult.razorpay.success ? '#FF5A00' : '#DC2626',
            }}>
              {testResult.razorpay.message}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                Razorpay Key ID
              </label>
              <input
                type="text"
                value={form.razorpay_key_id}
                onChange={e => handleChange('razorpay_key_id', e.target.value)}
                placeholder="rzp_live_..."
                style={{
                  width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #D1D5DB',
                  fontSize: 13, fontFamily: MONO, color: '#111827', boxSizing: 'border-box', outline: 'none',
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                Razorpay Key Secret
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showSecrets.razorpay_key_secret ? 'text' : 'password'}
                  value={form.razorpay_key_secret}
                  onChange={e => handleChange('razorpay_key_secret', e.target.value)}
                  placeholder="••••••••••••••••"
                  style={{
                    width: '100%', padding: '9px 36px 9px 12px', borderRadius: 8, border: '1px solid #D1D5DB',
                    fontSize: 13, fontFamily: MONO, color: '#111827', boxSizing: 'border-box', outline: 'none',
                  }}
                />
                <button
                  type="button"
                  onClick={() => toggleSecret('razorpay_key_secret')}
                  style={{
                    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: '#9CA3AF',
                  }}
                >
                  {showSecrets.razorpay_key_secret ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ── 2. Shiprocket Logistics & Fulfillment ───────────────── */}
        <div style={{ background: '#FFFFFF', border: '1px solid #ECEEF1', borderRadius: 16, padding: 24, marginBottom: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: '#EFF6FF', color: '#2563EB', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Truck size={20} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#111827' }}>Shiprocket Logistics</h3>
                <p style={{ margin: 0, fontSize: 12, color: '#6B7280' }}>Auto-generates shipments, courier pickups & AWB tracking</p>
              </div>
            </div>
            <button
              onClick={() => handleTest('shiprocket')}
              disabled={testingType === 'shiprocket'}
              style={{
                display: 'flex', alignItems: 'center', gap: 6, border: '1px solid #E5E7EB',
                background: '#F9FAFB', borderRadius: 8, padding: '6px 12px', fontSize: 12,
                fontWeight: 600, color: '#374151', cursor: 'pointer', fontFamily: FONT,
              }}
            >
              {testingType === 'shiprocket' ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
              <span>Test Connection</span>
            </button>
          </div>

          {testResult.shiprocket && (
            <div style={{
              padding: '8px 12px', borderRadius: 8, fontSize: 12, fontWeight: 600, marginBottom: 14,
              background: testResult.shiprocket.success ? '#FFF0E6' : '#FEF2F2',
              color: testResult.shiprocket.success ? '#FF5A00' : '#DC2626',
            }}>
              {testResult.shiprocket.message}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 14 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                Shiprocket Email
              </label>
              <input
                type="email"
                value={form.shiprocket_email}
                onChange={e => handleChange('shiprocket_email', e.target.value)}
                placeholder="account@brand.com"
                style={{
                  width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #D1D5DB',
                  fontSize: 13, color: '#111827', boxSizing: 'border-box', outline: 'none',
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                Shiprocket Password
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showSecrets.shiprocket_password ? 'text' : 'password'}
                  value={form.shiprocket_password}
                  onChange={e => handleChange('shiprocket_password', e.target.value)}
                  placeholder="••••••••••••••••"
                  style={{
                    width: '100%', padding: '9px 36px 9px 12px', borderRadius: 8, border: '1px solid #D1D5DB',
                    fontSize: 13, color: '#111827', boxSizing: 'border-box', outline: 'none',
                  }}
                />
                <button
                  type="button"
                  onClick={() => toggleSecret('shiprocket_password')}
                  style={{
                    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: '#9CA3AF',
                  }}
                >
                  {showSecrets.shiprocket_password ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                Default Pickup Location (Warehouse Name)
              </label>
              <input
                type="text"
                value={form.shiprocket_pickup_location}
                onChange={e => handleChange('shiprocket_pickup_location', e.target.value)}
                placeholder="warehouse or Primary"
                style={{
                  width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #D1D5DB',
                  fontSize: 13, color: '#111827', boxSizing: 'border-box', outline: 'none',
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                Direct API Token (Optional JWT override)
              </label>
              <input
                type="text"
                value={form.shiprocket_token}
                onChange={e => handleChange('shiprocket_token', e.target.value)}
                placeholder="ey..."
                style={{
                  width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #D1D5DB',
                  fontSize: 13, fontFamily: MONO, color: '#111827', boxSizing: 'border-box', outline: 'none',
                }}
              />
            </div>
          </div>
        </div>

        {/* ── 3. Google Sheets Webhook Sync ──────────────────────── */}
        <div style={{ background: '#FFFFFF', border: '1px solid #ECEEF1', borderRadius: 16, padding: 24, marginBottom: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: '#FFF0E6', color: '#FF5A00', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <FileSpreadsheet size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#111827' }}>Google Sheets Live Sync</h3>
              <p style={{ margin: 0, fontSize: 12, color: '#6B7280' }}>Appends orders and lead data to your spreadsheet in real-time</p>
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
              Google Apps Script / Webhook URL
            </label>
            <input
              type="text"
              value={form.google_sheet_webhook_url}
              onChange={e => handleChange('google_sheet_webhook_url', e.target.value)}
              placeholder="https://script.google.com/macros/s/AKfycb.../exec"
              style={{
                width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #D1D5DB',
                fontSize: 13, fontFamily: MONO, color: '#111827', boxSizing: 'border-box', outline: 'none',
              }}
            />
          </div>
        </div>

        {/* ── 4. WhatsApp Meta Flow & Order Defaults ──────────────── */}
        <div style={{ background: '#FFFFFF', border: '1px solid #ECEEF1', borderRadius: 16, padding: 24, marginBottom: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: '#FAF5FF', color: '#9333EA', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Zap size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#111827' }}>WhatsApp Meta Flows & Orders</h3>
              <p style={{ margin: 0, fontSize: 12, color: '#6B7280' }}>Default order prefix and Meta Flow ID for in-chat address capture</p>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                Default WhatsApp Flow ID
              </label>
              <input
                type="text"
                value={form.whatsapp_flow_id}
                onChange={e => handleChange('whatsapp_flow_id', e.target.value)}
                placeholder="e.g. 1581452639423610"
                style={{
                  width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #D1D5DB',
                  fontSize: 13, fontFamily: MONO, color: '#111827', boxSizing: 'border-box', outline: 'none',
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                Order Number Prefix
              </label>
              <input
                type="text"
                value={form.order_prefix}
                onChange={e => handleChange('order_prefix', e.target.value)}
                placeholder="LN- or ORD-"
                style={{
                  width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #D1D5DB',
                  fontSize: 13, fontFamily: MONO, color: '#111827', boxSizing: 'border-box', outline: 'none',
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                Default Shipping Fee (₹)
              </label>
              <input
                type="number"
                value={form.shipping_fee}
                onChange={e => handleChange('shipping_fee', e.target.value)}
                placeholder="60"
                style={{
                  width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #D1D5DB',
                  fontSize: 13, color: '#111827', boxSizing: 'border-box', outline: 'none',
                }}
              />
            </div>
          </div>
        </div>

        {/* ── 5. AI Providers (OpenAI / Anthropic) ────────────────── */}
        <div style={{ background: '#FFFFFF', border: '1px solid #ECEEF1', borderRadius: 16, padding: 24, boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: '#FAF5FF', color: '#9333EA', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Bot size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#111827' }}>AI Providers</h3>
              <p style={{ margin: 0, fontSize: 12, color: '#6B7280' }}>Powers autonomous AI agent sweeps and conversation intelligence</p>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                OpenAI API Key
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showSecrets.openai_api_key ? 'text' : 'password'}
                  value={form.openai_api_key}
                  onChange={e => handleChange('openai_api_key', e.target.value)}
                  placeholder="sk-proj-..."
                  style={{
                    width: '100%', padding: '9px 36px 9px 12px', borderRadius: 8, border: '1px solid #D1D5DB',
                    fontSize: 13, fontFamily: MONO, color: '#111827', boxSizing: 'border-box', outline: 'none',
                  }}
                />
                <button
                  type="button"
                  onClick={() => toggleSecret('openai_api_key')}
                  style={{
                    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: '#9CA3AF',
                  }}
                >
                  {showSecrets.openai_api_key ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                Anthropic API Key
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showSecrets.anthropic_api_key ? 'text' : 'password'}
                  value={form.anthropic_api_key}
                  onChange={e => handleChange('anthropic_api_key', e.target.value)}
                  placeholder="sk-ant-..."
                  style={{
                    width: '100%', padding: '9px 36px 9px 12px', borderRadius: 8, border: '1px solid #D1D5DB',
                    fontSize: 13, fontFamily: MONO, color: '#111827', boxSizing: 'border-box', outline: 'none',
                  }}
                />
                <button
                  type="button"
                  onClick={() => toggleSecret('anthropic_api_key')}
                  style={{
                    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: '#9CA3AF',
                  }}
                >
                  {showSecrets.anthropic_api_key ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
