import React, { useState } from 'react';
import { LayoutDashboard, Activity, MessageSquare, Upload, FileText, Utensils, History } from 'lucide-react';

import PatientDashboard from './PatientDashboard';
import AnalyzeMyHealth from './AnalyzeMyHealth';
import InteractiveSymptomChecker from './InteractiveSymptomChecker';
import UploadMedicalReports from './UploadMedicalReports';
import MedicalHistoryTimeline from './MedicalHistoryTimeline';
import AllergyAndDietView from './AllergyAndDietView';
import PreviousAssessments from './PreviousAssessments';

export default function PatientPortal({ currentUser }) {
  const [activeTab, setActiveTab] = useState('dashboard');

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={17} /> },
    { id: 'analyze', label: 'Analyze My Health', icon: <Activity size={17} /> },
    { id: 'checker', label: 'AI Virtual Doctor', icon: <MessageSquare size={17} /> },
    { id: 'reports', label: 'Upload Medical Reports', icon: <Upload size={17} /> },
    { id: 'history', label: 'Health Timeline', icon: <History size={17} /> },
    { id: 'diet', label: 'Allergies & Diet', icon: <Utensils size={17} /> },
    { id: 'assessments', label: 'Previous AI Assessments', icon: <History size={17} /> },
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
        {activeTab === 'dashboard' && <PatientDashboard onNavigateTab={setActiveTab} />}
        {activeTab === 'analyze' && <AnalyzeMyHealth />}
        {activeTab === 'checker' && <InteractiveSymptomChecker onNavigateTab={setActiveTab} />}
        {activeTab === 'reports' && <UploadMedicalReports />}
        {activeTab === 'history' && <MedicalHistoryTimeline />}
        {activeTab === 'diet' && <AllergyAndDietView />}
        {activeTab === 'assessments' && <PreviousAssessments />}
      </main>
    </div>
  );
}
