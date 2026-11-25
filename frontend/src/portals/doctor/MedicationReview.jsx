import React, { useState } from 'react';
import { Pill, Search, ShieldCheck, AlertTriangle } from 'lucide-react';
import { api } from '../../api';
import SourceBadge from '../../components/SourceBadge';

export default function MedicationReview() {
  const [query, setQuery] = useState('cough and mild fever');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const res = await api.getMedicationInfo(query);
      setData(res);
    } catch (err) {
      alert("Error retrieving medication information: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="card-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h2 className="card-title" style={{ fontSize: '1.4rem' }}>
            <Pill size={22} color="var(--primary)" /> Medication Information Review
          </h2>
          <p className="card-description">
            Inspect AI medication educational content, interaction warnings, and verify clinical compliance (No dosage/prescriptions).
          </p>
        </div>
      </div>

      {/* Search Input */}
      <form onSubmit={handleSearch} className="card" style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        <input
          type="text"
          className="form-input"
          placeholder="Enter symptom, condition, or medication class (e.g. cough, fever, GERD, paracetamol, asthma)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" className="btn btn-primary" disabled={loading} style={{ whiteSpace: 'nowrap' }}>
          <Search size={16} /> Look Up Class
        </button>
      </form>

      {/* Safety Compliance Banner */}
      <div className="card" style={{ background: '#fef3c7', borderLeft: '4px solid #d97706', padding: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: '800', color: '#92400e', marginBottom: '0.35rem' }}>
          <ShieldCheck size={18} /> Physician Safety Compliance Verification
        </div>
        <p style={{ fontSize: '0.84rem', color: '#78350f' }}>
          Smart Health AI is strictly restricted from calculating dosages, writing prescriptions, or initiating pharmacotherapy. All medication details presented to patients are purely educational.
        </p>
      </div>

      {/* Results */}
      {data && (
        <div>
          <div style={{ marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginRight: '0.5rem' }}>
              Reference Guidelines:
            </span>
            {data.medical_sources?.map((s, i) => (
              <SourceBadge key={i} source={s} />
            ))}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {data.educational_medication_info?.map((item, idx) => (
              <div key={idx} className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: '800', color: 'var(--dark)' }}>
                    {item.drug_class}
                  </h3>
                  <span className="badge badge-routine">
                    {item.common_agents?.join(', ')}
                  </span>
                </div>

                <div style={{ fontSize: '0.88rem', color: '#334155', marginBottom: '0.6rem' }}>
                  <strong>Mechanism & Purpose:</strong> {item.clinical_purpose}
                </div>

                <div style={{ fontSize: '0.85rem', color: '#475569', marginBottom: '0.6rem' }}>
                  <strong>Pharmacological Mechanism:</strong> {item.mechanism}
                </div>

                <div className="grid-2" style={{ fontSize: '0.82rem', marginTop: '0.75rem' }}>
                  <div style={{ background: '#fffbeb', padding: '0.75rem', borderRadius: '6px', border: '1px solid #fef3c7' }}>
                    <strong style={{ color: '#92400e' }}>Precautions & Contraindications:</strong>
                    <ul style={{ paddingLeft: '1.2rem', color: '#78350f', marginTop: '0.2rem' }}>
                      {item.precautions?.map((p, i) => <li key={i}>{p}</li>)}
                    </ul>
                  </div>

                  <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <strong style={{ color: '#334155' }}>Key Drug-Drug Interactions:</strong>
                    <ul style={{ paddingLeft: '1.2rem', color: '#475569', marginTop: '0.2rem' }}>
                      {item.key_interactions?.map((ki, i) => <li key={i}>{ki}</li>)}
                    </ul>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
