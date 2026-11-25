import React, { useState } from 'react';
import { ShieldCheck, Lock, CheckCircle2 } from 'lucide-react';
import { api } from '../api';

export default function ConsentModal({ isOpen, onClose, onConsentUpdated }) {
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (!agreed) return;
    setLoading(true);
    try {
      await api.updateConsent(true);
      if (onConsentUpdated) onConsentUpdated(true);
      onClose();
    } catch (err) {
      alert("Error saving consent: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '520px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
          <div style={{
            width: '42px', height: '42px', borderRadius: '12px',
            background: 'var(--primary-light)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', color: 'var(--primary)'
          }}>
            <ShieldCheck size={24} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: '800' }}>Patient AI Service Consent</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Required before processing clinical information</p>
          </div>
        </div>

        <div style={{
          background: '#f8fafc', padding: '1rem', borderRadius: '8px',
          border: '1px solid var(--border)', fontSize: '0.86rem', color: '#334155',
          marginBottom: '1.25rem', lineHeight: '1.5'
        }}>
          <p style={{ marginBottom: '0.6rem' }}>
            To provide automated symptom analysis, clinical entity extraction, and health summaries, Smart Health AI processes your non-identifiable symptoms and clinical reports using OpenRouter AI.
          </p>
          <ul style={{ paddingLeft: '1.2rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            <li>Your medical information is isolated and protected.</li>
            <li>All generated condition possibilities are educational and require doctor review.</li>
            <li>Prescriptions and medication dosages are strictly prohibited on this platform.</li>
            <li>You can revoke or update your consent at any time.</li>
          </ul>
        </div>

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem', marginBottom: '1.5rem' }}>
          <input
            type="checkbox"
            id="consentCheck"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            style={{ width: '18px', height: '18px', marginTop: '2px', cursor: 'pointer' }}
          />
          <label htmlFor="consentCheck" style={{ fontSize: '0.85rem', cursor: 'pointer', fontWeight: '600' }}>
            I understand and consent to sending my entered health information to external AI services for clinical decision-support and educational analysis.
          </label>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!agreed || loading}
            onClick={handleSubmit}
          >
            <CheckCircle2 size={16} /> {loading ? "Saving..." : "Accept & Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
