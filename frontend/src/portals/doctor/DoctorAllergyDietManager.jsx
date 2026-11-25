import React, { useState, useEffect } from 'react';
import { Utensils, CheckCircle2, ShieldCheck, Edit3 } from 'lucide-react';
import { api } from '../../api';

export default function DoctorAllergyDietManager() {
  const [allergies, setAllergies] = useState([]);
  const [editingRecord, setEditingRecord] = useState(null);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAllergies();
  }, []);

  const loadAllergies = async () => {
    try {
      const data = await api.getAllergiesAndDiet();
      setAllergies(data.allergies_and_diet_plans || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id, approved = true) => {
    try {
      await api.doctorApproveDiet(id, {
        approved: approved,
        doctor_notes: notes || "Diet plan clinically verified and approved by physician."
      });
      alert("Allergy & diet plan updated with doctor clinical approval.");
      setEditingRecord(null);
      setNotes('');
      loadAllergies();
    } catch (err) {
      alert("Error approving diet plan: " + err.message);
    }
  };

  return (
    <div>
      <div className="card-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h2 className="card-title" style={{ fontSize: '1.4rem' }}>
            <Utensils size={22} color="var(--primary)" /> Allergy & Diet Management
          </h2>
          <p className="card-description">
            Review food allergens, verify dietary exclusions, and provide doctor-approved nutrition guidance.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {allergies.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
            <p style={{ color: 'var(--text-muted)' }}>No allergy records requiring management.</p>
          </div>
        ) : (
          allergies.map(al => (
            <div key={al.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <strong style={{ fontSize: '1.15rem' }}>{al.allergen}</strong>
                  <span className={`badge ${al.severity === 'severe' ? 'badge-emergency' : al.severity === 'moderate' ? 'badge-urgent' : 'badge-selfcare'}`}>
                    {al.severity}
                  </span>
                </div>

                <div>
                  {al.doctor_approved ? (
                    <span className="badge badge-selfcare"><CheckCircle2 size={13} /> Doctor Approved</span>
                  ) : (
                    <span className="badge badge-urgent">Pending Approval</span>
                  )}
                </div>
              </div>

              {al.reaction && (
                <div style={{ fontSize: '0.85rem', color: '#475569', marginBottom: '0.6rem' }}>
                  <strong>Patient Reaction:</strong> {al.reaction}
                </div>
              )}

              <div className="grid-2" style={{ fontSize: '0.84rem', marginBottom: '0.75rem' }}>
                <div style={{ background: '#fef2f2', padding: '0.75rem', borderRadius: '6px' }}>
                  <strong style={{ color: '#b91c1c' }}>Foods to Exclude:</strong>
                  <ul style={{ paddingLeft: '1.2rem', color: '#7f1d1d', marginTop: '0.2rem' }}>
                    {al.foods_to_avoid?.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </div>
                <div style={{ background: '#f0fdf4', padding: '0.75rem', borderRadius: '6px' }}>
                  <strong style={{ color: '#15803d' }}>Approved Substitutes:</strong>
                  <ul style={{ paddingLeft: '1.2rem', color: '#14532d', marginTop: '0.2rem' }}>
                    {al.recommended_foods?.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </div>
              </div>

              {al.doctor_notes && (
                <div style={{ background: '#f8fafc', padding: '0.6rem 0.8rem', borderRadius: '6px', fontSize: '0.82rem', marginBottom: '0.75rem' }}>
                  <strong>Doctor Notes:</strong> {al.doctor_notes}
                </div>
              )}

              {editingRecord === al.id ? (
                <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)' }}>
                  <textarea
                    className="form-textarea"
                    placeholder="Enter doctor clinical recommendations or specific substitute guidance..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={2}
                    style={{ marginBottom: '0.5rem' }}
                  />
                  <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                    <button className="btn btn-sm btn-secondary" onClick={() => setEditingRecord(null)}>Cancel</button>
                    <button className="btn btn-sm btn-primary" onClick={() => handleApprove(al.id, true)}>
                      <CheckCircle2 size={14} /> Confirm Doctor Approval
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button className="btn btn-sm btn-outline-primary" onClick={() => { setEditingRecord(al.id); setNotes(al.doctor_notes || ''); }}>
                    <Edit3 size={14} /> {al.doctor_approved ? "Edit Approval & Notes" : "Approve Diet Plan"}
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
