import { useState } from 'react';
import {
  MessageSquare, Bot, KanbanSquare, Megaphone, Zap, Users, ShieldCheck,
  ArrowRight, Sparkles, Check, CheckCircle2, TrendingUp, Layers, Cpu
} from 'lucide-react';
import { C, FONT, MONO } from '../../constants.js';
import WhatsAppSimulator from '../components/WhatsAppSimulator.jsx';

export default function LandingPage({ onNavigate, onOpenDemo }) {
  return (
    <div style={{ fontFamily: FONT, background: C.pageBg, color: C.text }}>
      {/* ── HERO SECTION ──────────────────────────────────────────────── */}
      <section style={{ padding: '64px 24px 72px', maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 48, alignItems: 'center' }}>
          <div>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 14px',
                borderRadius: 20,
                background: '#FEE2E2',
                border: '1px solid #FECACA',
                color: C.primary,
                fontSize: 12.5,
                fontWeight: 700,
                marginBottom: 20,
                letterSpacing: '0.02em',
              }}
            >
              <Sparkles size={14} /> Next-Gen AI WhatsApp CRM Platform
            </div>

            <h1
              style={{
                fontSize: 'clamp(32px, 5vw, 54px)',
                fontWeight: 800,
                lineHeight: 1.15,
                letterSpacing: '-0.03em',
                margin: '0 0 20px',
                color: C.text,
              }}
            >
              Scale customer conversations with{' '}
              <span style={{ color: C.primary }}>Autonomous AI</span> & Shared Team Inbox.
            </h1>

            <p style={{ fontSize: 16, color: C.textSecondary, lineHeight: 1.6, margin: '0 0 32px', maxWidth: 520 }}>
              Synaptic Chat by Synaptic Info connects multiple WhatsApp phone numbers into a unified CRM. Deploy autonomous AI agents that qualify leads and resolve inquiries 24/7, while your human agents step in seamlessly with zero collision.
            </p>

            <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap', marginBottom: 36 }}>
              <button
                onClick={() => onNavigate('login')}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '13px 26px',
                  borderRadius: 10,
                  background: C.primary,
                  color: '#ffffff',
                  border: 'none',
                  fontSize: 15,
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 8px 20px rgba(220, 38, 38, 0.25)',
                  transition: 'transform .15s',
                }}
              >
                Start Free Trial <ArrowRight size={17} />
              </button>
              <button
                onClick={onOpenDemo}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '13px 22px',
                  borderRadius: 10,
                  background: '#ffffff',
                  color: C.text,
                  border: `1.5px solid ${C.border}`,
                  fontSize: 15,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <Sparkles size={16} color={C.primary} /> Book Live Demo
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap', fontSize: 12.5, color: C.textSecondary }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <CheckCircle2 size={16} color="#16a34a" /> Official Meta Cloud API
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <CheckCircle2 size={16} color="#16a34a" /> Multi-Tenant Isolation
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <CheckCircle2 size={16} color="#16a34a" /> BYOK AI Models
              </span>
            </div>
          </div>

          {/* Right Column: Live Interactive WhatsApp Simulator */}
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <WhatsAppSimulator />
          </div>
        </div>
      </section>

      {/* ── METRICS TICKER ────────────────────────────────────────────── */}
      <section style={{ borderTop: `1px solid ${C.border}`, borderBottom: `1px solid ${C.border}`, background: '#ffffff', padding: '36px 24px' }}>
        <div
          style={{
            maxWidth: 1200,
            margin: '0 auto',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 24,
            textAlign: 'center',
          }}
        >
          <div>
            <div style={{ fontSize: 32, fontWeight: 800, color: C.text, fontFamily: MONO }}>10x</div>
            <div style={{ fontSize: 13, color: C.textSecondary, marginTop: 4 }}>Faster First Response Speed</div>
          </div>
          <div>
            <div style={{ fontSize: 32, fontWeight: 800, color: '#16a34a', fontFamily: MONO }}>98%</div>
            <div style={{ fontSize: 13, color: C.textSecondary, marginTop: 4 }}>WhatsApp Message Open Rate</div>
          </div>
          <div>
            <div style={{ fontSize: 32, fontWeight: 800, color: C.primary, fontFamily: MONO }}>24 / 7</div>
            <div style={{ fontSize: 13, color: C.textSecondary, marginTop: 4 }}>Autonomous AI Resolution</div>
          </div>
          <div>
            <div style={{ fontSize: 32, fontWeight: 800, color: '#534AB7', fontFamily: MONO }}>100%</div>
            <div style={{ fontSize: 13, color: C.textSecondary, marginTop: 4 }}>Data Residency & Privacy</div>
          </div>
        </div>
      </section>

      {/* ── BENTO FEATURES GRID ────────────────────────────────────────── */}
      <section style={{ padding: '80px 24px', maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', maxWidth: 680, margin: '0 auto 52px' }}>
          <h2 style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.02em', margin: '0 0 14px' }}>
            Everything required to turn WhatsApp into your highest-converting channel
          </h2>
          <p style={{ fontSize: 15, color: C.textSecondary, lineHeight: 1.5, margin: 0 }}>
            No fragmented tools. Synaptic Chat unifies inbox management, customer relationship pipelines, and generative AI agents into one high-performance stack.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
          {/* Card 1: Shared Team Inbox */}
          <div style={{ background: '#ffffff', borderRadius: 16, border: `1px solid ${C.border}`, padding: '28px 24px', boxShadow: C.shadowSm }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: '#EFF6FF', color: '#2563EB', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 18 }}>
              <MessageSquare size={22} />
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 10px' }}>Shared Team Inbox</h3>
            <p style={{ fontSize: 13.5, color: C.textSecondary, lineHeight: 1.6, margin: '0 0 18px' }}>
              Assign chats, tag conversations, add internal team notes, and prevent agent collision. One phone number handles dozens of simultaneous customer conversations.
            </p>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#2563EB', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }} onClick={() => onNavigate('features')}>
              Explore Shared Inbox <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 2: Autonomous AI Agents */}
          <div style={{ background: '#ffffff', borderRadius: 16, border: `1px solid ${C.border}`, padding: '28px 24px', boxShadow: C.shadowSm }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: '#FCEBEB', color: C.primary, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 18 }}>
              <Bot size={22} />
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 10px' }}>Autonomous AI Agents (BYOK)</h3>
            <p style={{ fontSize: 13.5, color: C.textSecondary, lineHeight: 1.6, margin: '0 0 18px' }}>
              Create intelligent agents powered by GPT-4o, Claude 3.5, or DeepSeek. Equip them with webhooks and tool-calling to look up orders, update Google Sheets, and qualify leads.
            </p>
            <div style={{ fontSize: 12, fontWeight: 600, color: C.primary, display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }} onClick={() => onNavigate('features')}>
              Explore AI Agents <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 3: Visual Deals & Pipelines */}
          <div style={{ background: '#ffffff', borderRadius: 16, border: `1px solid ${C.border}`, padding: '28px 24px', boxShadow: C.shadowSm }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: '#F0FDF4', color: '#16a34a', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 18 }}>
              <KanbanSquare size={22} />
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 10px' }}>Deals & Sales Pipelines</h3>
            <p style={{ fontSize: 13.5, color: C.textSecondary, lineHeight: 1.6, margin: '0 0 18px' }}>
              Drag and drop leads through stages on a customizable Kanban board. Track deal values, won/lost ratios, and sync directly with WhatsApp chat histories.
            </p>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#16a34a', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }} onClick={() => onNavigate('features')}>
              Explore Pipelines <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 4: Official Meta Cloud Templates & Broadcasts */}
          <div style={{ background: '#ffffff', borderRadius: 16, border: `1px solid ${C.border}`, padding: '28px 24px', boxShadow: C.shadowSm }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: '#FAF5FF', color: '#9333EA', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 18 }}>
              <Megaphone size={22} />
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 10px' }}>Templates & Bulk Broadcasts</h3>
            <p style={{ fontSize: 13.5, color: C.textSecondary, lineHeight: 1.6, margin: '0 0 18px' }}>
              Design approved WhatsApp templates with rich headers, media, and quick-reply buttons. Send segmented broadcast campaigns with high-throughput delivery and live read-receipt analytics.
            </p>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#9333EA', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }} onClick={() => onNavigate('features')}>
              Explore Templates <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 5: Flow Automations */}
          <div style={{ background: '#ffffff', borderRadius: 16, border: `1px solid ${C.border}`, padding: '28px 24px', boxShadow: C.shadowSm }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: '#FFFBEB', color: '#D97706', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 18 }}>
              <Zap size={22} />
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 10px' }}>Visual Flow Automations</h3>
            <p style={{ fontSize: 13.5, color: C.textSecondary, lineHeight: 1.6, margin: '0 0 18px' }}>
              Trigger automated responses on keywords, button clicks, or external webhook events. Build decision trees that route inquiries to the right sales reps instantly.
            </p>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#D97706', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }} onClick={() => onNavigate('features')}>
              Explore Automations <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 6: Multi-Tenant Architecture & Switchboard */}
          <div style={{ background: '#ffffff', borderRadius: 16, border: `1px solid ${C.border}`, padding: '28px 24px', boxShadow: C.shadowSm }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: '#F8FAFC', color: '#0F172A', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 18 }}>
              <Layers size={22} />
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 10px' }}>Multi-Tenant Switchboard</h3>
            <p style={{ fontSize: 13.5, color: C.textSecondary, lineHeight: 1.6, margin: '0 0 18px' }}>
              Built for agencies and enterprises. Manage distinct client organizations, customize accessible modules per client via feature switchboard, and allocate quota caps.
            </p>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#0F172A', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }} onClick={() => onNavigate('solutions')}>
              Explore Enterprise Tenancy <ArrowRight size={14} />
            </div>
          </div>
        </div>
      </section>

      {/* ── BOTTOM CONVERSION BANNER ──────────────────────────────────── */}
      <section style={{ padding: '40px 24px 80px', maxWidth: 1200, margin: '0 auto' }}>
        <div
          style={{
            background: 'linear-gradient(135deg, #0F0F10 0%, #1c1c1f 100%)',
            borderRadius: 24,
            padding: '60px 40px',
            color: '#ffffff',
            textAlign: 'center',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <div style={{ maxWidth: 640, margin: '0 auto', position: 'relative', zIndex: 1 }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'rgba(255,255,255,0.1)', padding: '6px 14px', borderRadius: 20, fontSize: 12, fontWeight: 600, marginBottom: 18 }}>
              <ShieldCheck size={14} color="#25D366" /> Certified WhatsApp Business Solution
            </div>
            <h2 style={{ fontSize: 'clamp(28px, 4vw, 42px)', fontWeight: 800, letterSpacing: '-0.02em', margin: '0 0 18px' }}>
              Ready to transform your customer operations on WhatsApp?
            </h2>
            <p style={{ fontSize: 16, color: '#A1A1AA', lineHeight: 1.6, margin: '0 0 32px' }}>
              Join fast-growing sales and support teams using Synaptic Chat. Setup takes under 5 minutes with our Docker self-host or managed cloud.
            </p>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 14, flexWrap: 'wrap' }}>
              <button
                onClick={() => onNavigate('login')}
                style={{
                  padding: '13px 28px',
                  borderRadius: 10,
                  background: C.primary,
                  color: '#ffffff',
                  border: 'none',
                  fontSize: 15,
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 8px 24px rgba(220, 38, 38, 0.4)',
                }}
              >
                Get Started Now
              </button>
              <button
                onClick={onOpenDemo}
                style={{
                  padding: '13px 24px',
                  borderRadius: 10,
                  background: 'rgba(255,255,255,0.12)',
                  color: '#ffffff',
                  border: '1px solid rgba(255,255,255,0.2)',
                  fontSize: 15,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Request Enterprise Demo
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
