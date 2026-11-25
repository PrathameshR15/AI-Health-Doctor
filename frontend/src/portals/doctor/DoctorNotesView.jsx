import React, { useState, useEffect } from 'react';
import { Edit3, CheckCircle2, User, FileText } from 'lucide-react';
import { api } from '../../api';

export default function DoctorNotesView() {
  const [patients, setPatients] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [noteType, setNoteType] = useState('clinical');
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    try {
      const data = await api.getDoctorPatients();
      setPatients(data || []);
      if (data && data.length > 0) {
        setSelectedPatientId(data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedPatientId || !title.trim() || !content.trim()) return;

    setSubmitting(true);
    setSuccessMsg(null);
    try {
      await api.createDoctorNote({
        patient_id: Number(selectedPatientId),
        title,
        content,
        note_type: noteType
      });
      setSuccessMsg("Clinical note saved and added to the patient's medical chart.");
      setTitle('');
      setContent('');
    } catch (err) {
      alert("Error saving note: " + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="card-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h2 className="card-title" style={{ fontSize: '1.4rem' }}>
            <Edit3 size={22} color="var(--primary)" /> Doctor Clinical Notes
          </h2>
          <p className="card-description">
            Author and record physician clinical notes, observation follow-ups, and dietary directives into patient charts.
          </p>
        </div>
      </div>

      {successMsg && (
        <div style={{ padding: '0.85rem 1.25rem', background: '#dcfce7', color: '#166534', borderRadius: '8px', marginBottom: '1.5rem', fontWeight: '600' }}>
          ✓ {successMsg}
        </div>
      )}

      <form onSubmit={handleSubmit} className="card">
        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Select Patient</label>
            <select
              className="form-select"
              value={selectedPatientId}
              onChange={(e) => setSelectedPatientId(e.target.value)}
              required
            >
              {patients.map(p => (
                <option key={p.id} value={p.id}>
                  {p.full_name} ({p.email})
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Note Category</label>
            <select className="form-select" value={noteType} onChange={(e) => setNoteType(e.target.value)}>
              <option value="clinical">Clinical Examination & Assessment</option>
              <option value="prescription_review">Prescription & Therapy Review</option>
              <option value="lab_followup">Laboratory & Imaging Follow-up</option>
              <option value="dietary">Dietary & Lifestyle Directive</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Note Title <span style={{ color: '#dc2626' }}>*</span></label>
          <input
            type="text"
            className="form-input"
            placeholder="e.g. Asthma control review & follow-up instructions..."
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Clinical Observations & Directives <span style={{ color: '#dc2626' }}>*</span></label>
          <textarea
            className="form-textarea"
            rows={6}
            placeholder="Document physical findings, auscultation, confirmed diagnoses, instructions, or warning signs discussed with the patient..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
            required
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          style={{ width: '100%', padding: '0.8rem' }}
          disabled={submitting}
        >
          <CheckCircle2 size={16} /> {submitting ? "Signing & Saving Note..." : "Save Clinical Note to Patient Chart"}
        </button>
      </form>
    </div>
  );
}
