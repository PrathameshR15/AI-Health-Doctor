import React, { useState, useEffect } from 'react';
import { Utensils, AlertTriangle, CheckCircle2, PlusCircle, ShieldCheck } from 'lucide-react';
import { api } from '../../api';
import SourceBadge from '../../components/SourceBadge';

export default function AllergyAndDietView() {
  const [allergies, setAllergies] = useState([]);
  const [citations, setCitations] = useState([]);
  const [showForm, setShowForm] = useState(false);
  
  const [allergen, setAllergen] = useState('');
  const [reaction, setReaction] = useState('');
  const [severity, setSeverity] = useState('mild');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadAllergies();
  }, []);

  const loadAllergies = async () => {
    try {
      const data = await api.getAllergiesAndDiet();
      setAllergies(data.allergies_and_diet_plans || []);
      setCitations(data.citations || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!allergen.trim()) return;

    setSubmitting(true);
    try {
      await api.addAllergyRecord({
        allergen,
        reaction,
        severity
      });
      setAllergen('');
      setReaction('');
      setShowForm(false);
      loadAllergies();
    } catch (err) {
      alert("Error adding allergy record: " + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="card-header" style={{ marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 className="card-title" style={{ fontSize: '1.4rem' }}>
            <Utensils size={22} color="var(--primary)" /> Allergy & Diet Assistant
          </h2>
          <p className="card-description">
            Evidence-based nutritional alternatives, conflict identification, and doctor-approved dietary plans.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          <PlusCircle size={16} /> {showForm ? "Cancel" : "Add Allergy Trigger"}
        </button>
      </div>

      {citations.length > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginRight: '0.5rem' }}>
            Nutritional Reference Guidelines:
          </span>
          {citations.map((c, i) => (
            <SourceBadge key={i} source={c} />
          ))}
        </div>
      )}

      {/* Add Form */}
      {showForm && (
        <form onSubmit={handleAdd} className="card" style={{ background: '#f8fafc', borderLeft: '4px solid var(--primary)' }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: '700', marginBottom: '1rem' }}>
            Record New Allergy / Food Sensitivity
          </h3>

          <div className="grid-3">
            <div className="form-group">
              <label className="form-label">Allergen / Substance <span style={{ color: '#dc2626' }}>*</span></label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Peanuts, Shellfish, Dairy, Gluten, Eggs..."
                value={allergen}
                onChange={(e) => setAllergen(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Observed Reaction</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Hives, facial swelling, vomiting, bloating..."
                value={reaction}
                onChange={(e) => setReaction(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Severity Level</label>
              <select className="form-select" value={severity} onChange={(e) => setSeverity(e.target.value)}>
                <option value="mild">Mild (Localized rash, itching)</option>
                <option value="moderate">Moderate (Widespread hives, nausea)</option>
                <option value="severe">Severe / Anaphylaxis Risk</option>
              </select>
            </div>
          </div>

          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Analyzing Dietary Replacements..." : "Save Allergy & Generate Food Plan"}
          </button>
        </form>
      )}

      {/* List of Allergy & Diet Plans */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {allergies.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '2.5rem' }}>
            <p style={{ color: 'var(--text-muted)' }}>No allergies recorded yet. Click "Add Allergy Trigger" above.</p>
          </div>
        ) : (
          allergies.map((al) => (
            <div key={al.id} className="card" style={{ borderLeft: `5px solid ${al.severity === 'severe' ? '#ef4444' : al.severity === 'moderate' ? '#f59e0b' : '#10b981'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span style={{ fontSize: '1.2rem', fontWeight: '800', color: 'var(--dark)' }}>
                    {al.allergen}
                  </span>
                  <span className={`badge ${al.severity === 'severe' ? 'badge-emergency' : al.severity === 'moderate' ? 'badge-urgent' : 'badge-selfcare'}`}>
                    {al.severity.toUpperCase()}
                  </span>
                </div>

                <div>
                  {al.doctor_approved ? (
                    <span className="badge badge-selfcare">
                      <CheckCircle2 size={13} /> Doctor Approved
                    </span>
                  ) : (
                    <span className="badge badge-urgent">
                      Doctor Review Pending
                    </span>
                  )}
                </div>
              </div>

              {al.reaction && (
                <div style={{ fontSize: '0.85rem', color: '#475569', marginBottom: '0.75rem' }}>
                  <strong>Reported Reaction:</strong> {al.reaction}
                </div>
              )}

              <div className="grid-2">
                <div style={{ background: '#fef2f2', padding: '0.85rem', borderRadius: '8px', border: '1px solid #fecaca', fontSize: '0.85rem' }}>
                  <h4 style={{ color: '#b91c1c', fontWeight: '700', marginBottom: '0.35rem' }}>Foods to Strictly Avoid:</h4>
                  <ul style={{ paddingLeft: '1.2rem', color: '#7f1d1d' }}>
                    {al.foods_to_avoid?.map((f, i) => <li key={i}>{f}</li>) || <li>Avoid allergen ingredient</li>}
                  </ul>
                </div>

                <div style={{ background: '#f0fdf4', padding: '0.85rem', borderRadius: '8px', border: '1px solid #bbf7d0', fontSize: '0.85rem' }}>
                  <h4 style={{ color: '#15803d', fontWeight: '700', marginBottom: '0.35rem' }}>Recommended Safe Substitutes:</h4>
                  <ul style={{ paddingLeft: '1.2rem', color: '#14532d' }}>
                    {al.recommended_foods?.map((f, i) => <li key={i}>{f}</li>) || <li>Consult nutritionist</li>}
                  </ul>
                </div>
              </div>

              {al.doctor_notes && (
                <div style={{ marginTop: '0.85rem', padding: '0.65rem 0.85rem', background: '#f8fafc', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '0.82rem' }}>
                  <strong>Doctor Clinical Note:</strong> {al.doctor_notes}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
