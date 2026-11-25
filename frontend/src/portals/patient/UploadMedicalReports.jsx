import React, { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle, FileCode, AlertCircle, Eye } from 'lucide-react';
import { api } from '../../api';

export default function UploadMedicalReports() {
  const [reports, setReports] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [viewingFhir, setViewingFhir] = useState(null);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      const data = await api.getReports();
      setReports(data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setAnalysisResult(null);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await api.uploadReport(formData);
      setAnalysisResult(res);
      setSelectedFile(null);
      loadReports();
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <div className="card-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h2 className="card-title" style={{ fontSize: '1.4rem' }}>
            <Upload size={22} color="var(--primary)" /> Medical Report Analysis
          </h2>
          <p className="card-description">
            Upload blood work, lab panels, radiology PDFs, scans, or FHIR JSON records.
          </p>
        </div>
      </div>

      {/* Upload Box */}
      <form onSubmit={handleUpload} className="card">
        <div style={{
          border: '2px dashed var(--border)',
          borderRadius: 'var(--radius)',
          padding: '2rem',
          textAlign: 'center',
          background: '#f8fafc',
          cursor: 'pointer',
          marginBottom: '1rem'
        }}>
          <input
            type="file"
            id="fileInput"
            accept=".pdf,.png,.jpg,.jpeg,.json,.txt"
            onChange={(e) => setSelectedFile(e.target.files[0])}
            style={{ display: 'none' }}
          />
          <label htmlFor="fileInput" style={{ cursor: 'pointer' }}>
            <div style={{
              width: '50px', height: '50px', borderRadius: '50%', background: 'var(--primary-light)',
              color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 1rem'
            }}>
              <Upload size={24} />
            </div>
            <div style={{ fontWeight: '700', fontSize: '1rem', color: 'var(--dark)' }}>
              {selectedFile ? selectedFile.name : "Click to select or drag a medical document"}
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Supported formats: PDF, PNG, JPG, JSON (HL7 FHIR Bundle), TXT (Max 20MB)
            </p>
          </label>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          style={{ width: '100%', padding: '0.75rem' }}
          disabled={!selectedFile || uploading}
        >
          {uploading ? "Extracting Text & Analyzing Findings with MedSpaCy..." : "Upload & Analyze Medical Report"}
        </button>
      </form>

      {/* Analysis Output */}
      {analysisResult && (
        <div className="card" style={{ borderLeft: '4px solid var(--primary)', background: '#ffffff', marginBottom: '1.5rem' }}>
          {/* Doctor Portal Submission Banner */}
          <div style={{
            background: '#eff6ff',
            border: '1px solid #bfdbfe',
            borderRadius: '8px',
            padding: '0.85rem 1rem',
            marginBottom: '1.25rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '0.75rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <CheckCircle size={22} color="#2563eb" />
              <div>
                <div style={{ fontWeight: '700', fontSize: '0.94rem', color: '#1e40af' }}>
                  ✓ Saved to Doctor Portal for Review
                </div>
                <div style={{ fontSize: '0.82rem', color: '#475569' }}>
                  Report analysis and conclusion are stored in your chart. Treating physicians can review and sign off.
                </div>
              </div>
            </div>
            <span className="badge badge-warning" style={{ fontSize: '0.78rem' }}>
              ⏳ Doctor Review: Pending
            </span>
          </div>

          <div className="card-header" style={{ marginBottom: '0.75rem' }}>
            <h3 className="card-title" style={{ fontSize: '1.18rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileText size={20} color="var(--primary)" />
              Report Analysis: {analysisResult.file_name}
            </h3>
            <button
              className="btn btn-sm btn-secondary"
              onClick={() => setViewingFhir(analysisResult.fhir_diagnostic_report)}
            >
              <FileCode size={14} /> View FHIR JSON
            </button>
          </div>

          {/* 1. Short Analysis Overview */}
          <div style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            padding: '0.85rem 1rem',
            marginBottom: '1rem',
            fontSize: '0.88rem',
            color: '#334155',
            lineHeight: '1.5'
          }}>
            <strong style={{ color: 'var(--dark)', display: 'block', marginBottom: '0.25rem' }}>
              🔍 Short Document Analysis:
            </strong>
            {analysisResult.short_analysis || analysisResult.explanation}
          </div>

          {/* 2. WHAT IS ABNORMAL (Prominently Highlighted) */}
          {analysisResult.abnormal_findings && analysisResult.abnormal_findings.length > 0 ? (
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
                  Abnormal Findings & Parameters Detected ({analysisResult.abnormal_findings.length})
                </h4>
              </div>
              <p style={{ fontSize: '0.82rem', color: '#7f1d1d', marginBottom: '0.75rem' }}>
                The following values fall outside standard biological reference limits:
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {analysisResult.abnormal_findings.map((abn, i) => (
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
                        Patient Value: <strong style={{ color: '#dc2626' }}>{abn.patient_value}</strong> • Normal Ref: {abn.normal_range}
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
              padding: '0.9rem 1rem',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.65rem'
            }}>
              <CheckCircle size={20} color="#166534" />
              <div>
                <strong style={{ color: '#166534', fontSize: '0.92rem' }}>All Evaluated Parameters Within Normal Limits</strong>
                <div style={{ fontSize: '0.82rem', color: '#14532d', marginTop: '0.15rem' }}>
                  No acute laboratory or clinical outliers were detected outside standard reference intervals.
                </div>
              </div>
            </div>
          )}

          {/* 3. RELEVANT CONCLUSION */}
          <div style={{
            background: '#faf5ff',
            border: '1px solid #e9d5ff',
            borderLeft: '4px solid #8b5cf6',
            borderRadius: '8px',
            padding: '1rem',
            marginBottom: '1.25rem'
          }}>
            <h4 style={{ margin: 0, fontSize: '0.96rem', fontWeight: '800', color: '#6b21a8', marginBottom: '0.4rem' }}>
              📋 Relevant Clinical Conclusion:
            </h4>
            <p style={{ margin: 0, fontSize: '0.88rem', color: '#4c1d95', lineHeight: '1.55' }}>
              {analysisResult.relevant_conclusion || analysisResult.explanation}
            </p>
          </div>

          {/* 4. Full Extracted Parameters Table */}
          <h4 style={{ fontSize: '0.95rem', fontWeight: '800', marginBottom: '0.6rem', color: 'var(--dark)' }}>
            All Extracted Parameters & Reference Ranges:
          </h4>
          <div style={{ overflowX: 'auto', marginBottom: '0.5rem' }}>
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
                {analysisResult.findings?.map((f, i) => {
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
                      <td style={{ padding: '0.6rem 0.8rem', color: '#334155', fontSize: '0.82rem' }}>{f.explanation}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Uploaded Reports Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <FileText size={18} color="#0284c7" /> Your Uploaded Reports ({reports.length})
          </h3>
        </div>

        {reports.length === 0 ? (
          <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', textAlign: 'center', padding: '1.5rem 0' }}>
            No reports uploaded yet.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {reports.map((r) => (
              <div key={r.id} style={{
                padding: '0.95rem 1.1rem', background: '#f8fafc', borderRadius: '8px',
                border: '1px solid var(--border)', display: 'flex', alignItems: 'center',
                justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem'
              }}>
                <div style={{ flex: 1, minWidth: '240px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <div style={{ fontWeight: '700', fontSize: '0.92rem' }}>{r.file_name}</div>
                    <span className={`badge ${r.doctor_review_status === 'approved' ? 'badge-routine' : 'badge-warning'}`} style={{ fontSize: '0.72rem' }}>
                      {r.doctor_review_status === 'approved' ? '✓ Doctor Approved' : '⏳ Pending Doctor Review'}
                    </span>
                    {r.has_abnormalities && (
                      <span className="badge badge-emergency" style={{ fontSize: '0.72rem' }}>
                        ⚠️ {r.abnormal_count || (r.abnormal_findings?.length || 1)} Abnormal
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    Type: {r.file_type.toUpperCase()} • {(r.file_size_bytes / 1024).toFixed(1)} KB • Uploaded: {new Date(r.uploaded_at).toLocaleDateString()}
                  </div>

                  {r.relevant_conclusion ? (
                    <div style={{ fontSize: '0.83rem', color: '#475569', marginTop: '0.35rem', lineHeight: '1.4' }}>
                      <strong>Conclusion:</strong> {r.relevant_conclusion}
                    </div>
                  ) : r.key_observations ? (
                    <div style={{ fontSize: '0.82rem', color: '#475569', marginTop: '0.3rem' }}>
                      {r.key_observations.slice(0, 140)}...
                    </div>
                  ) : null}

                  {r.doctor_notes && (
                    <div style={{ fontSize: '0.82rem', color: '#166534', marginTop: '0.35rem', background: '#f0fdf4', padding: '0.35rem 0.5rem', borderRadius: '4px' }}>
                      <strong>Doctor Notes:</strong> {r.doctor_notes}
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <span className="badge badge-routine">
                    {r.findings_count} Parameters
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* FHIR Modal */}
      {viewingFhir && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="card-header">
              <h3 className="card-title"><FileCode size={20} /> HL7 FHIR DiagnosticReport Resource</h3>
              <button className="btn btn-sm btn-secondary" onClick={() => setViewingFhir(null)}>Close</button>
            </div>
            <pre style={{
              background: '#0f172a', color: '#38bdf8', padding: '1rem',
              borderRadius: '8px', overflowX: 'auto', fontSize: '0.78rem', maxHeight: '450px'
            }}>
              {JSON.stringify(viewingFhir, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
