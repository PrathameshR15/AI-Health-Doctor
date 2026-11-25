import React, { useState, useEffect } from 'react';
import { Clock, CheckCircle2, ShieldAlert, FileText, ChevronRight, Stethoscope, AlertOctagon } from 'lucide-react';
import { api } from '../../api';
import SourceBadge from '../../components/SourceBadge';

export default function AIAssessmentReview() {
  const [assessments, setAssessments] = useState([]);
  const [selectedAssessment, setSelectedAssessment] = useState(null);
  const [doctorNotes, setDoctorNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAssessments(filter);
  }, [filter]);

  const loadAssessments = async (status = '') => {
    try {
      const data = await api.getDoctorAssessments(status);
      setAssessments(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = async (id) => {
    try {
      const data = await api.getAssessmentDetail(id);
      setSelectedAssessment(data);
      setDoctorNotes(data.doctor_notes || '');
    } catch (err) {
      alert("Error fetching assessment: " + err.message);
    }
  };

  const handleReviewSubmit = async (status = 'approved') => {
    if (!selectedAssessment) return;
    setSubmitting(true);
    try {
      await api.reviewAssessment(selectedAssessment.id, {
        status: status,
        doctor_notes: doctorNotes || "Clinical assessment reviewed and approved by treating physician."
      });
      alert(`Assessment marked as ${status.toUpperCase()} and signed off in patient chart.`);
      setSelectedAssessment(null);
      loadAssessments(filter);
    } catch (err) {
      alert("Error submitting review: " + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="card-header" style={{ marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 className="card-title" style={{ fontSize: '1.4rem' }}>
            <Stethoscope size={22} color="var(--primary)" /> AI Assessment Reviews
          </h2>
          <p className="card-description">
            Evaluate and sign off on AI symptom assessments, differential considerations, and SOAP summaries.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className={`btn btn-sm ${filter === '' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter('')}
          >
            All Assessments
          </button>
          <button
            className={`btn btn-sm ${filter === 'pending' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter('pending')}
          >
            Pending Review Only
          </button>
          <button
            className={`btn btn-sm ${filter === 'approved' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter('approved')}
          >
            Approved
          </button>
        </div>
      </div>

      {selectedAssessment ? (
        <div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setSelectedAssessment(null)}
            style={{ marginBottom: '1.25rem' }}
          >
            ← Back to Assessment Queue
          </button>

          {/* Assessment Header */}
          <div className="card" style={{ borderLeft: '5px solid #0284c7' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div>
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.4rem' }}>
                  <span className="badge badge-routine">Triage: {selectedAssessment.triage_level}</span>
                  {selectedAssessment.emergency_warning && (
                    <span className="badge badge-emergency">Emergency Red Flag Triggered</span>
                  )}
                </div>
                <h3 style={{ fontSize: '1.3rem', fontWeight: '800' }}>{selectedAssessment.title}</h3>
                <div style={{ fontSize: '0.86rem', color: '#1e293b', marginTop: '0.25rem' }}>
                  <strong>Patient-Reported Chief Complaint:</strong> {selectedAssessment.chief_complaint}
                </div>
                {selectedAssessment.symptoms_summary && (
                  <div style={{ fontSize: '0.84rem', color: '#334155', marginTop: '0.35rem', lineHeight: '1.45' }}>
                    <strong>Reported Symptoms & Details:</strong> {selectedAssessment.symptoms_summary}
                  </div>
                )}
                {selectedAssessment.extracted_entities?.active_symptoms && selectedAssessment.extracted_entities.active_symptoms.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.5rem' }}>
                    {selectedAssessment.extracted_entities.active_symptoms.map((sym, idx) => (
                      <span key={idx} style={{
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        background: '#e0f2fe',
                        color: '#0369a1',
                        padding: '0.2rem 0.6rem',
                        borderRadius: '12px'
                      }}>
                        {sym}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <span className={`badge ${selectedAssessment.doctor_review_status === 'approved' ? 'badge-selfcare' : 'badge-urgent'}`}>
                  {selectedAssessment.doctor_review_status}
                </span>
              </div>
            </div>

            {selectedAssessment.sources && selectedAssessment.sources.length > 0 && (
              <div style={{ marginTop: '0.85rem', paddingTop: '0.6rem', borderTop: '1px solid var(--border)' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginRight: '0.5rem' }}>
                  Referenced Guidelines:
                </span>
                {selectedAssessment.sources.map((s, idx) => (
                  <SourceBadge key={idx} source={s} />
                ))}
              </div>
            )}
          </div>

          {/* Differential Considerations */}
          <div className="card">
            <h4 style={{ fontWeight: '800', marginBottom: '0.75rem' }}>
              AI Differential Considerations:
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {selectedAssessment.possible_conditions?.map((c, i) => (
                <div key={i} style={{ padding: '0.85rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <strong style={{ fontSize: '0.92rem' }}>{c.condition}</strong>
                    <span className="badge badge-routine">{c.likelihood} Likelihood</span>
                  </div>
                  <div style={{ fontSize: '0.84rem', color: '#334155', marginTop: '0.25rem' }}>
                    {c.rationale}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {c.clinical_explanation}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* SOAP Note Review */}
          <div className="card">
            <h4 style={{ fontWeight: '800', marginBottom: '0.75rem' }}>
              Generated Pre-Encounter SOAP Note:
            </h4>
            <div className="soap-box">
              <div className="soap-section">
                <div><span className="soap-letter">S</span> <strong>Subjective</strong></div>
                <p style={{ marginTop: '0.25rem', fontSize: '0.85rem' }}>
                  {typeof selectedAssessment.consultation_summary?.subjective === 'string'
                    ? selectedAssessment.consultation_summary.subjective
                    : JSON.stringify(selectedAssessment.consultation_summary?.subjective)}
                </p>
              </div>
              <div className="soap-section">
                <div><span className="soap-letter">O</span> <strong>Objective</strong></div>
                <p style={{ marginTop: '0.25rem', fontSize: '0.85rem' }}>
                  {typeof selectedAssessment.consultation_summary?.objective === 'string'
                    ? selectedAssessment.consultation_summary.objective
                    : JSON.stringify(selectedAssessment.consultation_summary?.objective)}
                </p>
              </div>
              <div className="soap-section">
                <div><span className="soap-letter">A</span> <strong>Assessment</strong></div>
                <p style={{ marginTop: '0.25rem', fontSize: '0.85rem' }}>
                  {typeof selectedAssessment.consultation_summary?.assessment === 'string'
                    ? selectedAssessment.consultation_summary.assessment
                    : JSON.stringify(selectedAssessment.consultation_summary?.assessment)}
                </p>
              </div>
              <div className="soap-section">
                <div><span className="soap-letter">P</span> <strong>Plan</strong></div>
                <p style={{ marginTop: '0.25rem', fontSize: '0.85rem' }}>
                  {typeof selectedAssessment.consultation_summary?.plan === 'string'
                    ? selectedAssessment.consultation_summary.plan
                    : JSON.stringify(selectedAssessment.consultation_summary?.plan)}
                </p>
              </div>
            </div>
          </div>

          {/* Doctor Sign-off Box */}
          <div className="card" style={{ background: '#f8fafc', border: '2px solid #cbd5e1' }}>
            <h4 style={{ fontWeight: '800', marginBottom: '0.6rem', color: 'var(--dark)' }}>
              Doctor Clinical Sign-Off & Notes
            </h4>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
              Add your clinical observations, recommendations, or adjustments to enter into the patient's EHR chart.
            </p>
            <textarea
              className="form-textarea"
              placeholder="e.g. Assessment reviewed and corroborated. Advised patient to maintain hydration, take temperature log twice daily. Schedule in-person clinic visit if fever exceeds 101F."
              value={doctorNotes}
              onChange={(e) => setDoctorNotes(e.target.value)}
              rows={4}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
              <button
                className="btn btn-secondary"
                onClick={() => handleReviewSubmit('modified')}
                disabled={submitting}
              >
                Mark as Modified
              </button>
              <button
                className="btn btn-primary"
                onClick={() => handleReviewSubmit('approved')}
                disabled={submitting}
              >
                <CheckCircle2 size={16} /> Approve & Sign Off in Patient Chart
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* List View */
        <div className="card">
          {assessments.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem 0' }}>
              No assessments matching current filter.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {assessments.map(a => (
                <div
                  key={a.id}
                  onClick={() => handleSelect(a.id)}
                  style={{
                    padding: '1rem', background: '#f8fafc', borderRadius: '8px',
                    border: '1px solid var(--border)', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    flexWrap: 'wrap', gap: '0.75rem', transition: 'all 0.15s ease'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
                      <span style={{ fontWeight: '700', fontSize: '0.95rem' }}>{a.chief_complaint}</span>
                      <span className={`badge ${a.emergency_warning ? 'badge-emergency' : a.triage_level === 'URGENT' ? 'badge-urgent' : 'badge-routine'}`}>
                        {a.triage_level}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Patient: <strong>{a.patient_name}</strong> • Recorded: {new Date(a.created_at).toLocaleString()}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                    <span className={`badge ${a.doctor_review_status === 'approved' ? 'badge-selfcare' : 'badge-urgent'}`}>
                      {a.doctor_review_status}
                    </span>
                    <ChevronRight size={18} color="var(--text-muted)" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
