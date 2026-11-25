import React, { useState, useEffect } from 'react';
import { FileText, Eye, FileCode, CheckCircle, AlertCircle, UserCheck } from 'lucide-react';
import { api } from '../../api';

export default function MedicalRecordAnalysisView() {
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [viewingFhir, setViewingFhir] = useState(null);
  const [loading, setLoading] = useState(true);
  const [doctorNotes, setDoctorNotes] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      const data = await api.getReports();
      setReports(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const inspectReport = async (id) => {
    try {
      const detail = await api.getReportDetail(id);
      setSelectedReport(detail);
      setDoctorNotes(detail.doctor_notes || '');
    } catch (err) {
      alert("Error loading report detail: " + err.message);
    }
  };

  const handleApproveReport = async (status = 'approved') => {
    if (!selectedReport || !selectedReport.assessment_id) {
      alert("No linked assessment record found for this report.");
      return;
    }
    setSubmittingReview(true);
    try {
      await api.reviewAssessment(selectedReport.assessment_id, {
        status: status,
        doctor_notes: doctorNotes || "Report findings and clinical parameters verified by attending physician."
      });
      alert(`Report marked as ${status.toUpperCase()}! Doctor note recorded in patient chart.`);
      inspectReport(selectedReport.id);
      loadReports();
    } catch (err) {
      alert("Review submission failed: " + err.message);
    } finally {
      setSubmittingReview(false);
    }
  };

  return (
    <div>
      <div className="card-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h2 className="card-title" style={{ fontSize: '1.4rem' }}>
            <FileText size={22} color="var(--primary)" /> Medical Record Analysis
          </h2>
          <p className="card-description">
            Physician analysis of uploaded lab panels, abnormal findings, radiology records, and HL7 FHIR DiagnosticReports.
          </p>
        </div>
      </div>

      {selectedReport ? (
        <div>
          <button className="btn btn-secondary btn-sm" onClick={() => setSelectedReport(null)} style={{ marginBottom: '1.25rem' }}>
            ← Back to Reports
          </button>

          <div className="card" style={{ borderLeft: '4px solid var(--primary)', background: '#ffffff' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--dark)' }}>{selectedReport.file_name}</h3>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  Patient ID: #{selectedReport.patient_id} • Uploaded: {new Date(selectedReport.uploaded_at).toLocaleString()}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span className={`badge ${selectedReport.doctor_review_status === 'approved' ? 'badge-routine' : 'badge-warning'}`}>
                  {selectedReport.doctor_review_status === 'approved' ? '✓ Doctor Approved' : '⏳ Pending Review'}
                </span>
                <button className="btn btn-sm btn-secondary" onClick={() => setViewingFhir(selectedReport.fhir_bundle)}>
                  <FileCode size={14} /> View FHIR JSON
                </button>
              </div>
            </div>

            {/* 1. Short Analysis */}
            {selectedReport.short_analysis && (
              <div style={{ background: '#f8fafc', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '1rem', fontSize: '0.88rem' }}>
                <strong style={{ color: 'var(--dark)', display: 'block', marginBottom: '0.2rem' }}>🔍 Short Analysis:</strong>
                {selectedReport.short_analysis}
              </div>
            )}

            {/* 2. WHAT IS ABNORMAL (Prominently Highlighted for Doctor) */}
            {selectedReport.abnormal_findings && selectedReport.abnormal_findings.length > 0 ? (
              <div style={{
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderLeft: '4px solid #ef4444',
                borderRadius: '8px',
                padding: '1rem',
                marginBottom: '1rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.6rem' }}>
                  <AlertCircle size={20} color="#dc2626" />
                  <h4 style={{ margin: 0, fontSize: '0.98rem', fontWeight: '800', color: '#991b1b' }}>
                    Abnormal Findings & Critical Parameters ({selectedReport.abnormal_findings.length})
                  </h4>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {selectedReport.abnormal_findings.map((abn, i) => (
                    <div key={i} style={{
                      background: '#ffffff',
                      padding: '0.75rem 0.9rem',
                      borderRadius: '6px',
                      border: '1px solid #fee2e2',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: '0.5rem'
                    }}>
                      <div>
                        <div style={{ fontWeight: '700', fontSize: '0.9rem', color: '#1e293b' }}>
                          {abn.finding}
                        </div>
                        <div style={{ fontSize: '0.82rem', color: '#475569', marginTop: '0.15rem' }}>
                          Patient Value: <strong style={{ color: '#dc2626' }}>{abn.patient_value}</strong> • Reference Interval: {abn.normal_range}
                        </div>
                        {abn.explanation && (
                          <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.15rem' }}>
                            {abn.explanation}
                          </div>
                        )}
                      </div>
                      <span className="badge badge-emergency" style={{ fontSize: '0.75rem', fontWeight: '700' }}>
                        {abn.status || "Abnormal"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{
                background: '#f0fdf4',
                border: '1px solid #bbf7d0',
                borderLeft: '4px solid #10b981',
                borderRadius: '8px',
                padding: '0.85rem 1rem',
                marginBottom: '1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem'
              }}>
                <CheckCircle size={20} color="#166534" />
                <div>
                  <strong style={{ color: '#166534', fontSize: '0.92rem' }}>All Evaluated Parameters Within Normal Limits</strong>
                  <div style={{ fontSize: '0.82rem', color: '#14532d', marginTop: '0.15rem' }}>
                    No biological reference range outliers were detected in this document.
                  </div>
                </div>
              </div>
            )}

            {/* 3. RELEVANT CONCLUSION */}
            {selectedReport.relevant_conclusion && (
              <div style={{
                background: '#faf5ff',
                border: '1px solid #e9d5ff',
                borderLeft: '4px solid #8b5cf6',
                borderRadius: '8px',
                padding: '1rem',
                marginBottom: '1.25rem'
              }}>
                <h4 style={{ margin: 0, fontSize: '0.96rem', fontWeight: '800', color: '#6b21a8', marginBottom: '0.35rem' }}>
                  📋 Relevant Clinical Conclusion:
                </h4>
                <p style={{ margin: 0, fontSize: '0.88rem', color: '#4c1d95', lineHeight: '1.55' }}>
                  {selectedReport.relevant_conclusion}
                </p>
              </div>
            )}

            {/* 4. Full Extracted Parameters */}
            <h4 style={{ fontWeight: '700', fontSize: '0.95rem', marginBottom: '0.5rem', color: 'var(--dark)' }}>
              All Extracted Parameters & Reference Ranges:
            </h4>
            <div style={{ overflowX: 'auto', marginBottom: '1.5rem' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.86rem' }}>
                <thead>
                  <tr style={{ background: '#f1f5f9', textAlign: 'left' }}>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Parameter</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Patient Value</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Normal Range</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Status</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Clinical Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedReport.clinical_findings?.map((f, i) => {
                    const isAbn = f.status === 'High' || f.status === 'Low' || f.status === 'Abnormal';
                    return (
                      <tr key={i} style={{ borderBottom: '1px solid #e2e8f0', background: isAbn ? '#fff7f7' : '#ffffff' }}>
                        <td style={{ padding: '0.6rem 0.8rem', fontWeight: '700' }}>{f.finding}</td>
                        <td style={{ padding: '0.6rem 0.8rem', fontWeight: '700', color: isAbn ? '#dc2626' : 'var(--primary)' }}>
                          {f.patient_value}
                        </td>
                        <td style={{ padding: '0.6rem 0.8rem', color: 'var(--text-muted)' }}>{f.normal_range}</td>
                        <td style={{ padding: '0.6rem 0.8rem' }}>
                          <span className={`badge ${isAbn ? 'badge-emergency' : 'badge-routine'}`} style={{ fontSize: '0.72rem' }}>
                            {f.status || 'Normal'}
                          </span>
                        </td>
                        <td style={{ padding: '0.6rem 0.8rem', fontSize: '0.82rem', color: '#334155' }}>{f.explanation}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* 5. Doctor Review & Sign-Off Section */}
            <div style={{ background: '#f8fafc', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
              <h4 style={{ fontSize: '0.96rem', fontWeight: '800', marginBottom: '0.5rem', color: 'var(--dark)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <UserCheck size={18} color="var(--primary)" /> Attending Physician Verification & Clinical Notes:
              </h4>
              <textarea
                className="form-textarea"
                rows={3}
                placeholder="Enter clinical notes, prescribed follow-up, or diagnostic impression..."
                value={doctorNotes}
                onChange={(e) => setDoctorNotes(e.target.value)}
                style={{ marginBottom: '0.75rem', fontSize: '0.88rem' }}
              />
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <button
                  className="btn btn-primary"
                  onClick={() => handleApproveReport('approved')}
                  disabled={submittingReview}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  <CheckCircle size={15} /> {submittingReview ? "Submitting..." : "Approve & Record Clinical Note"}
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => handleApproveReport('reviewed')}
                  disabled={submittingReview}
                >
                  Mark as Reviewed (Needs Follow-up)
                </button>
              </div>
            </div>

            <h4 style={{ fontWeight: '700', fontSize: '0.9rem', margin: '1.25rem 0 0.4rem', color: 'var(--text-muted)' }}>
              Raw Extracted Document Text:
            </h4>
            <pre style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '6px', fontSize: '0.78rem', maxHeight: '180px', overflowY: 'auto' }}>
              {selectedReport.extracted_text}
            </pre>
          </div>
        </div>
      ) : (
        <div className="card">
          {reports.length === 0 ? (
            <p style={{ textAlign: 'center', padding: '2rem 0', color: 'var(--text-muted)' }}>
              No medical reports uploaded yet.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {reports.map(r => (
                <div key={r.id} style={{
                  padding: '1rem', background: '#f8fafc', borderRadius: '8px',
                  border: '1px solid var(--border)', display: 'flex', alignItems: 'center',
                  justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem'
                }}>
                  <div style={{ flex: 1, minWidth: '240px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <div style={{ fontWeight: '700', fontSize: '0.92rem' }}>{r.file_name}</div>
                      <span className={`badge ${r.doctor_review_status === 'approved' ? 'badge-routine' : 'badge-warning'}`} style={{ fontSize: '0.72rem' }}>
                        {r.doctor_review_status === 'approved' ? '✓ Approved' : '⏳ Pending Review'}
                      </span>
                      {r.has_abnormalities && (
                        <span className="badge badge-emergency" style={{ fontSize: '0.72rem' }}>
                          ⚠️ Abnormal Parameters
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                      Type: {r.file_type.toUpperCase()} • {(r.file_size_bytes / 1024).toFixed(1)} KB • Uploaded: {new Date(r.uploaded_at).toLocaleString()}
                    </div>
                    {r.relevant_conclusion && (
                      <div style={{ fontSize: '0.82rem', color: '#475569', marginTop: '0.25rem' }}>
                        <strong>Conclusion:</strong> {r.relevant_conclusion.slice(0, 120)}...
                      </div>
                    )}
                  </div>
                  <button className="btn btn-sm btn-primary" onClick={() => inspectReport(r.id)}>
                    <Eye size={14} /> Review Findings
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {viewingFhir && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="card-header">
              <h3 className="card-title">HL7 FHIR DiagnosticReport</h3>
              <button className="btn btn-sm btn-secondary" onClick={() => setViewingFhir(null)}>Close</button>
            </div>
            <pre style={{ background: '#0f172a', color: '#38bdf8', padding: '1rem', borderRadius: '8px', overflowX: 'auto', fontSize: '0.78rem', maxHeight: '450px' }}>
              {JSON.stringify(viewingFhir, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
