import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { api } from '../api.js';
import { C, FONT } from '../constants.js';

const label = {
  display: 'block',
  fontSize: 13,
  fontWeight: 600,
  color: C.textSecondary,
  marginBottom: 6,
};

const input = {
  width: '100%',
  height: 42,
  padding: '0 14px',
  borderRadius: 8,
  border: `1px solid ${C.borderDark}`,
  background: C.cardBg,
  color: C.text,
  fontSize: 14,
  fontFamily: FONT,
  outline: 'none',
};

export default function LoginGate({ onLogin, onBackToMarketing }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) { setError('Enter your email and password.'); return; }
    setError('');
    setLoading(true);
    try {
      const { user } = await api.auth.login(email.trim(), password);
      onLogin(user);
    } catch (err) {
      setError(err.message || 'Email or password is incorrect.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: C.pageBg,
      padding: 24,
      fontFamily: FONT,
      overflowY: 'auto',
    }}>
      <style>{`
        .sc-field:focus { border-color: var(--c-primary); box-shadow: 0 0 0 3px rgba(220,38,38,.15); }
        .sc-submit:hover:not(:disabled) { background: var(--c-primaryHover); }
        .sc-submit:focus-visible, .sc-toggle:focus-visible { outline: 2px solid var(--c-primary); outline-offset: 2px; }
        .sc-submit:disabled { cursor: not-allowed; opacity: .7; }
      `}</style>

      <main style={{ width: '100%', maxWidth: 360 }}>
        {onBackToMarketing && (
          <button
            type="button"
            onClick={onBackToMarketing}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              background: 'none',
              border: 'none',
              color: C.textSecondary,
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
              padding: 0,
              marginBottom: 20,
            }}
          >
            ← Back to Homepage
          </button>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 32 }}>
          <img
            src="/synaptic-logo.svg"
            alt=""
            aria-hidden="true"
            style={{ width: 32, height: 32, objectFit: 'contain' }}
            onError={e => { e.currentTarget.style.display = 'none'; }}
          />
          <span style={{ fontSize: 16, fontWeight: 700, color: C.text, letterSpacing: '-0.01em' }}>
            Synaptic Chat
          </span>
        </div>

        <h1 style={{ fontSize: 24, fontWeight: 700, color: C.text, margin: '0 0 6px', letterSpacing: '-0.02em' }}>
          Sign in
        </h1>
        <p style={{ fontSize: 14, color: C.textSecondary, margin: '0 0 28px', lineHeight: 1.5 }}>
          Use the email and password for your account.
        </p>

        <form onSubmit={handleSubmit} noValidate>
          <div style={{ marginBottom: 16 }}>
            <label htmlFor="login-email" style={label}>Email</label>
            <input
              id="login-email"
              className="sc-field"
              type="email"
              name="email"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              placeholder="you@company.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoFocus
              style={input}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label htmlFor="login-password" style={label}>Password</label>
            <div style={{ position: 'relative' }}>
              <input
                id="login-password"
                className="sc-field"
                type={showPw ? 'text' : 'password'}
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                style={{ ...input, paddingRight: 44 }}
              />
              <button
                type="button"
                className="sc-toggle"
                onClick={() => setShowPw(v => !v)}
                aria-label={showPw ? 'Hide password' : 'Show password'}
                style={{
                  position: 'absolute',
                  right: 6,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: 32,
                  height: 32,
                  border: 'none',
                  borderRadius: 6,
                  background: 'none',
                  cursor: 'pointer',
                  color: C.textSecondary,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {error && (
            <div role="alert" style={{
              background: C.primaryLight,
              color: '#A32D2D',
              borderRadius: 8,
              padding: '10px 12px',
              fontSize: 13,
              lineHeight: 1.45,
              marginBottom: 16,
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            className="sc-submit"
            disabled={loading}
            style={{
              width: '100%',
              height: 42,
              borderRadius: 8,
              border: 'none',
              background: C.primary,
              color: '#fff',
              fontSize: 14,
              fontWeight: 600,
              fontFamily: FONT,
              cursor: 'pointer',
              transition: 'background .15s, opacity .15s',
            }}
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </main>
    </div>
  );
}
