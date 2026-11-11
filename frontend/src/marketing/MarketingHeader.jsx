import { useState } from 'react';
import { Menu, X, ArrowRight, Shield, Sparkles, LayoutDashboard, ChevronRight } from 'lucide-react';
import { C, FONT } from '../constants.js';

export default function MarketingHeader({ activeRoute, onNavigate, onOpenDemo, user }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const navLinks = [
    { id: 'landing', label: 'Home' },
    { id: 'features', label: 'Features' },
    { id: 'solutions', label: 'Solutions' },
    { id: 'pricing', label: 'Pricing' },
    { id: 'about', label: 'About & Security' },
  ];

  const handleNav = (id) => {
    setMobileOpen(false);
    onNavigate(id);
  };

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        background: 'rgba(255, 255, 255, 0.92)',
        backdropFilter: 'blur(10px)',
        borderBottom: `1px solid ${C.border}`,
        fontFamily: FONT,
      }}
    >
      <div
        style={{
          maxWidth: 1200,
          margin: '0 auto',
          padding: '0 24px',
          height: 68,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        {/* Brand Logo */}
        <div
          onClick={() => handleNav('landing')}
          style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}
        >
          <img
            src="/synaptic-logo.svg"
            alt="Synaptic Chat"
            style={{ width: 32, height: 32, objectFit: 'contain' }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
          <span style={{ fontSize: 17, fontWeight: 800, color: C.text, letterSpacing: '-0.02em' }}>
            Synaptic Chat
          </span>
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              padding: '2px 6px',
              borderRadius: 6,
              background: '#f1f5f9',
              color: '#475569',
              border: '1px solid #e2e8f0',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            WhatsApp CRM
          </span>
        </div>

        {/* Desktop Nav Links */}
        <nav
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 24,
          }}
          className="marketing-desktop-nav"
        >
          <style>{`
            @media (max-width: 767px) {
              .marketing-desktop-nav { display: none !important; }
            }
            @media (min-width: 768px) {
              .marketing-mobile-btn { display: none !important; }
            }
          `}</style>
          {navLinks.map((link) => {
            const isActive = activeRoute === link.id || (link.id === 'landing' && activeRoute === '');
            return (
              <button
                key={link.id}
                onClick={() => handleNav(link.id)}
                style={{
                  border: 'none',
                  background: 'transparent',
                  cursor: 'pointer',
                  fontSize: 14,
                  fontWeight: isActive ? 700 : 500,
                  color: isActive ? C.primary : C.textSecondary,
                  transition: 'color .15s ease',
                  padding: '6px 2px',
                }}
              >
                {link.label}
              </button>
            );
          })}
        </nav>

        {/* Action CTAs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {user ? (
            <button
              onClick={() => onNavigate('home')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '8px 16px',
                borderRadius: 8,
                background: C.primary,
                color: '#fff',
                border: 'none',
                fontSize: 13,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <LayoutDashboard size={15} /> Open App
            </button>
          ) : (
            <>
              <button
                onClick={() => onNavigate('login')}
                style={{
                  padding: '8px 14px',
                  borderRadius: 8,
                  border: `1px solid ${C.border}`,
                  background: '#fff',
                  color: C.text,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Sign In
              </button>
              <button
                onClick={onOpenDemo}
                style={{
                  display: 'none',
                  alignItems: 'center',
                  gap: 6,
                  padding: '8px 16px',
                  borderRadius: 8,
                  background: C.primary,
                  color: '#fff',
                  border: 'none',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
                className="marketing-desktop-nav"
              >
                <Sparkles size={14} /> Book Demo
              </button>
            </>
          )}

          {/* Mobile Menu Hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="marketing-mobile-btn"
            style={{
              border: `1px solid ${C.border}`,
              background: '#fff',
              borderRadius: 8,
              padding: '6px 8px',
              cursor: 'pointer',
              color: C.text,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div
          style={{
            borderTop: `1px solid ${C.border}`,
            background: '#ffffff',
            padding: '16px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          {navLinks.map((link) => (
            <div
              key={link.id}
              onClick={() => handleNav(link.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 4px',
                fontSize: 15,
                fontWeight: 600,
                color: activeRoute === link.id ? C.primary : C.text,
                cursor: 'pointer',
                borderBottom: `1px solid ${C.border}`,
              }}
            >
              <span>{link.label}</span>
              <ChevronRight size={16} color={C.textMuted} />
            </div>
          ))}
          {!user && (
            <button
              onClick={() => {
                setMobileOpen(false);
                onOpenDemo();
              }}
              style={{
                marginTop: 8,
                padding: '12px',
                borderRadius: 8,
                background: C.primary,
                color: '#fff',
                border: 'none',
                fontSize: 14,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
              }}
            >
              <Sparkles size={16} /> Book a Personalized Demo
            </button>
          )}
        </div>
      )}
    </header>
  );
}
