import { useState } from 'react';
import { Calculator, Check, ArrowRight, Zap, TrendingUp, ShieldCheck } from 'lucide-react';
import { C, FONT, MONO } from '../../constants.js';

export default function PricingCalculator({ onSelectPlan }) {
  const [conversations, setConversations] = useState(10000);

  // Recommendations:
  // <= 3000: Starter
  // 3001 - 25000: Pro
  // > 25000: Enterprise
  let plan = 'Starter Community';
  let planPrice = 2499;
  let recommendedKey = 'starter';
  if (conversations > 3000 && conversations <= 25000) {
    plan = 'Professional Growth';
    planPrice = 6499;
    recommendedKey = 'pro';
  } else if (conversations > 25000) {
    plan = 'Enterprise Scale';
    planPrice = 16999;
    recommendedKey = 'enterprise';
  }

  // Estimates (INR):
  // Average support desk agent handles ~1,200 conversations/mo (~₹28,000/mo)
  const humanAgentsNeeded = Math.max(1, Math.ceil(conversations / 1200));
  const estimatedHoursSaved = Math.round((conversations * 4.5) / 60); // 4.5 mins per chat
  const estimatedSavings = Math.max(15000, Math.round(humanAgentsNeeded * 28000 - planPrice));

  return (
    <div
      style={{
        background: '#ffffff',
        borderRadius: 18,
        border: `1px solid ${C.border}`,
        boxShadow: '0 12px 36px rgba(0,0,0,0.06)',
        padding: '28px 24px',
        fontFamily: FONT,
        maxWidth: 720,
        margin: '0 auto',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
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
          <Calculator size={18} />
        </div>
        <div>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: C.text }}>
            Interactive ROI & Volume Calculator
          </h3>
          <p style={{ margin: 0, fontSize: 13, color: C.textSecondary }}>
            Estimate your monthly plan and cost savings based on customer conversation volume
          </p>
        </div>
      </div>

      {/* Slider */}
      <div style={{ marginBottom: 28, background: '#f8fafc', padding: '18px 20px', borderRadius: 12, border: `1px solid ${C.border}` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: C.textSecondary }}>
            Monthly Inbound & Outbound WhatsApp Conversations:
          </span>
          <span style={{ fontSize: 20, fontWeight: 700, color: C.primary, fontFamily: MONO }}>
            {conversations.toLocaleString()} / mo
          </span>
        </div>
        <input
          type="range"
          min="1000"
          max="80000"
          step="1000"
          value={conversations}
          onChange={(e) => setConversations(Number(e.target.value))}
          style={{ width: '100%', cursor: 'pointer', accentColor: 'var(--c-primary, #dc2626)' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: C.textMuted, marginTop: 4 }}>
          <span>1,000 chats</span>
          <span>25,000 chats</span>
          <span>50,000 chats</span>
          <span>80,000+ chats</span>
        </div>
      </div>

      {/* Metrics Result Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14, marginBottom: 24 }}>
        <div style={{ background: '#f8fafc', padding: '16px', borderRadius: 12, border: `1px solid ${C.border}`, textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: C.textSecondary, fontWeight: 600, marginBottom: 4 }}>Recommended Plan</div>
          <div style={{ fontSize: 17, fontWeight: 700, color: C.text }}>{plan}</div>
          <div style={{ fontSize: 13, color: C.primary, fontWeight: 700, marginTop: 2 }}>₹{planPrice.toLocaleString('en-IN')} / month</div>
        </div>

        <div style={{ background: '#F0FDF4', padding: '16px', borderRadius: 12, border: '1px solid #BBF7D0', textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: '#166534', fontWeight: 600, marginBottom: 4 }}>Support Time Saved</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#15803D', fontFamily: MONO }}>
            ~{estimatedHoursSaved.toLocaleString('en-IN')} hrs
          </div>
          <div style={{ fontSize: 11, color: '#166534', marginTop: 2 }}>per month via automated AI</div>
        </div>

        <div style={{ background: '#EFF6FF', padding: '16px', borderRadius: 12, border: '1px solid #BFDBFE', textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: '#1E40AF', fontWeight: 600, marginBottom: 4 }}>Est. Cost Savings</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#1D4ED8', fontFamily: MONO }}>
            ₹{estimatedSavings.toLocaleString('en-IN')}
          </div>
          <div style={{ fontSize: 11, color: '#1E40AF', marginTop: 2 }}>compared to manual support desks</div>
        </div>
      </div>

      {/* Action Button */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: C.textSecondary }}>
          <ShieldCheck size={16} color="#16a34a" /> 14-day free trial on all plans · No credit card required
        </div>
        <button
          onClick={() => onSelectPlan && onSelectPlan(recommendedKey)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 20px',
            borderRadius: 8,
            background: C.primary,
            color: '#fff',
            border: 'none',
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Select {plan} <ArrowRight size={15} />
        </button>
      </div>
    </div>
  );
}
