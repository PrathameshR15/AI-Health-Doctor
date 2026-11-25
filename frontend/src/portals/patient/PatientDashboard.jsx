import React, { useState, useEffect } from 'react';
import { Activity, MessageSquare, Upload, FileText, Heart, ShieldAlert, CheckCircle, Clock } from 'lucide-react';
import { api } from '../../api';

export default function PatientDashboard({ onNavigateTab }) {
  const [profile, setProfile] = useState(null);
  const [recentAssessments, setRecentAssessments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(false);
    try {
      const p = await api.getProfile();
      setProfile(p);
      const prev = await api.getPreviousAssessments();
      setRecentAssessments(prev || []);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div>
      {/* Welcome Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #0d9488, #0284c7)',
        borderRadius: 'var(--radius)',
        color: '#ffffff',
        padding: '2rem',
        marginBottom: '1.5rem',
        boxShadow: 'var(--shadow)'
      }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: '800', marginBottom: '0.4rem' }}>
          Welcome, {profile?.full_name || 'Patient'}
        </h1>
        <p style={{ opacity: 0.9, maxWidth: '650px', fontSize: '0.95rem' }}>
          Smart Health AI is ready to assist you. Check symptoms step-by-step, analyze lab reports, organize your medical history, and receive verified medical guidance.
        </p>
      </div>

      {/* Quick Action Cards */}
      <h2 style={{ fontSize: '1.15rem', fontWeight: '700', marginBottom: '1rem', color: 'var(--dark)' }}>
        Health Services & AI Tools
      </h2>
      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        <div className="card" style={{ cursor: 'pointer', textAlign: 'center' }} onClick={() => onNavigateTab('analyze')}>
          <div style={{
            width: '46px', height: '46px', borderRadius: '12px', background: '#ccfbf1',
            color: '#0f766e', display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 0.75rem'
          }}>
            <Activity size={24} />
          </div>
          <h3 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '0.25rem' }}>Analyze My Health</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Unified AI assessment & triage</p>
        </div>

        <div className="card" style={{ cursor: 'pointer', textAlign: 'center' }} onClick={() => onNavigateTab('checker')}>
          <div style={{
            width: '46px', height: '46px', borderRadius: '12px', background: '#e0f2fe',
            color: '#0369a1', display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 0.75rem'
          }}>
            <MessageSquare size={24} />
          </div>
          <h3 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '0.25rem' }}>AI Virtual Doctor</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Clinical Q&A, guidance & doctor review</p>
        </div>

        <div className="card" style={{ cursor: 'pointer', textAlign: 'center' }} onClick={() => onNavigateTab('reports')}>
          <div style={{
            width: '46px', height: '46px', borderRadius: '12px', background: '#fef3c7',
            color: '#b45309', display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 0.75rem'
          }}>
            <Upload size={24} />
          </div>
          <h3 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '0.25rem' }}>Medical Reports</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Upload PDF, images & FHIR</p>
        </div>

        <div className="card" style={{ cursor: 'pointer', textAlign: 'center' }} onClick={() => onNavigateTab('history')}>
          <div style={{
            width: '46px', height: '46px', borderRadius: '12px', background: '#ede9fe',
            color: '#6d28d9', display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 0.75rem'
          }}>
            <FileText size={24} />
          </div>
          <h3 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '0.25rem' }}>Medical History</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Timeline & FHIR Export</p>
        </div>
      </div>

      {/* Patient Profile Highlights & Recent Assessments */}
      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><Heart size={18} color="#0d9488" /> Clinical Profile Summary</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.88rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.4rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Blood Group:</span>
              <strong>{profile?.profile?.blood_group || 'O+'}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.4rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Chronic Conditions:</span>
              <strong>{profile?.profile?.chronic_conditions || 'None recorded'}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.4rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Known Allergies:</span>
              <strong style={{ color: '#dc2626' }}>{profile?.profile?.allergies_summary || 'None recorded'}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.4rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Current Medications:</span>
              <strong>{profile?.profile?.current_medications || 'None recorded'}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Emergency Contact:</span>
              <strong>{profile?.profile?.emergency_contact || 'None specified'}</strong>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><Clock size={18} color="#0284c7" /> Recent AI Health Assessments</h3>
            <button className="btn btn-sm btn-outline-primary" onClick={() => onNavigateTab('assessments')}>
              View All
            </button>
          </div>
          {recentAssessments.length === 0 ? (
            <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', textAlign: 'center', padding: '1.5rem 0' }}>
              No health assessments completed yet. Try "Analyze My Health" or "AI Virtual Doctor".
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {recentAssessments.slice(0, 3).map((a) => (
                <div key={a.id} style={{
                  padding: '0.75rem', background: '#f8fafc', borderRadius: '8px',
                  border: '1px solid var(--border)', display: 'flex',
                  alignItems: 'center', justifyContent: 'space-between'
                }}>
                  <div>
                    <div style={{ fontWeight: '700', fontSize: '0.88rem' }}>{a.chief_complaint}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {new Date(a.created_at).toLocaleDateString()} • {a.possible_conditions_count} conditions considered
                    </div>
                  </div>
                  <div>
                    {a.doctor_review_status === 'approved' ? (
                      <span className="badge badge-selfcare"><CheckCircle size={12} /> Approved by Doctor</span>
                    ) : (
                      <span className="badge badge-routine"><Clock size={12} /> Review Pending</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
