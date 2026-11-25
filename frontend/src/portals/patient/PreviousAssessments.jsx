import React, { useState, useEffect } from 'react';
import { Activity, Clock, CheckCircle2, AlertOctagon, ChevronRight, ArrowLeft } from 'lucide-react';
import { api } from '../../api';
import SourceBadge from '../../components/SourceBadge';

export default function PreviousAssessments() {
  const [assessments, setAssessments] = useState([]);
  const [selectedAssessment, setSelectedAssessment] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAssessments();
  }, []);

  const loadAssessments = async () => {
    try {
      const data = await api.getPreviousAssessments();
      setAssessments(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = async (id) => {
    try {
      const detail = await api.getAssessmentDetail(id);
      setSelectedAssessment(detail);
    } catch (err) {
      alert("Error loading assessment: " + err.message);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '3rem' }}>Loading previous assessments...</div>;
  }

  if (selectedAssessment) {
    return (
      <div>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => setSelectedAssessment(null)}
          style={{ marginBottom: '1.25rem' }}
        >
          <ArrowLeft size={16} /> Back to Assessments List
        </button>

        <div className="card" style={{ borderLeft: '4px solid var(--primary)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem' }}>
            <div>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.4rem' }}>
                <span className="badge badge-routine">Triage: {selectedAssessment.triage_level}</span>
                {selectedAssessment.emergency_warning && (
                  <span className="badge badge-emergency">Emergency Warning Flagged</span>
                )}
              </div>
              <h2 style={{ fontSize: '1.35rem', fontWeight: '800' }}>{selectedAssessment.title}</h2>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Recorded on {new Date(selectedAssessment.created_at).toLocaleString()}
              </div>
            </div>

            <div>
              {selectedAssessment.doctor_review_status === 'approved' ? (
                <span className="badge badge-selfcare"><CheckCircle2 size={13} /> Approved by Doctor</span>
              ) : (
                <span className="badge badge-urgent"><Clock size={13} /> Doctor Review Pending</span>
              )}
            </div>
          </div>

          {selectedAssessment.doctor_notes && (
            <div style={{ marginTop: '1rem', padding: '0.85rem', background: '#f0fdf4', borderRadius: '8px', border: '1px solid #bbf7d0', fontSize: '0.86rem' }}>
              <strong style={{ color: '#166534' }}>Doctor Feedback & Sign-Off:</strong>
              <p style={{ marginTop: '0.2rem', color: '#14532d' }}>{selectedAssessment.doctor_notes}</p>
            </div>
          )}

          {/* Sources */}
          {selectedAssessment.sources && selectedAssessment.sources.length > 0 && (
            <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginRight: '0.5rem' }}>
                References:
              </span>
              {selectedAssessment.sources.map((s, idx) => (
                <SourceBadge key={idx} source={s} />
              ))}
            </div>
          )}
        </div>

        {/* Possible Conditions */}
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '1rem' }}>
            Possible Health Conditions Evaluated
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {selectedAssessment.possible_conditions?.map((c, i) => (
              <div key={i} style={{ padding: '0.85rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong style={{ fontSize: '0.95rem' }}>{c.condition}</strong>
                  <span className="badge badge-routine">{c.likelihood} Likelihood</span>
                </div>
                <p style={{ fontSize: '0.84rem', color: '#334155', marginTop: '0.35rem' }}>{c.rationale}</p>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>{c.clinical_explanation}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Precautions & Tests */}
        <div className="grid-2">
          <div className="card">
            <h3 className="card-title" style={{ marginBottom: '0.8rem' }}>Non-Drug Precautions</h3>
            <ul style={{ paddingLeft: '1.2rem', fontSize: '0.86rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              {selectedAssessment.precautions?.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          </div>

          <div className="card">
            <h3 className="card-title" style={{ marginBottom: '0.8rem' }}>Medical Tests to Consider</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.84rem' }}>
              {selectedAssessment.test_guidance?.map((t, i) => (
                <div key={i} style={{ padding: '0.5rem', background: '#f8fafc', borderRadius: '6px' }}>
                  <strong>{t.test_name}:</strong> {t.purpose}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="card-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h2 className="card-title" style={{ fontSize: '1.4rem' }}>
            <Activity size={22} color="var(--primary)" /> Previous AI Health Assessments
          </h2>
          <p className="card-description">
            Complete record of your previous AI evaluations, symptom checks, and doctor reviews.
          </p>
        </div>
      </div>

      {assessments.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <p style={{ color: 'var(--text-muted)' }}>No previous assessments on record.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {assessments.map((a) => (
            <div
              key={a.id}
              className="card"
              onClick={() => handleSelect(a.id)}
              style={{
                cursor: 'pointer',
                marginBottom: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                transition: 'all 0.15s ease'
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.3rem' }}>
                  <span style={{ fontWeight: '800', fontSize: '1.05rem', color: 'var(--dark)' }}>
                    {a.title}
                  </span>
                  <span className="badge badge-routine">
                    {a.triage_level}
                  </span>
                  {a.emergency_warning && (
                    <span className="badge badge-emergency">Emergency</span>
                  )}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {new Date(a.created_at).toLocaleString()} • {a.possible_conditions_count} conditions considered
                </div>
                {a.doctor_notes && (
                  <div style={{ fontSize: '0.82rem', color: '#166534', marginTop: '0.4rem' }}>
                    Doctor note: "{a.doctor_notes.slice(0, 90)}..."
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div>
                  {a.doctor_review_status === 'approved' ? (
                    <span className="badge badge-selfcare"><CheckCircle2 size={12} /> Approved</span>
                  ) : (
                    <span className="badge badge-urgent"><Clock size={12} /> Pending</span>
                  )}
                </div>
                <ChevronRight size={18} color="var(--text-muted)" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
