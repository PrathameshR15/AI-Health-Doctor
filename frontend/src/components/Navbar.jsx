import React from 'react';
import { Activity, User, LogOut, Stethoscope, ShieldCheck } from 'lucide-react';
import { removeAuthToken, removeUser } from '../api';

export default function Navbar({ currentUser, onLogout, onOpenConsent }) {
  const isDoctor = currentUser?.role === 'doctor';

  return (
    <header className="navbar">
      <div className="nav-content">
        <div className="nav-brand">
          <div className="nav-logo-icon">
            <Activity size={22} />
          </div>
          <div>
            <div className="nav-brand-title">Smart Health AI</div>
            <div className="nav-brand-subtitle">LLM Medical Decision Support</div>
          </div>
        </div>

        <div className="nav-actions">
          {currentUser && (
            <>
              {currentUser.role === 'patient' && (
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  onClick={onOpenConsent}
                  title="View AI Service Consent Status"
                  style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  <ShieldCheck size={14} color="#0d9488" />
                  <span style={{ fontSize: '0.78rem' }}>AI Consent: Active</span>
                </button>
              )}

              <div className="user-badge">
                {isDoctor ? <Stethoscope size={16} color="#6d28d9" /> : <User size={16} color="#0d9488" />}
                <span>{currentUser.full_name}</span>
                <span className={`role-pill ${currentUser.role}`}>
                  {currentUser.role}
                </span>
              </div>

              <button
                type="button"
                className="btn btn-sm btn-secondary"
                onClick={onLogout}
                title="Log Out"
              >
                <LogOut size={15} />
                <span>Sign Out</span>
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
