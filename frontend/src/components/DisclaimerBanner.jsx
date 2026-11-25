import React from 'react';
import { ShieldAlert, AlertTriangle } from 'lucide-react';

export default function DisclaimerBanner() {
  return (
    <div className="disclaimer-banner">
      <AlertTriangle size={15} color="#d97706" />
      <span>
        <strong>Medical Notice:</strong> Smart Health AI is an educational clinical decision-support assistant. It does <strong>not</strong> provide confirmed diagnoses or prescribe medications. All decisions require professional review by a licensed physician. If you are experiencing a medical emergency, call <strong>911 / 112</strong> immediately.
      </span>
    </div>
  );
}
