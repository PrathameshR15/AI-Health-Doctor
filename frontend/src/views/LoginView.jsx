import React, { useState } from 'react';
import { Activity, Stethoscope, User, Lock, Mail, ArrowRight, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { api, setAuthToken, setUser } from '../api';

export default function LoginView({ onLoginSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('patient');
  const [phone, setPhone] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let res;
      if (isRegister) {
        res = await api.register({
          email,
          password,
          full_name: fullName,
          role,
          phone
        });
      } else {
        res = await api.login(email, password);
      }

      setAuthToken(res.access_token);
      setUser(res.user);
      onLoginSuccess(res.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async (demoEmail, demoPass) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.login(demoEmail, demoPass);
      setAuthToken(res.access_token);
      setUser(res.user);
      onLoginSuccess(res.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '85vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem 1rem'
    }}>
      <div style={{ maxWidth: '480px', width: '100%' }}>
        {/* Brand Card */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{
            width: '54px', height: '54px', borderRadius: '14px',
            background: 'linear-gradient(135deg, #0d9488, #0284c7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#ffffff', margin: '0 auto 1rem',
            boxShadow: '0 8px 16px rgba(13, 148, 136, 0.25)'
          }}>
            <Activity size={32} />
          </div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: '800', letterSpacing: '-0.02em', color: 'var(--dark)' }}>
            Smart Health AI
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', marginTop: '0.2rem' }}>
            LLM-Powered Healthcare Assistant with MedSpaCy & FHIR Support
          </p>
        </div>

        {/* 1-Click Quick Demo Login Card */}
        <div className="card" style={{ background: '#f0fdfa', border: '1px solid #99f6e4', marginBottom: '1.5rem', padding: '1.25rem' }}>
          <div style={{ fontWeight: '800', fontSize: '0.86rem', color: '#0f766e', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            ⚡ Quick 1-Click Demo Evaluation
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              style={{ background: '#ffffff', borderColor: '#ccfbf1', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.65rem' }}
              onClick={() => handleDemoLogin('patient@smarthealth.ai', 'Patient@123')}
              disabled={loading}
            >
              <User size={16} color="#0d9488" />
              <div style={{ textAlign: 'left', lineHeight: '1.2' }}>
                <div style={{ fontWeight: '700', fontSize: '0.85rem' }}>Patient Portal</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>John Doe</div>
              </div>
            </button>

            <button
              type="button"
              className="btn btn-secondary btn-sm"
              style={{ background: '#ffffff', borderColor: '#ede9fe', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.65rem' }}
              onClick={() => handleDemoLogin('doctor@smarthealth.ai', 'Doctor@123')}
              disabled={loading}
            >
              <Stethoscope size={16} color="#6d28d9" />
              <div style={{ textAlign: 'left', lineHeight: '1.2' }}>
                <div style={{ fontWeight: '700', fontSize: '0.85rem' }}>Doctor Portal</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Dr. Sarah Chen</div>
              </div>
            </button>
          </div>
        </div>

        {/* Login / Register Card */}
        <div className="card">
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', marginBottom: '1.25rem' }}>
            <button
              type="button"
              onClick={() => { setIsRegister(false); setError(null); }}
              style={{
                flex: 1, padding: '0.75rem', background: 'none', border: 'none',
                fontWeight: '700', fontSize: '0.9rem', cursor: 'pointer',
                color: !isRegister ? 'var(--primary)' : 'var(--text-muted)',
                borderBottom: !isRegister ? '2px solid var(--primary)' : 'none'
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setIsRegister(true); setError(null); }}
              style={{
                flex: 1, padding: '0.75rem', background: 'none', border: 'none',
                fontWeight: '700', fontSize: '0.9rem', cursor: 'pointer',
                color: isRegister ? 'var(--primary)' : 'var(--text-muted)',
                borderBottom: isRegister ? '2px solid var(--primary)' : 'none'
              }}
            >
              Create Account
            </button>
          </div>

          {error && (
            <div style={{
              padding: '0.75rem', background: '#fee2e2', color: '#b91c1c',
              borderRadius: '6px', fontSize: '0.84rem', marginBottom: '1rem', fontWeight: '600'
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {isRegister && (
              <>
                <div className="form-group">
                  <label className="form-label">Full Name</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Jane Doe"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Role</label>
                  <select className="form-select" value={role} onChange={(e) => setRole(e.target.value)}>
                    <option value="patient">Patient</option>
                    <option value="doctor">Medical Doctor</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Phone Number (optional)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. +1-555-0123"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </div>
              </>
            )}

            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                type="email"
                className="form-input"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', padding: '0.75rem', marginTop: '0.5rem' }}
              disabled={loading}
            >
              {loading ? "Authenticating..." : (isRegister ? "Complete Registration" : "Sign In to Portal")}
            </button>
          </form>
        </div>

        {/* Feature List Footer */}
        <div style={{ textAlign: 'center', fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '1rem', lineHeight: '1.6' }}>
          <div>🛡️ Role-Based Access • Protected Health Information Isolation</div>
          <div>📚 Evidence-based sources: WHO • NHS • MedlinePlus • ICMR • NCDC India</div>
        </div>
      </div>
    </div>
  );
}
