import React, { useState, useEffect } from 'react';
import { 
  Users, Search, FileText, ArrowLeft, CheckCircle, 
  AlertTriangle, AlertCircle, Stethoscope, Utensils, 
  MessageSquare, PlusCircle, ShieldAlert, Clock, Pill
} from 'lucide-react';
import { api } from '../../api';
import HealthTimelinePlot from '../../components/HealthTimelinePlot';

export default function PatientManagement({ initialPatientId = null, onSelectPatient, onWriteNote }) {
  const [patients, setPatients] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPatientId, setSelectedPatientId] = useState(initialPatientId);
  const [patientChart, setPatientChart] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeChartTab, setActiveChartTab] = useState('timeline'); // 'timeline', 'consultations', 'reports', 'allergies', 'notes'

  // Form states inside patient chart
  const [reviewNotes, setReviewNotes] = useState({});
  const [submittingReview, setSubmittingReview] = useState(false);
  const [newNoteTitle, setNewNoteTitle] = useState('');
  const [newNoteContent, setNewNoteContent] = useState('');
  const [newNoteType, setNewNoteType] = useState('clinical');
  const [savingNote, setSavingNote] = useState(false);

  useEffect(() => {
    loadPatients();
    if (initialPatientId) {
      openPatientChart(initialPatientId);
    }
  }, [initialPatientId]);

  const loadPatients = async (query = '') => {
    try {
      const data = await api.getDoctorPatients(query);
      setPatients(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    loadPatients(searchTerm);
  };

  const openPatientChart = async (id) => {
    setSelectedPatientId(id);
    setActiveChartTab('consultations');
    try {
      const data = await api.getDoctorPatientDetail(id);
      setPatientChart(data);
    } catch (err) {
      alert("Error loading patient chart: " + err.message);
    }
  };

  const refreshCurrentChart = async () => {
    if (!selectedPatientId) return;
    try {
      const data = await api.getDoctorPatientDetail(selectedPatientId);
      setPatientChart(data);
    } catch (err) {
      console.error("Error refreshing chart:", err);
    }
  };

  const handleApproveAssessment = async (assessmentId) => {
    const noteText = reviewNotes[assessmentId] || "Clinical evaluation verified and approved by attending physician.";
    setSubmittingReview(true);
    try {
      await api.reviewAssessment(assessmentId, {
        status: 'approved',
        doctor_notes: noteText
      });
      alert("Consultation approved and recorded in patient chart!");
      setReviewNotes(prev => ({ ...prev, [assessmentId]: '' }));
      await refreshCurrentChart();
      loadPatients(searchTerm);
    } catch (err) {
      alert("Failed to submit review: " + err.message);
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleCreateNewNote = async (e) => {
    e.preventDefault();
    if (!newNoteTitle.trim() || !newNoteContent.trim()) {
      alert("Please provide both note title and clinical content.");
      return;
    }
    setSavingNote(true);
    try {
      await api.createDoctorNote({
        patient_id: selectedPatientId,
        title: newNoteTitle.trim(),
        content: newNoteContent.trim(),
        note_type: newNoteType
      });
      setNewNoteTitle('');
      setNewNoteContent('');
      alert("Clinical note saved to patient chart!");
      await refreshCurrentChart();
    } catch (err) {
      alert("Failed to save note: " + err.message);
    } finally {
      setSavingNote(false);
    }
  };

  // --- PATIENT CHART VIEW ---
  if (selectedPatientId && patientChart) {
    const { patient, assessments = [], reports = [], allergies = [], notes = [], timeline = [] } = patientChart;

    return (
      <div>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => { setSelectedPatientId(null); setPatientChart(null); }}
          style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
        >
          <ArrowLeft size={16} /> Back to Patient Roster
        </button>

        {/* 1. Patient Summary Header Card */}
        <div className="card" style={{ borderLeft: '5px solid var(--primary)', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <h2 style={{ fontSize: '1.45rem', fontWeight: '800', margin: 0, color: 'var(--dark)' }}>
                  {patient.full_name}
                </h2>
                <span className="badge badge-routine" style={{ fontSize: '0.75rem' }}>
                  Patient ID: #{patient.id}
                </span>
              </div>
              <div style={{ fontSize: '0.86rem', color: '#475569', marginTop: '0.35rem' }}>
                {patient.gender || 'Adult'} • DOB: {patient.dob || 'Unspecified'} • Blood Group: <strong style={{ color: 'var(--dark)' }}>{patient.blood_group || 'O+'}</strong>
              </div>
              <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                Email: {patient.email} • Phone: {patient.phone || 'N/A'}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span className={`badge ${patient.ai_consent_given ? 'badge-routine' : 'badge-warning'}`}>
                AI Consent: {patient.ai_consent_given ? "Active" : "Not Provided"}
              </span>
            </div>
          </div>

          {/* Quick Clinical Info Row */}
          <div className="grid-3" style={{ marginTop: '1rem', paddingTop: '0.85rem', borderTop: '1px solid var(--border)', fontSize: '0.86rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.78rem' }}>Chronic Conditions:</span>
              <strong style={{ color: 'var(--dark)' }}>{patient.chronic_conditions || 'None reported'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.78rem' }}>Recorded Allergies:</span>
              <strong style={{ color: allergies.length > 0 ? '#dc2626' : 'var(--dark)' }}>
                {allergies.map(a => a.allergen).join(', ') || 'No recorded allergies'}
              </strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.78rem' }}>Current Medications:</span>
              <strong style={{ color: 'var(--dark)' }}>{patient.current_medications || 'None recorded'}</strong>
            </div>
          </div>
        </div>

        {/* 2. Patient Chart Navigation Tabs (Simple & Unbloated) */}
        <div style={{
          display: 'flex', gap: '0.5rem', borderBottom: '2px solid var(--border)',
          marginBottom: '1.25rem', overflowX: 'auto', paddingBottom: '0.2rem'
        }}>
          {[
            { id: 'timeline', label: `⏱️ Health Timeline (${timeline.length})`, icon: <Clock size={16} /> },
            { id: 'consultations', label: `AI Consultations (${assessments.length})`, icon: <Stethoscope size={16} /> },
            { id: 'reports', label: `Lab & Medical Reports (${reports.length})`, icon: <FileText size={16} /> },
            { id: 'allergies', label: `Allergies & Diet (${allergies.length})`, icon: <Utensils size={16} /> },
            { id: 'notes', label: `Clinical Notes (${notes.length})`, icon: <MessageSquare size={16} /> },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveChartTab(tab.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.45rem',
                padding: '0.65rem 1rem', fontSize: '0.88rem', fontWeight: '700',
                background: activeChartTab === tab.id ? '#ffffff' : 'transparent',
                color: activeChartTab === tab.id ? 'var(--primary)' : 'var(--text-muted)',
                border: 'none',
                borderBottom: activeChartTab === tab.id ? '3px solid var(--primary)' : '3px solid transparent',
                borderRadius: '6px 6px 0 0',
                cursor: 'pointer',
                whiteSpace: 'nowrap'
              }}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* --- TAB 0: HEALTH TIMELINE --- */}
        {activeChartTab === 'timeline' && (
          <div>
            {/* Visual Time-Axis Graph Plot */}
            <HealthTimelinePlot events={timeline} />

            <div className="card">
              <div className="card-header" style={{ marginBottom: '1rem' }}>
                <h3 className="card-title" style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Clock size={18} color="var(--primary)" /> Patient Health Timeline Events ({timeline.length})
                </h3>
                <p className="card-description" style={{ margin: 0 }}>
                  Chronological sequence of treatments started, AI assessments (2 words), and lab report analyses (3 words).
                </p>
              </div>

            {timeline.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', textAlign: 'center', padding: '2rem 0' }}>
                No events recorded in the health timeline for Patient #{patient.id} yet.
              </p>
            ) : (
              <div className="timeline" style={{ paddingLeft: '0.5rem' }}>
                {timeline.map((item) => {
                  const isAssessment = item.event_type === 'ai_assessment';
                  const isReport = item.event_type === 'report_analysis';
                  const isTreatment = item.event_type === 'treatment_started';

                  let borderAccent = 'var(--primary)';
                  let bgAccent = '#f8fafc';
                  let badgeColor = '#0284c7';
                  let badgeBg = '#e0f2fe';
                  let icon = <Clock size={16} />;

                  if (isAssessment) {
                    borderAccent = '#8b5cf6';
                    bgAccent = '#faf5ff';
                    badgeColor = '#6d28d9';
                    badgeBg = '#ede9fe';
                    icon = <Stethoscope size={16} color="#7c3aed" />;
                  } else if (isReport) {
                    borderAccent = '#0d9488';
                    bgAccent = '#f0fdfa';
                    badgeColor = '#0f766e';
                    badgeBg = '#ccfbf1';
                    icon = <FileText size={16} color="#0d9488" />;
                  } else if (isTreatment) {
                    borderAccent = '#16a34a';
                    bgAccent = '#f0fdf4';
                    badgeColor = '#15803d';
                    badgeBg = '#dcfce7';
                    icon = <Pill size={16} color="#16a34a" />;
                  }

                  return (
                    <div key={item.id} className="timeline-item" style={{ marginBottom: '1.25rem' }}>
                      <div className="timeline-dot" style={{ background: borderAccent }} />
                      <div style={{
                        padding: '1rem 1.2rem',
                        background: bgAccent,
                        borderRadius: '10px',
                        border: '1px solid var(--border)',
                        borderLeft: `5px solid ${borderAccent}`,
                        boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            {icon}
                            <strong style={{ fontSize: '0.96rem', color: 'var(--dark)' }}>
                              {item.event_label}
                            </strong>
                          </div>
                          <span style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: '600' }}>
                            📅 {item.date_time}
                          </span>
                        </div>

                        {item.highlight && (
                          <div style={{ marginTop: '0.6rem', marginBottom: '0.45rem' }}>
                            <span style={{
                              display: 'inline-block',
                              padding: '0.28rem 0.75rem',
                              borderRadius: '20px',
                              background: badgeBg,
                              color: badgeColor,
                              fontWeight: '800',
                              fontSize: '0.88rem',
                              border: `1px solid ${borderAccent}40`
                            }}>
                              {isAssessment && '🎯 Assessment: '}
                              {isReport && '🔬 Report: '}
                              {isTreatment && '💊 Treatment: '}
                              {item.highlight}
                            </span>
                          </div>
                        )}

                        <p style={{ fontSize: '0.85rem', color: '#334155', margin: '0.35rem 0 0 0', lineHeight: '1.45' }}>
                          {item.summary}
                        </p>

                        {item.details && (
                          <div style={{
                            marginTop: '0.5rem',
                            padding: '0.5rem 0.75rem',
                            background: '#ffffff',
                            borderRadius: '6px',
                            border: '1px solid rgba(0,0,0,0.06)',
                            fontSize: '0.8rem',
                            color: '#475569'
                          }}>
                            {item.details}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            </div>
          </div>
        )}

        {/* --- TAB 1: AI CONSULTATIONS & ASSESSMENTS --- */}
        {activeChartTab === 'consultations' && (
          <div className="card">
            <div className="card-header" style={{ marginBottom: '1rem' }}>
              <h3 className="card-title" style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Stethoscope size={18} color="var(--primary)" /> AI Virtual Doctor Consultations ({assessments.length})
              </h3>
            </div>

            {assessments.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', textAlign: 'center', padding: '2rem 0' }}>
                No consultations or symptom assessments recorded for Patient #{patient.id} yet.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {assessments.map(a => {
                  const isApproved = a.doctor_review_status === 'approved';
                  return (
                    <div key={a.id} style={{
                      padding: '1.1rem', background: '#f8fafc', borderRadius: '8px',
                      border: '1px solid var(--border)', borderLeft: isApproved ? '4px solid #10b981' : '4px solid #f59e0b'
                    }}>
                      {/* Title & Status */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                        <div>
                          <strong style={{ fontSize: '1rem', color: 'var(--dark)' }}>
                            {a.title || a.chief_complaint}
                          </strong>
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                            Visit Date: {new Date(a.created_at).toLocaleString()} • Triage: <span style={{ fontWeight: '700', textTransform: 'uppercase' }}>{a.triage_level}</span>
                            {a.emergency_warning && <span className="badge badge-emergency" style={{ marginLeft: '0.5rem' }}>🚨 Warning Signs Active</span>}
                          </div>
                        </div>

                        <span className={`badge ${isApproved ? 'badge-routine' : 'badge-warning'}`} style={{ fontSize: '0.78rem' }}>
                          {isApproved ? '✓ Doctor Approved' : '⏳ Pending Doctor Review'}
                        </span>
                      </div>

                      {/* Patient-Reported Symptoms & Dialogue Summary */}
                      <div style={{
                        marginTop: '0.7rem',
                        padding: '0.75rem 0.9rem',
                        background: '#ffffff',
                        borderRadius: '6px',
                        border: '1px solid #e2e8f0',
                        borderLeft: '3px solid #0284c7'
                      }}>
                        <div style={{ fontSize: '0.82rem', fontWeight: '700', color: '#0369a1', marginBottom: '0.3rem' }}>
                          🩺 Patient-Reported Symptoms:
                        </div>
                        {a.chief_complaint && (
                          <div style={{ fontSize: '0.85rem', color: '#1e293b', marginBottom: '0.25rem' }}>
                            <strong>Chief Complaint:</strong> {a.chief_complaint}
                          </div>
                        )}
                        {a.symptoms_summary && (
                          <div style={{ fontSize: '0.84rem', color: '#334155', lineHeight: '1.45' }}>
                            <strong>Details / Dialogue:</strong> {a.symptoms_summary}
                          </div>
                        )}
                        {a.extracted_entities?.active_symptoms && a.extracted_entities.active_symptoms.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.45rem' }}>
                            {a.extracted_entities.active_symptoms.map((sym, idx) => (
                              <span key={idx} style={{
                                fontSize: '0.75rem',
                                fontWeight: '600',
                                background: '#e0f2fe',
                                color: '#0369a1',
                                padding: '0.18rem 0.55rem',
                                borderRadius: '12px'
                              }}>
                                {sym}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Suspected Conditions / Differentials */}
                      {a.possible_conditions && a.possible_conditions.length > 0 && (
                        <div style={{ marginTop: '0.65rem' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#475569' }}>
                            Differential Diagnoses Identified:
                          </span>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.3rem' }}>
                            {a.possible_conditions.map((c, idx) => (
                              <span key={idx} className="badge badge-routine" style={{ fontSize: '0.76rem' }}>
                                {c.condition || c.name || c} ({c.likelihood || 'Review'})
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Doctor Review / Approval Action */}
                      <div style={{
                        marginTop: '0.9rem', paddingTop: '0.75rem', borderTop: '1px solid #e2e8f0',
                        background: '#ffffff', padding: '0.75rem', borderRadius: '6px'
                      }}>
                        {isApproved ? (
                          <div style={{ fontSize: '0.84rem', color: '#166534' }}>
                            <strong>✓ Attending Physician Sign-Off:</strong> {a.doctor_notes || "Clinical findings approved."}
                          </div>
                        ) : (
                          <div>
                            <div style={{ fontSize: '0.82rem', fontWeight: '700', color: '#92400e', marginBottom: '0.35rem' }}>
                              ✍️ Physician Review & Approval:
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                              <input
                                type="text"
                                className="form-input"
                                placeholder="Enter clinical notes, dosage instructions, or recommendations..."
                                value={reviewNotes[a.id] || ''}
                                onChange={(e) => setReviewNotes({ ...reviewNotes, [a.id]: e.target.value })}
                                style={{ flex: 1, minWidth: '220px', fontSize: '0.85rem' }}
                              />
                              <button
                                className="btn btn-sm btn-primary"
                                onClick={() => handleApproveAssessment(a.id)}
                                disabled={submittingReview}
                                style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}
                              >
                                <CheckCircle size={14} /> Approve & Sign Off
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* --- TAB 2: LAB & MEDICAL REPORTS --- */}
        {activeChartTab === 'reports' && (
          <div className="card">
            <div className="card-header" style={{ marginBottom: '1rem' }}>
              <h3 className="card-title" style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileText size={18} color="var(--primary)" /> Medical Reports & Diagnostic Files ({reports.length})
              </h3>
            </div>

            {reports.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', textAlign: 'center', padding: '2rem 0' }}>
                No lab reports or documents uploaded for Patient #{patient.id} yet.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {reports.map(r => (
                  <div key={r.id} style={{
                    padding: '1.1rem', background: '#f8fafc', borderRadius: '8px',
                    border: '1px solid var(--border)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div>
                        <div style={{ fontWeight: '800', fontSize: '0.98rem', color: 'var(--dark)' }}>
                          {r.file_name}
                        </div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                          Type: {r.file_type?.toUpperCase()} • Uploaded: {new Date(r.uploaded_at).toLocaleString()}
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                        <span className={`badge ${r.doctor_review_status === 'approved' ? 'badge-routine' : 'badge-warning'}`} style={{ fontSize: '0.74rem' }}>
                          {r.doctor_review_status === 'approved' ? '✓ Approved' : '⏳ Pending Review'}
                        </span>
                        {r.has_abnormalities && (
                          <span className="badge badge-emergency" style={{ fontSize: '0.74rem' }}>
                            ⚠️ Abnormal Findings
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Prescribed Medicines Explained (if Prescription) */}
                    {r.medications && r.medications.length > 0 && (
                      <div style={{
                        background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '6px',
                        padding: '0.75rem', marginTop: '0.75rem'
                      }}>
                        <div style={{ fontWeight: '700', fontSize: '0.84rem', color: '#0369a1', marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <Pill size={15} color="#0284c7" /> Prescribed Medicines ({r.medications.length}):
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                          {r.medications.map((med, idx) => (
                            <div key={idx} style={{ fontSize: '0.82rem', color: '#334155', background: '#ffffff', padding: '0.5rem 0.65rem', borderRadius: '4px', border: '1px solid #e0f2fe' }}>
                              <div style={{ fontWeight: '700', color: '#0369a1' }}>💊 {med.medicine_name}</div>
                              <div><strong>What it is:</strong> {med.what_it_is}</div>
                              <div><strong>What it is for:</strong> {med.what_it_is_for}</div>
                              <div><strong>Why prescribed:</strong> {med.why_prescribed}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* What is Abnormal Box */}
                    {r.abnormal_findings && r.abnormal_findings.length > 0 && (
                      <div style={{
                        background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px',
                        padding: '0.75rem', marginTop: '0.75rem'
                      }}>
                        <div style={{ fontWeight: '700', fontSize: '0.84rem', color: '#991b1b', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <AlertCircle size={15} color="#dc2626" /> Abnormal Parameters Detected ({r.abnormal_findings.length}):
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                          {r.abnormal_findings.map((abn, idx) => (
                            <div key={idx} style={{ fontSize: '0.82rem', color: '#7f1d1d' }}>
                              • <strong>{abn.finding}</strong>: <span style={{ fontWeight: '700' }}>{abn.patient_value}</span> ({abn.status}) [Normal: {abn.normal_range}]
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Relevant Conclusion */}
                    {r.relevant_conclusion && (
                      <div style={{
                        background: '#faf5ff', border: '1px solid #e9d5ff', borderRadius: '6px',
                        padding: '0.75rem', marginTop: '0.65rem', fontSize: '0.85rem', color: '#581c87'
                      }}>
                        <strong>Clinical Conclusion:</strong> {r.relevant_conclusion}
                      </div>
                    )}

                    {/* Doctor Notes if Present */}
                    {r.doctor_notes && (
                      <div style={{ fontSize: '0.82rem', color: '#166534', marginTop: '0.5rem', background: '#f0fdf4', padding: '0.4rem 0.6rem', borderRadius: '4px' }}>
                        <strong>Doctor Notes:</strong> {r.doctor_notes}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* --- TAB 3: ALLERGIES & DIET --- */}
        {activeChartTab === 'allergies' && (
          <div className="card">
            <div className="card-header" style={{ marginBottom: '1rem' }}>
              <h3 className="card-title" style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Utensils size={18} color="var(--primary)" /> Patient Allergies & Dietary Restrictions ({allergies.length})
              </h3>
            </div>

            {allergies.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', textAlign: 'center', padding: '2rem 0' }}>
                No allergies or dietary records registered for Patient #{patient.id}.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {allergies.map(al => (
                  <div key={al.id} style={{
                    padding: '0.9rem', background: '#ffffff', borderRadius: '8px',
                    border: '1px solid var(--border)', borderLeft: '4px solid #ef4444'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong style={{ fontSize: '0.94rem', color: '#dc2626' }}>{al.allergen}</strong>
                      <span className="badge badge-emergency" style={{ fontSize: '0.72rem' }}>
                        {al.severity?.toUpperCase() || 'MILD'}
                      </span>
                    </div>
                    {al.reaction && (
                      <div style={{ fontSize: '0.82rem', color: '#475569', marginTop: '0.2rem' }}>
                        Reaction: {al.reaction}
                      </div>
                    )}
                    {al.foods_to_avoid && al.foods_to_avoid.length > 0 && (
                      <div style={{ fontSize: '0.82rem', color: '#b91c1c', marginTop: '0.35rem' }}>
                        <strong>Avoid:</strong> {al.foods_to_avoid.join(', ')}
                      </div>
                    )}
                    {al.recommended_foods && al.recommended_foods.length > 0 && (
                      <div style={{ fontSize: '0.82rem', color: '#166534', marginTop: '0.2rem' }}>
                        <strong>Safe Alternatives:</strong> {al.recommended_foods.join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* --- TAB 4: CLINICAL NOTES & ADD NOTE --- */}
        {activeChartTab === 'notes' && (
          <div>
            {/* Add Clinical Note Form */}
            <form onSubmit={handleCreateNewNote} className="card" style={{ marginBottom: '1.25rem', borderLeft: '4px solid var(--primary)' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: '800', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <PlusCircle size={18} color="var(--primary)" /> Add Clinical Note to Patient Chart
              </h3>

              <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Note title (e.g. Follow-up plan, In-person exam, Prescription note)..."
                  value={newNoteTitle}
                  onChange={(e) => setNewNoteTitle(e.target.value)}
                  style={{ flex: 2, minWidth: '220px' }}
                  required
                />
                <select
                  className="form-select"
                  value={newNoteType}
                  onChange={(e) => setNewNoteType(e.target.value)}
                  style={{ flex: 1, minWidth: '140px' }}
                >
                  <option value="clinical">Clinical Examination</option>
                  <option value="prescription">Prescription / Medication</option>
                  <option value="progress">Progress Note</option>
                  <option value="consultation">Consultation Review</option>
                </select>
              </div>

              <textarea
                className="form-textarea"
                rows={3}
                placeholder="Write detailed clinical impression, recommendations, or treatment instructions..."
                value={newNoteContent}
                onChange={(e) => setNewNoteContent(e.target.value)}
                style={{ marginBottom: '0.75rem' }}
                required
              />

              <button
                type="submit"
                className="btn btn-primary btn-sm"
                disabled={savingNote}
                style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
              >
                <PlusCircle size={15} /> {savingNote ? "Saving..." : "Save Note to Patient Chart"}
              </button>
            </form>

            {/* Existing Notes List */}
            <div className="card">
              <div className="card-header" style={{ marginBottom: '1rem' }}>
                <h3 className="card-title" style={{ fontSize: '1.15rem' }}>
                  Recorded Clinical Notes in Chart ({notes.length})
                </h3>
              </div>

              {notes.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', textAlign: 'center', padding: '1.5rem 0' }}>
                  No doctor clinical notes recorded yet for Patient #{patient.id}.
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {notes.map(n => (
                    <div key={n.id} style={{ padding: '0.9rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <strong style={{ fontSize: '0.94rem', color: 'var(--dark)' }}>{n.title}</strong>
                        <span className="badge badge-routine" style={{ fontSize: '0.72rem' }}>{n.note_type}</span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '0.2rem 0 0.4rem' }}>
                        {new Date(n.created_at).toLocaleString()}
                      </div>
                      <p style={{ fontSize: '0.86rem', color: '#334155', whiteSpace: 'pre-wrap', margin: 0, lineHeight: '1.5' }}>
                        {n.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  // --- PATIENTS ROSTER LIST VIEW ---
  return (
    <div>
      <div className="card-header" style={{ marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 className="card-title" style={{ fontSize: '1.4rem' }}>
            <Users size={22} color="var(--primary)" /> Patient Management
          </h2>
          <p className="card-description">
            Search patient records, view complete clinical histories, and review charts.
          </p>
        </div>

        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            className="form-input"
            placeholder="Search by name or email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: '240px' }}
          />
          <button type="submit" className="btn btn-secondary">
            <Search size={16} />
          </button>
        </form>
      </div>

      <div className="card">
        {loading ? (
          <p style={{ textAlign: 'center', padding: '2rem 0', color: 'var(--text-muted)' }}>
            Loading patient records...
          </p>
        ) : patients.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem 0' }}>
            No patients found matching your search.
          </p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
              <thead>
                <tr style={{ background: '#f8fafc', textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                  <th style={{ padding: '0.75rem 1rem' }}>Patient Name</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Contact</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Chronic Conditions</th>
                  <th style={{ padding: '0.75rem 1rem' }}>AI Consultations</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Lab Reports</th>
                  <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {patients.map(p => (
                  <tr key={p.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '0.75rem 1rem', fontWeight: '700' }}>
                      <div style={{ color: 'var(--dark)' }}>{p.full_name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        ID #{p.id} • {p.gender || 'Patient'} • {p.blood_group || 'O+'}
                      </div>
                    </td>
                    <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)' }}>
                      <div>{p.email}</div>
                      <div style={{ fontSize: '0.75rem' }}>{p.phone || 'N/A'}</div>
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      {p.chronic_conditions || 'None reported'}
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <span className="badge badge-routine">{p.assessments_count} Consultations</span>
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <span className="badge badge-routine">{p.reports_count} Reports</span>
                    </td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={() => openPatientChart(p.id)}
                      >
                        Open Chart
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
