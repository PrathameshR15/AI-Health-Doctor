import React, { useState, useEffect } from 'react';
import { Clock, Download, Calendar, Activity, AlertCircle, Pill, Heart, FileText, CheckCircle2, Stethoscope, BarChart3, List } from 'lucide-react';
import { api } from '../../api';
import HealthTimelinePlot from '../../components/HealthTimelinePlot';

export default function MedicalHistoryTimeline() {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [viewMode, setViewMode] = useState('both'); // 'both', 'graph', 'list'

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await api.getHistorySummary();
      setHistory(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const downloadFhirBundle = async () => {
    setDownloading(true);
    try {
      const bundle = await api.exportFHIRBundle();
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `FHIR_R4_Bundle_Patient_${history?.patient?.id || 'Record'}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("Error exporting FHIR bundle: " + err.message);
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '3rem' }}>Loading health timeline...</div>;
  }

  const timelineEvents = history?.timeline || [];

  return (
    <div>
      <div className="card-header" style={{ marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 className="card-title" style={{ fontSize: '1.4rem' }}>
            <Clock size={22} color="var(--primary)" /> Patient Health Timeline
          </h2>
          <p className="card-description">
            Chronological log of your health journey: AI assessments, lab report analyses, and treatment starts with exact dates & times.
          </p>
        </div>
        <button
          className="btn btn-secondary btn-sm"
          onClick={downloadFhirBundle}
          disabled={downloading}
          style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
        >
          <Download size={15} />
          {downloading ? "Exporting..." : "Download HL7 FHIR Bundle"}
        </button>
      </div>

      {/* Quick Vitals / Patient Banner */}
      <div className="card" style={{ background: '#f8fafc', marginBottom: '1.5rem' }}>
        <div className="grid-4" style={{ fontSize: '0.86rem' }}>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Date of Birth:</span>
            <div style={{ fontWeight: '700' }}>{history?.patient?.dob || 'Not set'}</div>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Blood Group:</span>
            <div style={{ fontWeight: '700' }}>{history?.patient?.blood_group || 'O+'}</div>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Chronic Conditions:</span>
            <div style={{ fontWeight: '700' }}>{history?.patient?.chronic_conditions || 'None'}</div>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Current Medications:</span>
            <div style={{ fontWeight: '700' }}>{history?.patient?.current_medications || 'None'}</div>
          </div>
        </div>
      </div>

      {/* 1. Interactive Graph Plotting of Timeline */}
      <HealthTimelinePlot events={timelineEvents} />

      {/* Main Health Timeline Stream */}
      <div className="card">
        <div className="card-header" style={{ marginBottom: '1rem' }}>
          <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Calendar size={18} color="var(--primary)" /> Chronological Health Events ({timelineEvents.length})
          </h3>
        </div>

        {timelineEvents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--text-muted)' }}>
            <Clock size={32} style={{ opacity: 0.35, marginBottom: '0.75rem' }} />
            <p style={{ margin: 0 }}>No health timeline events recorded yet.</p>
            <p style={{ fontSize: '0.82rem', marginTop: '0.35rem' }}>
              Consult the AI Virtual Doctor or upload medical reports to start tracking your timeline.
            </p>
          </div>
        ) : (
          <div className="timeline" style={{ paddingLeft: '0.5rem' }}>
            {timelineEvents.map((item) => {
              const isAssessment = item.event_type === 'ai_assessment';
              const isReport = item.event_type === 'report_analysis';
              const isTreatment = item.event_type === 'treatment_started';

              // Card styling depending on event
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
                    {/* Header Row: Event Label + Date & Time */}
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

                    {/* Word-limited Highlight Badge: 2 Words for Assessment, 3 Words for Report */}
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
                          border: `1px solid ${borderAccent}40`,
                          letterSpacing: '0.2px'
                        }}>
                          {isAssessment && '🎯 Assessment: '}
                          {isReport && '🔬 Report: '}
                          {isTreatment && '💊 Treatment: '}
                          {item.highlight}
                        </span>
                      </div>
                    )}

                    {/* Details / Summary */}
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

      {/* Conditions summary card */}
      {history?.diagnoses_and_assessments && history.diagnoses_and_assessments.length > 0 && (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <div className="card-header">
            <h3 className="card-title">
              <Heart size={18} color="#0d9488" /> Tracked Conditions ({history.diagnoses_and_assessments.length})
            </h3>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
            {history.diagnoses_and_assessments.map((c, i) => (
              <div key={i} style={{
                padding: '0.65rem 1rem', background: '#ffffff', borderRadius: '8px',
                border: '1px solid var(--border)', fontSize: '0.86rem'
              }}>
                <div style={{ fontWeight: '700', color: 'var(--dark)' }}>{c.name}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {c.date} • Status: <span style={{ textTransform: 'capitalize', fontWeight: '600', color: c.status === 'approved' ? '#166534' : '#b45309' }}>{c.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
