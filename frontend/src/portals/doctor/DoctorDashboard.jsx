import React, { useState, useEffect } from 'react';
import { Users, AlertOctagon, Clock, FileText, CheckCircle, ArrowRight } from 'lucide-react';
import { api } from '../../api';

export default function DoctorDashboard({ onNavigateTab, onSelectPatient }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const data = await api.getDoctorDashboard();
      setStats(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{
        background: 'linear-gradient(135deg, #1e1b4b, #4338ca)',
        borderRadius: 'var(--radius)',
        color: '#ffffff',
        padding: '2rem',
        marginBottom: '1.5rem',
        boxShadow: 'var(--shadow)'
      }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: '800', marginBottom: '0.4rem' }}>
          Doctor Clinical Decision Portal
        </h1>
        <p style={{ opacity: 0.9, maxWidth: '650px', fontSize: '0.95rem' }}>
          Welcome, {stats?.doctor_name || 'Doctor'}. Review patient AI symptom assessments, verify clinical reports, manage allergies, and author clinical chart notes.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        <div className="card" style={{ cursor: 'pointer', textAlign: 'center' }} onClick={() => onNavigateTab('patients')}>
          <div style={{
            width: '46px', height: '46px', borderRadius: '12px', background: '#e0f2fe',
            color: '#0369a1', display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 0.75rem'
          }}>
            <Users size={24} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: 'var(--dark)' }}>
            {stats?.total_patients || 0}
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Registered Patients</div>
        </div>

        <div className="card" style={{ cursor: 'pointer', textAlign: 'center' }} onClick={() => onNavigateTab('reviews')}>
          <div style={{
            width: '46px', height: '46px', borderRadius: '12px', background: '#fef3c7',
            color: '#b45309', display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 0.75rem'
          }}>
            <Clock size={24} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#b45309' }}>
            {stats?.pending_assessments_count || 0}
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Pending AI Reviews</div>
        </div>

        <div className="card" style={{ cursor: 'pointer', textAlign: 'center' }} onClick={() => onNavigateTab('reviews')}>
          <div style={{
            width: '46px', height: '46px', borderRadius: '12px', background: '#fee2e2',
            color: '#dc2626', display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 0.75rem'
          }}>
            <AlertOctagon size={24} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#dc2626' }}>
            {stats?.emergency_alerts_count || 0}
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Emergency / Red-Flag Alerts</div>
        </div>

        <div className="card" style={{ cursor: 'pointer', textAlign: 'center' }} onClick={() => onNavigateTab('reports')}>
          <div style={{
            width: '46px', height: '46px', borderRadius: '12px', background: '#ede9fe',
            color: '#6d28d9', display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 0.75rem'
          }}>
            <FileText size={24} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#6d28d9' }}>
            {stats?.total_reports_uploaded || 0}
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Uploaded Lab Reports</div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Recent Clinical AI Assessments Queue</h3>
          <button className="btn btn-sm btn-outline-primary" onClick={() => onNavigateTab('reviews')}>
            Open Full Review Queue
          </button>
        </div>

        {stats?.recent_activity?.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '1.5rem 0' }}>
            No recent assessments found.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {stats?.recent_activity?.map((a) => (
              <div key={a.id} style={{
                padding: '0.85rem 1rem', background: '#f8fafc', borderRadius: '8px',
                border: '1px solid var(--border)', display: 'flex', alignItems: 'center',
                justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem'
              }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontWeight: '700', fontSize: '0.92rem' }}>{a.chief_complaint}</span>
                    <span className={`badge ${a.emergency_warning ? 'badge-emergency' : a.triage_level === 'URGENT' ? 'badge-urgent' : 'badge-routine'}`}>
                      {a.triage_level}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Patient ID #{a.patient_id} • {new Date(a.created_at).toLocaleString()}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span className={`badge ${a.review_status === 'approved' ? 'badge-selfcare' : 'badge-urgent'}`}>
                    {a.review_status}
                  </span>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => onNavigateTab('reviews')}
                  >
                    Review <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
