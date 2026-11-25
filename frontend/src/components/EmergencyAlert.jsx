import React from 'react';
import { AlertOctagon, PhoneCall, X } from 'lucide-react';

export default function EmergencyAlert({ message, onClose }) {
  if (!message) return null;

  return (
    <div className="emergency-alert-banner">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <AlertOctagon size={24} />
        <div>
          <div style={{ fontWeight: '800', fontSize: '0.95rem' }}>EMERGENCY WARNING DETECTED</div>
          <div style={{ fontSize: '0.85rem', opacity: 0.95 }}>{message}</div>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <a
          href="tel:112"
          className="btn btn-sm"
          style={{ background: '#ffffff', color: '#dc2626', fontWeight: '800' }}
        >
          <PhoneCall size={16} /> Call Emergency (911 / 112)
        </a>
        {onClose && (
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#ffffff', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        )}
      </div>
    </div>
  );
}
