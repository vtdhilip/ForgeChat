import { useState, useEffect, useRef } from 'react';
import { Bot, User, CheckCheck, Sparkles, Send, ShieldCheck, Zap } from 'lucide-react';
import { C, FONT, MONO } from '../../constants.js';

const SCENARIOS = {
  ai: [
    { from: 'customer', text: 'Hi! Do you have pricing for enterprise team plans?', time: '10:41 AM' },
    { from: 'system', text: '🤖 Synaptic AI Agent "Atlas" activated · Querying Knowledge Base', time: '10:41 AM' },
    {
      from: 'agent',
      type: 'ai',
      text: 'Hello! 👋 Yes, our Enterprise plan includes unlimited team seats, BYOK custom AI models (GPT-4o & Claude 3.5), and dedicated phone lines. Would you like a breakdown or a live demo?',
      time: '10:41 AM',
    },
    { from: 'customer', text: 'Does it support automated order tracking and CRM sync?', time: '10:42 AM' },
    {
      from: 'agent',
      type: 'ai',
      text: 'Absolutely! 🚀 Synaptic Chat integrates directly with Shopify, Razorpay, and Shiprocket for instant tracking, plus 2-way syncing with HubSpot and Google Sheets.',
      time: '10:42 AM',
    },
  ],
  human: [
    { from: 'customer', text: 'I need help with a custom API webhook for our billing system.', time: '11:15 AM' },
    { from: 'system', text: '⚡ AI flagged complex integration · Assigned to Senior Engineer Naveen', time: '11:15 AM' },
    {
      from: 'agent',
      type: 'human',
      name: 'Naveen (Integration Specialist)',
      text: 'Hi there! Naveen here from engineering. I have your account details open. You can send JSON payloads to our /api/webhook/custom endpoint. Let me generate a test webhook secret for you.',
      time: '11:16 AM',
    },
    { from: 'customer', text: 'That was super fast, thank you!', time: '11:17 AM' },
  ],
};

export default function WhatsAppSimulator() {
  const [mode, setMode] = useState('ai');
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const chatBodyRef = useRef(null);

  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  useEffect(() => {
    setMessages([]);
    setIsTyping(true);

    const scenario = SCENARIOS[mode];
    let currentIndex = 0;

    const interval = setInterval(() => {
      if (currentIndex < scenario.length) {
        const nextMessage = scenario[currentIndex];
        currentIndex += 1;
        if (nextMessage) {
          setMessages((prev) => [...prev, nextMessage]);
        }
        if (currentIndex >= scenario.length) {
          setIsTyping(false);
          clearInterval(interval);
        }
      }
    }, 900);

    return () => clearInterval(interval);
  }, [mode]);

  return (
    <div
      style={{
        background: '#ffffff',
        borderRadius: 18,
        border: `1px solid ${C.border}`,
        boxShadow: '0 20px 45px rgba(0, 0, 0, 0.08)',
        overflow: 'hidden',
        width: '100%',
        maxWidth: 480,
        fontFamily: FONT,
      }}
    >
      {/* Top Simulator Mode Switcher */}
      <div
        style={{
          background: '#f8fafc',
          padding: '10px 14px',
          borderBottom: `1px solid ${C.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span style={{ fontSize: 11, fontWeight: 700, color: C.textSecondary, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Interactive Simulation
        </span>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={() => setMode('ai')}
            style={{
              padding: '4px 10px',
              borderRadius: 6,
              border: 'none',
              background: mode === 'ai' ? C.primary : 'transparent',
              color: mode === 'ai' ? '#fff' : C.textSecondary,
              fontSize: 11.5,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <Bot size={13} /> AI Autonomous
          </button>
          <button
            onClick={() => setMode('human')}
            style={{
              padding: '4px 10px',
              borderRadius: 6,
              border: 'none',
              background: mode === 'human' ? '#0F6E56' : 'transparent',
              color: mode === 'human' ? '#fff' : C.textSecondary,
              fontSize: 11.5,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <User size={13} /> Team Coexistence
          </button>
        </div>
      </div>

      {/* WhatsApp Window Header */}
      <div
        style={{
          background: '#075E54',
          color: '#ffffff',
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 38,
              height: 38,
              borderRadius: '50%',
              background: '#ffffff',
              color: '#075E54',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: 16,
            }}
          >
            SC
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>
              Synaptic Chat Official
              <ShieldCheck size={14} color="#25D366" />
            </div>
            <div style={{ fontSize: 11, color: '#e2f7ea' }}>
              {isTyping ? 'typing…' : 'Online · Official Meta Cloud API'}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, background: 'rgba(255,255,255,0.15)', padding: '4px 8px', borderRadius: 12 }}>
          <Zap size={12} color="#FACC15" /> Active
        </div>
      </div>

      {/* Chat Messages Area */}
      <div
        ref={chatBodyRef}
        style={{
          background: '#EFEAE2',
          backgroundImage: C.waBgPattern,
          padding: '16px 14px',
          minHeight: 280,
          maxHeight: 320,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}
      >
        {messages.map((m, i) => {
          if (!m) return null;
          if (m.from === 'system') {
            return (
              <div
                key={i}
                style={{
                  alignSelf: 'center',
                  background: 'rgba(255, 255, 255, 0.85)',
                  backdropFilter: 'blur(4px)',
                  padding: '4px 10px',
                  borderRadius: 12,
                  fontSize: 10.5,
                  fontWeight: 600,
                  color: C.textSecondary,
                  boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                  textAlign: 'center',
                  maxWidth: '90%',
                }}
              >
                {m.text}
              </div>
            );
          }

          const isMe = m.from === 'agent';
          return (
            <div
              key={i}
              style={{
                alignSelf: isMe ? 'flex-end' : 'flex-start',
                maxWidth: '82%',
                background: isMe ? '#D9FDD3' : '#ffffff',
                color: '#111b21',
                padding: '8px 11px',
                borderRadius: 8,
                boxShadow: '0 1px 1px rgba(0,0,0,0.1)',
                fontSize: 13,
                lineHeight: 1.45,
                position: 'relative',
              }}
            >
              {m.name && (
                <div style={{ fontSize: 10.5, fontWeight: 700, color: '#0F6E56', marginBottom: 2 }}>
                  {m.name}
                </div>
              )}
              {m.text}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                  gap: 3,
                  fontSize: 9.5,
                  color: '#667781',
                  marginTop: 4,
                }}
              >
                <span>{m.time}</span>
                {isMe && <CheckCheck size={13} color="#53BDEB" />}
              </div>
            </div>
          );
        })}

        {isTyping && (
          <div
            style={{
              alignSelf: 'flex-end',
              background: '#D9FDD3',
              padding: '6px 12px',
              borderRadius: 8,
              fontSize: 11.5,
              color: '#54656f',
              fontStyle: 'italic',
            }}
          >
            Agent replying…
          </div>
        )}
      </div>

      {/* Simulator Bottom Bar */}
      <div
        style={{
          background: '#f0f2f5',
          padding: '10px 14px',
          borderTop: `1px solid ${C.border}`,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <div
          style={{
            flex: 1,
            background: '#ffffff',
            borderRadius: 8,
            padding: '7px 12px',
            fontSize: 12.5,
            color: C.textMuted,
            border: `1px solid ${C.border}`,
          }}
        >
          {mode === 'ai' ? 'Type a question to trigger AI Agent...' : 'Agent reply field (shared inbox)...'}
        </div>
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: '#075E54',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Send size={14} />
        </div>
      </div>
    </div>
  );
}
