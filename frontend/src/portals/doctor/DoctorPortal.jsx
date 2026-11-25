import React, { useState } from 'react';
import { LayoutDashboard, Users, FileText, CheckSquare, History, Utensils, Pill, Edit3 } from 'lucide-react';

import DoctorDashboard from './DoctorDashboard';
import PatientManagement from './PatientManagement';
import MedicalRecordAnalysisView from './MedicalRecordAnalysisView';
import AIAssessmentReview from './AIAssessmentReview';
import DoctorAllergyDietManager from './DoctorAllergyDietManager';
import MedicationReview from './MedicationReview';
import DoctorNotesView from './DoctorNotesView';

export default function DoctorPortal({ currentUser }) {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedPatientId, setSelectedPatientId] = useState(null);

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={17} /> },
    { id: 'patients', label: 'Patient Management', icon: <Users size={17} /> },
    { id: 'reports', label: 'Medical Record Analysis', icon: <FileText size={17} /> },
    { id: 'reviews', label: 'AI Assessment Reviews', icon: <CheckSquare size={17} /> },
    { id: 'allergies', label: 'Allergy & Diet Management', icon: <Utensils size={17} /> },
    { id: 'medications', label: 'Medication Review', icon: <Pill size={17} /> },
    { id: 'notes', label: 'Doctor Notes', icon: <Edit3 size={17} /> },
  ];

  return (
    <div>
      <div className="portal-tabs-wrapper">
        <div className="portal-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`portal-tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      <main className="main-content">
        {activeTab === 'dashboard' && (
          <DoctorDashboard
            onNavigateTab={setActiveTab}
            onSelectPatient={(id) => { setSelectedPatientId(id); setActiveTab('patients'); }}
          />
        )}
        {activeTab === 'patients' && (
          <PatientManagement
            initialPatientId={selectedPatientId}
            onWriteNote={(id) => { setSelectedPatientId(id); setActiveTab('notes'); }}
          />
        )}
        {activeTab === 'reports' && <MedicalRecordAnalysisView />}
        {activeTab === 'reviews' && <AIAssessmentReview />}
        {activeTab === 'allergies' && <DoctorAllergyDietManager />}
        {activeTab === 'medications' && <MedicationReview />}
        {activeTab === 'notes' && <DoctorNotesView initialPatientId={selectedPatientId} />}
      </main>
    </div>
  );
}
