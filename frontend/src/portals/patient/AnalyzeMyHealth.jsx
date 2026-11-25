import React, { useState } from 'react';
import { Activity, ShieldAlert, AlertTriangle, CheckCircle, FileText, Stethoscope, Utensils, Pill, BookOpen, Clock, HeartPulse } from 'lucide-react';
import { api } from '../../api';
import SourceBadge from '../../components/SourceBadge';
import EmergencyAlert from '../../components/EmergencyAlert';

const safeText = (val) => {
  if (val === null || val === undefined) return '';
  if (typeof val === 'string' || typeof val === 'number') return String(val);
  if (typeof val === 'object') {
    return val.condition || val.test_name || val.drug_class || val.precaution || val.text || val.food || val.name || JSON.stringify(val);
  }
  return String(val);
};

const safeArray = (val) => {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  if (typeof val === 'object') return Object.values(val);
  return [val];
};

export default function AnalyzeMyHealth() {
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!chiefComplaint.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await api.analyzeFullHealth({
        chief_complaint: chiefComplaint.trim(),
        accompanying_symptoms: [],
        known_conditions: [],
        known_allergies: []
      });
      setResult(data);
    } catch (err) {
      setError(err.message || "Unable to complete analysis. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setChiefComplaint('');
    setError(null);
  };

  return (
    <div>
      <div className="card-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h2 className="card-title" style={{ fontSize: '1.4rem' }}>
            <Activity size={22} color="var(--primary)" /> Analyze My Health
          </h2>
          <p className="card-description">
            Comprehensive AI clinical analysis powered by OpenRouter, MedSpaCy entity structuring, and verified medical guidelines.
          </p>
        </div>
        {result && (
          <button className="btn btn-secondary btn-sm" onClick={handleReset}>
            Start New Analysis
          </button>
        )}
      </div>

      {error && (
        <div style={{ padding: '1rem', background: '#fee2e2', color: '#b91c1c', borderRadius: '8px', marginBottom: '1.5rem', fontWeight: '600' }}>
          {error}
        </div>
      )}

      {!result ? (
        <form onSubmit={handleSubmit} className="card" style={{ maxWidth: '760px' }}>
          <div className="form-group">
            <label className="form-label" style={{ fontSize: '1.05rem', fontWeight: '700', marginBottom: '0.5rem', display: 'block' }}>
              Describe how you are feeling in your own words <span style={{ color: '#dc2626' }}>*</span>
            </label>
            <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)', margin: '0 0 0.75rem 0' }}>
              Just write your symptoms, how many days you have had them, and how mild or strong they feel. No need to select multiple options.
            </p>
            <textarea
              className="form-textarea"
              rows={5}
              placeholder="Example: I have had a dry cough and mild fever for 3 days, along with a sore throat and body tiredness..."
              value={chiefComplaint}
              onChange={(e) => setChiefComplaint(e.target.value)}
              style={{ fontSize: '0.96rem', lineHeight: '1.5' }}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '0.9rem', fontSize: '1rem', fontWeight: '700' }}
            disabled={loading || !chiefComplaint.trim()}
          >
            {loading ? "Analyzing Your Health..." : "Analyze My Health"}
          </button>
        </form>
      ) : (
        /* Results View */
        <div>
          {/* Emergency Warning if triggered */}
          {result.emergency_triage?.is_emergency && (
            <EmergencyAlert message={result.emergency_triage.recommended_action} />
          )}

          {/* Assessment Header Card */}
          <div className="card" style={{ borderLeft: '5px solid var(--primary)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <span className="badge badge-routine" style={{ marginBottom: '0.5rem' }}>
                  Triage Category: {result.emergency_triage?.triage_level || 'ROUTINE'}
                </span>
                <h3 style={{ fontSize: '1.25rem', fontWeight: '800' }}>
                  Health Assessment for: {chiefComplaint}
                </h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  NLP Extracted Entities: <strong>{result.extracted_entities?.active_symptoms?.join(', ') || 'Chief complaint parsed'}</strong>
                </p>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span className="badge badge-urgent">
                  <Clock size={12} /> {result.review_status}
                </span>
              </div>
            </div>

            {/* Medical Reference Badges */}
            {result.assessment?.sources && result.assessment.sources.length > 0 && (
              <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginRight: '0.5rem' }}>
                  Verified Reference Sources:
                </span>
                {result.assessment.sources.map((s, idx) => (
                  <SourceBadge key={idx} source={s} />
                ))}
              </div>
            )}
          </div>

          {/* 1. Possible Health Conditions */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <HeartPulse size={20} color="#0d9488" /> 1. Possible Health Conditions
              </h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                Differential considerations for physician discussion (NOT confirmed diagnoses)
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {safeArray(result.assessment?.possible_conditions).map((c, idx) => (
                <div key={idx} style={{
                  padding: '1rem', background: '#f8fafc', borderRadius: '10px',
                  border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '0.4rem'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: '800', fontSize: '1rem', color: 'var(--dark)' }}>
                      {safeText(c?.condition || c?.name || c)}
                    </span>
                    <span className={`badge ${c?.likelihood === 'High' ? 'badge-emergency' : c?.likelihood === 'Moderate' ? 'badge-urgent' : 'badge-routine'}`}>
                      {safeText(c?.likelihood || 'Moderate')} Likelihood
                    </span>
                  </div>
                  <p style={{ fontSize: '0.86rem', color: '#334155' }}>
                    <strong>Clinical Rationale:</strong> {safeText(c?.rationale || c?.reason || 'Clinical observation')}
                  </p>
                  {c?.clinical_explanation && (
                    <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
                      {safeText(c.clinical_explanation)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 2. Health Precautions & Monitoring */}
          <div className="grid-2">
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <ShieldAlert size={20} color="#0284c7" /> 2. Non-Drug Precautions
                </h3>
              </div>
              <ul style={{ paddingLeft: '1.25rem', fontSize: '0.88rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {safeArray(result.assessment?.precautions).map((p, idx) => (
                  <li key={idx} style={{ color: '#334155' }}>{safeText(p)}</li>
                ))}
              </ul>
            </div>

            {/* 3. Medical Tests to Consider */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <Stethoscope size={20} color="#6d28d9" /> 3. Tests Doctors May Consider
                </h3>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.86rem' }}>
                {safeArray(result.assessment?.test_guidance).map((t, idx) => (
                  <div key={idx} style={{ padding: '0.65rem', background: '#f8fafc', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <div style={{ fontWeight: '700', color: '#1e293b' }}>{safeText(t?.test_name || t?.name || t)}</div>
                    {t?.purpose && <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Purpose: {safeText(t.purpose)}</div>}
                    {t?.when_considered && (
                      <div style={{ fontSize: '0.78rem', color: '#0284c7', marginTop: '0.2rem' }}>
                        Indications: {safeText(t.when_considered)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 4. Allergy & Diet Guidance */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <Utensils size={20} color="#b45309" /> 4. Allergy & Nutritional Guidance
              </h3>
            </div>
            <div className="grid-2" style={{ fontSize: '0.88rem' }}>
              <div style={{ background: '#fef2f2', padding: '1rem', borderRadius: '8px', border: '1px solid #fecaca' }}>
                <h4 style={{ color: '#b91c1c', fontWeight: '700', marginBottom: '0.4rem' }}>Foods & Triggers to Avoid:</h4>
                <ul style={{ paddingLeft: '1.2rem', color: '#7f1d1d' }}>
                  {safeArray(result.assessment?.diet_guidance?.avoid).length > 0 ? (
                    safeArray(result.assessment.diet_guidance.avoid).map((item, idx) => (
                      <li key={idx}>{safeText(item)}</li>
                    ))
                  ) : <li>No specific food restrictions noted.</li>}
                </ul>
              </div>

              <div style={{ background: '#f0fdf4', padding: '1rem', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
                <h4 style={{ color: '#15803d', fontWeight: '700', marginBottom: '0.4rem' }}>Recommended Nutritional Items:</h4>
                <ul style={{ paddingLeft: '1.2rem', color: '#14532d' }}>
                  {safeArray(result.assessment?.diet_guidance?.recommended).length > 0 ? (
                    safeArray(result.assessment.diet_guidance.recommended).map((item, idx) => (
                      <li key={idx}>{safeText(item)}</li>
                    ))
                  ) : <li>Follow a well-balanced hydration & light diet.</li>}
                </ul>
                {result.assessment?.diet_guidance?.hydration && (
                  <p style={{ marginTop: '0.5rem', fontWeight: '600', color: '#166534', fontSize: '0.82rem' }}>
                    Hydration Target: {safeText(result.assessment.diet_guidance.hydration)}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* 5. Symptom-Based Medication Educational Information */}
          <div className="card" style={{ borderLeft: '4px solid #f59e0b' }}>
            <div className="card-header">
              <h3 className="card-title">
                <Pill size={20} color="#d97706" /> 5. Medication Information (Educational Only)
              </h3>
              <span className="badge badge-urgent">NEVER PRESCRIBES DOSAGES</span>
            </div>

            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              The following explains common therapeutic classes relevant to these symptoms. Never take medications without a verified physician prescription.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              {safeArray(result.assessment?.medication_info).map((m, idx) => {
                const examples = safeArray(m?.common_examples || m?.common_agents || m?.examples).map(safeText).join(', ');
                return (
                  <div key={idx} style={{ padding: '0.85rem', background: '#fffbeb', borderRadius: '8px', border: '1px solid #fde68a', fontSize: '0.86rem' }}>
                    <div style={{ fontWeight: '800', color: '#92400e', marginBottom: '0.2rem' }}>
                      {safeText(m?.drug_class || m?.class || 'Therapeutic Class')} {examples && `(${examples})`}
                    </div>
                    {m?.clinical_purpose && (
                      <div style={{ color: '#78350f', marginBottom: '0.25rem' }}>
                        <strong>Clinical Purpose:</strong> {safeText(m.clinical_purpose)}
                      </div>
                    )}
                    <div style={{ color: '#b45309', fontSize: '0.8rem' }}>
                      <strong>Key Precautions & Side Effects:</strong> {safeText(m?.precautions || 'Consult doctor')} • {safeText(m?.side_effects || m?.common_side_effects || 'None noted')}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 6. Structured Doctor Consultation SOAP Note */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <FileText size={20} color="#0284c7" /> 6. Doctor Consultation Summary (SOAP Note)
              </h3>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Prepared for Doctor Review</span>
            </div>

            <div className="soap-box">
              <div className="soap-header">
                Structured Clinical Pre-Encounter SOAP Record
              </div>

              <div className="soap-section">
                <div><span className="soap-letter">S</span> <strong>Subjective</strong></div>
                <p style={{ marginTop: '0.35rem', fontSize: '0.86rem', color: '#334155' }}>
                  {typeof result.assessment?.consultation_summary?.subjective === 'string'
                    ? result.assessment.consultation_summary.subjective
                    : JSON.stringify(result.assessment?.consultation_summary?.subjective)}
                </p>
              </div>

              <div className="soap-section">
                <div><span className="soap-letter">O</span> <strong>Objective</strong></div>
                <p style={{ marginTop: '0.35rem', fontSize: '0.86rem', color: '#334155' }}>
                  {typeof result.assessment?.consultation_summary?.objective === 'string'
                    ? result.assessment.consultation_summary.objective
                    : JSON.stringify(result.assessment?.consultation_summary?.objective)}
                </p>
              </div>

              <div className="soap-section">
                <div><span className="soap-letter">A</span> <strong>Assessment</strong></div>
                <p style={{ marginTop: '0.35rem', fontSize: '0.86rem', color: '#334155' }}>
                  {typeof result.assessment?.consultation_summary?.assessment === 'string'
                    ? result.assessment.consultation_summary.assessment
                    : JSON.stringify(result.assessment?.consultation_summary?.assessment)}
                </p>
              </div>

              <div className="soap-section">
                <div><span className="soap-letter">P</span> <strong>Plan</strong></div>
                <p style={{ marginTop: '0.35rem', fontSize: '0.86rem', color: '#334155' }}>
                  {typeof result.assessment?.consultation_summary?.plan === 'string'
                    ? result.assessment.consultation_summary.plan
                    : JSON.stringify(result.assessment?.consultation_summary?.plan)}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
