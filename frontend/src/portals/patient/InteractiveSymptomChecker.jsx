import React, { useState, useEffect } from 'react';
import { 
  MessageSquare, Send, CheckCircle2, ShieldAlert, ArrowRight, RotateCcw, 
  Sparkles, HeartPulse, AlertTriangle, ShieldCheck, Coffee, Thermometer, 
  Stethoscope, Lightbulb, HelpCircle, BookOpen, Dumbbell, Droplets, Clock, 
  RefreshCw, Calendar, ChevronRight, Activity, UserCheck, History
} from 'lucide-react';
import { api } from '../../api';
import EmergencyAlert from '../../components/EmergencyAlert';

const safeText = (val) => {
  if (val === null || val === undefined) return '';
  if (typeof val === 'string' || typeof val === 'number') return String(val);
  if (typeof val === 'object') {
    return val.condition || val.test_name || val.drug_class || val.precaution || val.text || val.title || val.name || JSON.stringify(val);
  }
  return String(val);
};

const safeArray = (val) => {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  if (typeof val === 'object') return Object.values(val);
  return [val];
};

export default function InteractiveSymptomChecker({ onNavigateTab }) {
  // Navigation: 'consultation' or 'history'
  const [viewMode, setViewMode] = useState('consultation');
  
  // Consultation State
  const [complaint, setComplaint] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [assessmentId, setAssessmentId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [suggestedOptions, setSuggestedOptions] = useState([]);
  const [isCompleted, setIsCompleted] = useState(false);
  const [emergencyAlert, setEmergencyAlert] = useState(null);
  const [assessmentResult, setAssessmentResult] = useState(null);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [isFollowUp, setIsFollowUp] = useState(false);

  // Doctor Review Status State
  const [doctorStatus, setDoctorStatus] = useState(null);
  const [refreshingStatus, setRefreshingStatus] = useState(false);

  // Longitudinal Progress & History State
  const [historyList, setHistoryList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Session Recovery from localStorage
  useEffect(() => {
    const savedSessionId = localStorage.getItem('sh_active_consultation_id');
    if (savedSessionId && !sessionId && !isCompleted) {
      resumeSession(parseInt(savedSessionId));
    }
  }, []);

  const resumeSession = async (sId) => {
    try {
      setLoading(true);
      const data = await api.getSymptomSessionDetail(sId);
      if (data && data.status === 'in_progress') {
        setSessionId(data.id);
        setComplaint(data.chief_complaint);
        setMessages(data.conversation_history || []);
        setCurrentStep(Math.max(1, Math.floor((data.conversation_history || []).length / 2)));
        if (data.emergency_flag) {
          setEmergencyAlert("Emergency warning flagged during consultation. Seek prompt medical care.");
        }
      } else {
        localStorage.removeItem('sh_active_consultation_id');
      }
    } catch (e) {
      localStorage.removeItem('sh_active_consultation_id');
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await api.getPatientConsultationHistory();
      setHistoryList(res.consultations || []);
    } catch (err) {
      console.error("Failed to load history:", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const checkDoctorReviewStatus = async (aId) => {
    const targetId = aId || assessmentId;
    if (!targetId) return;
    setRefreshingStatus(true);
    try {
      const statusData = await api.getDoctorReviewStatus(targetId);
      setDoctorStatus(statusData);
    } catch (err) {
      console.error("Error checking doctor status:", err);
    } finally {
      setRefreshingStatus(false);
    }
  };

  const startSession = async (e, customComplaint = null) => {
    if (e) e.preventDefault();
    const textToSubmit = customComplaint || complaint;
    if (!textToSubmit.trim()) return;

    setLoading(true);
    setEmergencyAlert(null);
    setIsCompleted(false);
    setAssessmentResult(null);
    setDoctorStatus(null);
    setIsFollowUp(false);

    try {
      const data = await api.startSymptomSession(textToSubmit);
      setSessionId(data.session_id);
      localStorage.setItem('sh_active_consultation_id', String(data.session_id));
      setCurrentStep(data.step);
      setSuggestedOptions(data.suggested_options || []);
      
      const initialMessages = [
        { role: 'user', content: textToSubmit },
        { role: 'assistant', content: data.question }
      ];
      setMessages(initialMessages);

      if (data.emergency_flag) {
        setEmergencyAlert(data.emergency_message || "Critical emergency detected. Seek emergency medical attention immediately.");
      }
    } catch (err) {
      alert("Error starting AI Virtual Doctor consultation: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const startFollowUp = async (prevSessionId, previousComplaint) => {
    setLoading(true);
    setEmergencyAlert(null);
    setIsCompleted(false);
    setAssessmentResult(null);
    setDoctorStatus(null);
    setIsFollowUp(true);
    setViewMode('consultation');

    try {
      const data = await api.startFollowUpSession(prevSessionId, "");
      setSessionId(data.session_id);
      localStorage.setItem('sh_active_consultation_id', String(data.session_id));
      setCurrentStep(data.step);
      setSuggestedOptions(data.suggested_options || []);
      setComplaint(`Follow-up on: ${previousComplaint}`);

      const initialMessages = [
        { role: 'user', content: `Follow-up regarding my previous consultation on: "${previousComplaint}"` },
        { role: 'assistant', content: data.question }
      ];
      setMessages(initialMessages);
    } catch (err) {
      alert("Error starting follow-up consultation: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const sendAnswer = async (answerText) => {
    if (!answerText.trim() || !sessionId || isCompleted) return;

    const updatedMessages = [...messages, { role: 'user', content: answerText }];
    setMessages(updatedMessages);
    setInputText('');
    setLoading(true);

    try {
      const data = await api.answerSymptomQuestion(sessionId, answerText);
      setCurrentStep(data.step);

      if (data.emergency_flag) {
        setEmergencyAlert(data.emergency_message || "Potential emergency warning signs detected. Please proceed to an emergency clinic.");
      }

      if (data.is_completed) {
        setIsCompleted(true);
        localStorage.removeItem('sh_active_consultation_id');
        setSuggestedOptions([]);
        setAssessmentResult(data.assessment);
        if (data.assessment_id) {
          setAssessmentId(data.assessment_id);
          checkDoctorReviewStatus(data.assessment_id);
        }

        const botReply = data.assistant_reply || (
          answerText.toLowerCase().includes("advice") || answerText.toLowerCase().includes("cure")
            ? "Here is your personalized guidance including root causes, non-drug home relief, exercise modifications, hydration, and medical tests. Your report has also been securely sent to the Doctor Portal for physician review."
            : "Thank you for completing the clinical Q&A. I have analyzed your complete symptom constellation, generated personalized home care, and sent this report to the Doctor Portal for clinical review."
        );

        setMessages([
          ...updatedMessages,
          {
            role: 'assistant',
            content: botReply
          }
        ]);
      } else {
        setSuggestedOptions(data.suggested_options || []);
        setMessages([
          ...updatedMessages,
          { role: 'assistant', content: data.question }
        ]);
      }
    } catch (err) {
      alert("Error submitting consultation response: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRestart = () => {
    localStorage.removeItem('sh_active_consultation_id');
    setComplaint('');
    setSessionId(null);
    setAssessmentId(null);
    setMessages([]);
    setCurrentStep(0);
    setSuggestedOptions([]);
    setIsCompleted(false);
    setEmergencyAlert(null);
    setAssessmentResult(null);
    setDoctorStatus(null);
    setIsFollowUp(false);
  };

  return (
    <div>
      {/* Top Header & Mode Toggle */}
      <div className="card-header" style={{ marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
            <span className="badge badge-primary" style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}>
              <Sparkles size={12} style={{ marginRight: '3px' }} /> Clinical AI Telehealth
            </span>
            <span className="badge" style={{ background: '#f1f5f9', color: '#475569', fontSize: '0.75rem' }}>
              Doctor-Reviewed
            </span>
          </div>
          <h2 className="card-title" style={{ fontSize: '1.45rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Stethoscope size={24} color="var(--primary)" /> AI Virtual Doctor
          </h2>
          <p className="card-description">
            Interactive clinical consultation, smart follow-up questions, personalized guidance, and direct doctor review integration.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button 
            className={`btn btn-sm ${viewMode === 'consultation' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setViewMode('consultation')}
          >
            <MessageSquare size={14} /> Virtual Doctor Chat
          </button>
          <button 
            className={`btn btn-sm ${viewMode === 'history' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { setViewMode('history'); loadHistory(); }}
          >
            <History size={14} /> Consultation History & Progress
          </button>
          {sessionId && viewMode === 'consultation' && (
            <button className="btn btn-secondary btn-sm" onClick={handleRestart} title="Start Fresh Consultation">
              <RotateCcw size={14} /> Restart
            </button>
          )}
        </div>
      </div>

      {emergencyAlert && <EmergencyAlert message={emergencyAlert} />}

      {/* VIEW MODE 1: CONSULTATION HISTORY & LONGITUDINAL PROGRESS */}
      {viewMode === 'history' && (
        <div className="card">
          <div className="card-header" style={{ marginBottom: '1rem' }}>
            <div>
              <h3 className="card-title" style={{ fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Calendar size={18} color="var(--primary)" /> Symptom Progress & Consultation Tracking
              </h3>
              <p className="card-description">
                Monitor your symptom evolution across previous visits and initiate follow-ups with physician review tracking.
              </p>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={loadHistory} disabled={loadingHistory}>
              <RefreshCw size={13} className={loadingHistory ? 'spin' : ''} /> Refresh History
            </button>
          </div>

          {loadingHistory ? (
            <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
              Loading consultation history...
            </div>
          ) : historyList.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
              <Stethoscope size={36} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
              <p>No previous AI Virtual Doctor consultations recorded yet.</p>
              <button className="btn btn-primary btn-sm" onClick={() => setViewMode('consultation')} style={{ marginTop: '0.75rem' }}>
                Start Your First Consultation
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              {historyList.map((item, idx) => {
                const isApproved = item.doctor_review_status === 'approved';
                return (
                  <div key={idx} style={{
                    padding: '1rem 1.25rem',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    background: '#ffffff',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '0.75rem'
                  }}>
                    <div style={{ flex: 1, minWidth: '240px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
                        <strong style={{ fontSize: '1rem', color: 'var(--dark)' }}>
                          {item.chief_complaint}
                        </strong>
                        <span className={`badge ${isApproved ? 'badge-routine' : 'badge-urgent'}`} style={{ fontSize: '0.72rem' }}>
                          {isApproved ? `✓ Doctor Approved` : `⏳ Pending Doctor Review`}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                        <span>📅 {item.date}</span>
                        {item.active_symptoms?.length > 0 && (
                          <span>🩺 Symptoms: {item.active_symptoms.slice(0, 4).join(', ')}</span>
                        )}
                        {item.reviewed_by && (
                          <span>👨‍⚕️ Reviewed by: {item.reviewed_by}</span>
                        )}
                      </div>
                      {item.doctor_notes && (
                        <div style={{ fontSize: '0.82rem', color: '#047857', marginTop: '0.35rem', background: '#ecfdf5', padding: '0.35rem 0.65rem', borderRadius: '4px' }}>
                          <strong>Doctor Note:</strong> {item.doctor_notes}
                        </div>
                      )}
                    </div>

                    <button 
                      className="btn btn-secondary btn-sm"
                      onClick={() => startFollowUp(item.session_id, item.chief_complaint)}
                      style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}
                    >
                      <Activity size={14} color="var(--primary)" /> Follow Up Today
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* VIEW MODE 2: ACTIVE VIRTUAL DOCTOR CONSULTATION */}
      {viewMode === 'consultation' && (
        <div>
          {!sessionId ? (
            <form onSubmit={startSession} className="card">
              <div className="form-group">
                <label className="form-label" style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--dark)' }}>
                  Hello! I am your AI Virtual Doctor. What symptoms or discomfort are you experiencing?
                </label>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                  Describe your symptoms in natural language. Mention when they started, severity, and any accompanying discomfort.
                </p>
                <textarea
                  className="form-textarea"
                  placeholder="e.g. I've had headaches and weakness for three days, accompanied by mild neck tension..."
                  value={complaint}
                  onChange={(e) => setComplaint(e.target.value)}
                  rows={4}
                  required
                />
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', alignSelf: 'center' }}>Quick Examples:</span>
                {[
                  "I've had headaches and weakness for three days",
                  "Persistent dry cough, runny nose and throat tickle for 2 days",
                  "Stomach cramping, acidity, and mild nausea after meals",
                  "Facial sinus pressure, nasal congestion, and mild fatigue"
                ].map((ex) => (
                  <button
                    type="button"
                    key={ex}
                    className="quick-option-btn"
                    onClick={() => { setComplaint(ex); startSession(null, ex); }}
                  >
                    {ex}
                  </button>
                ))}
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%', padding: '0.85rem', fontSize: '1rem', fontWeight: '600' }}
                disabled={loading}
              >
                {loading ? "Starting AI Doctor Consultation..." : "Start Consultation with AI Virtual Doctor"}
              </button>
            </form>
          ) : (
            <div>
              {/* Consultation Progress Header */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                background: '#ffffff', padding: '0.85rem 1.25rem', borderRadius: 'var(--radius)',
                border: '1px solid var(--border)', marginBottom: '1rem', fontSize: '0.88rem'
              }}>
                <div>
                  <strong style={{ color: 'var(--primary)' }}>
                    {isCompleted ? "Consultation Analysis Complete" : `Doctor's Clinical Question ${Math.min(currentStep, 3)} of 3`}
                  </strong>
                  {isFollowUp && (
                    <span className="badge badge-primary" style={{ marginLeft: '0.5rem', fontSize: '0.72rem' }}>
                      Longitudinal Follow-up
                    </span>
                  )}
                </div>
                <div style={{ color: isCompleted ? '#166534' : 'var(--text-muted)', fontWeight: '600' }}>
                  {isCompleted ? "✓ Guidance Prepared & Sent to Doctor" : "Evaluating clinical response..."}
                </div>
              </div>

              {/* Chat Transcript Window */}
              <div className="chat-container">
                {messages.map((m, idx) => (
                  <div key={idx} className={`chat-bubble ${m.role}`}>
                    <div style={{ fontSize: '0.75rem', opacity: 0.75, marginBottom: '0.25rem', fontWeight: '700' }}>
                      {m.role === 'user' ? 'You (Patient)' : 'AI Virtual Doctor'}
                    </div>
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.55', fontSize: '0.94rem' }}>{m.content}</div>
                  </div>
                ))}
                {loading && (
                  <div className="chat-bubble assistant">
                    <span style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>
                      AI Virtual Doctor is reviewing clinical entities and knowledge guidelines...
                    </span>
                  </div>
                )}
              </div>

              {/* Interactive Answer Options & Advice Pill */}
              {!isCompleted && (
                <div style={{ marginBottom: '1.25rem', marginTop: '0.75rem' }}>
                  <div style={{ fontSize: '0.82rem', fontWeight: '700', color: 'var(--text-muted)', marginBottom: '0.45rem' }}>
                    Interactive Answers & Actions (Tap to respond):
                  </div>
                  <div className="quick-options" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {suggestedOptions.map((opt, idx) => {
                      const isAdvice = opt.toLowerCase().includes("advice") || opt.toLowerCase().includes("cure");
                      return (
                        <button
                          key={idx}
                          type="button"
                          className="quick-option-btn"
                          style={isAdvice ? {
                            background: '#eff6ff',
                            borderColor: '#93c5fd',
                            color: '#1d4ed8',
                            fontWeight: '700',
                            boxShadow: '0 1px 3px rgba(37,99,235,0.1)'
                          } : {}}
                          onClick={() => sendAnswer(opt)}
                          disabled={loading}
                        >
                          {opt}
                        </button>
                      );
                    })}

                    {!suggestedOptions.some(o => o.toLowerCase().includes("advice")) && (
                      <button
                        type="button"
                        className="quick-option-btn"
                        style={{
                          background: '#eff6ff',
                          borderColor: '#93c5fd',
                          color: '#1d4ed8',
                          fontWeight: '700',
                          boxShadow: '0 1px 3px rgba(37,99,235,0.1)'
                        }}
                        onClick={() => sendAnswer("💡 Give me advice: What should be done for cure, prevention and why it happens")}
                        disabled={loading}
                      >
                        💡 Give Me Advice: Cure, Prevention & Why It Happens
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Text Input for Custom Responses */}
              {!isCompleted && (
                <form
                  onSubmit={(e) => { e.preventDefault(); sendAnswer(inputText); }}
                  style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}
                >
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Type your answer to the AI Doctor in your own words..."
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    disabled={loading}
                  />
                  <button type="submit" className="btn btn-primary" disabled={loading || !inputText.trim()}>
                    <Send size={18} /> Send
                  </button>
                </form>
              )}

              {/* COMPREHENSIVE ASSESSMENT & PERSONALIZED GUIDANCE SECTION */}
              {isCompleted && assessmentResult && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginTop: '1.25rem' }}>
                  
                  {/* DOCTOR PORTAL INTEGRATION STATUS BANNER */}
                  <div style={{
                    background: doctorStatus?.doctor_review_status === 'approved' ? '#ecfdf5' : '#eff6ff',
                    border: `1px solid ${doctorStatus?.doctor_review_status === 'approved' ? '#a7f3d0' : '#bfdbfe'}`,
                    borderRadius: '10px',
                    padding: '1.1rem 1.35rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '0.85rem'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                      {doctorStatus?.doctor_review_status === 'approved' ? (
                        <UserCheck size={28} color="#059669" />
                      ) : (
                        <Clock size={28} color="#2563eb" />
                      )}
                      <div>
                        <div style={{ fontWeight: '700', fontSize: '1.02rem', color: doctorStatus?.doctor_review_status === 'approved' ? '#065f46' : '#1e40af' }}>
                          {doctorStatus?.doctor_review_status === 'approved' 
                            ? `✓ Reviewed & Approved by ${doctorStatus.reviewed_by || 'Treating Physician'}`
                            : "Report Sent to Doctor Portal • Pending Physician Sign-Off"}
                        </div>
                        <div style={{ fontSize: '0.86rem', color: '#475569', marginTop: '0.2rem' }}>
                          {doctorStatus?.doctor_review_status === 'approved'
                            ? (doctorStatus.doctor_notes || "Clinical findings reviewed and approved by treating physician.")
                            : "Your structured clinical SOAP note and differential assessment have been submitted to the Doctor Portal for review and prescription authorization."}
                        </div>
                      </div>
                    </div>

                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => checkDoctorReviewStatus()}
                      disabled={refreshingStatus}
                      style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem' }}
                    >
                      <RefreshCw size={13} className={refreshingStatus ? 'spin' : ''} />
                      {refreshingStatus ? "Checking..." : "Check Review Status"}
                    </button>
                  </div>

                  {/* 1. ASSESSED POSSIBLE CONDITIONS & DIFFERENTIAL CONSIDERATIONS */}
                  <div className="card" style={{ borderLeft: '4px solid #0284c7', background: '#f8fafc' }}>
                    <div className="card-header" style={{ marginBottom: '0.65rem' }}>
                      <h3 className="card-title" style={{ fontSize: '1.18rem', color: '#0369a1', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Stethoscope size={20} color="#0284c7" /> Assessed Conditions & Differential Diagnoses
                      </h3>
                      <span className="badge badge-routine" style={{ fontSize: '0.74rem' }}>
                        Decision-Support Only
                      </span>
                    </div>
                    
                    <p style={{ fontSize: '0.88rem', color: '#475569', marginBottom: '1rem', lineHeight: '1.5' }}>
                      {assessmentResult.what_it_likely_is || "Differential considerations identified based on your reported symptom constellation."}
                    </p>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      {safeArray(assessmentResult.possible_conditions || assessmentResult.differential_diagnoses).map((c, i) => (
                        <div key={i} style={{ padding: '0.85rem', background: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <strong style={{ color: 'var(--dark)', fontSize: '0.96rem' }}>{safeText(c?.condition || c?.name || c)}</strong>
                            <span className="badge badge-routine" style={{ fontSize: '0.74rem' }}>{safeText(c?.likelihood || 'Moderate')} Likelihood</span>
                          </div>
                          {c?.rationale && (
                            <div style={{ fontSize: '0.85rem', color: '#334155', marginTop: '0.35rem', lineHeight: '1.45' }}>
                              <strong>Clinical Rationale:</strong> {safeText(c.rationale)}
                            </div>
                          )}
                          {c?.clinical_explanation && (
                            <div style={{ fontSize: '0.82rem', color: '#64748b', marginTop: '0.2rem' }}>
                              {safeText(c.clinical_explanation)}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 2. PERSONALIZED NON-DRUG HOME REMEDIES */}
                  <div className="card" style={{ borderLeft: '4px solid #10b981', background: '#f0fdf4' }}>
                    <div className="card-header" style={{ marginBottom: '0.65rem' }}>
                      <h3 className="card-title" style={{ fontSize: '1.15rem', color: '#065f46', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Coffee size={20} color="#10b981" /> Personalized Home Remedies (Cure & Comfort)
                      </h3>
                    </div>
                    <p style={{ fontSize: '0.86rem', color: '#065f46', marginBottom: '0.85rem' }}>
                      Key evidence-based non-drug supportive measures for natural relief:
                    </p>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
                      {safeArray(assessmentResult.home_remedies || []).slice(0, 3).map((remedy, i) => (
                        <div key={i} style={{
                          background: '#ffffff',
                          padding: '0.85rem 1rem',
                          borderRadius: '8px',
                          border: '1px solid #bbf7d0',
                          boxShadow: '0 1px 2px rgba(0,0,0,0.02)'
                        }}>
                          <div style={{ fontWeight: '700', fontSize: '0.92rem', color: '#166534', marginBottom: '0.25rem' }}>
                            🌿 {safeText(remedy.title || remedy)}
                          </div>
                          {remedy.instructions && (
                            <div style={{ fontSize: '0.84rem', color: '#334155', lineHeight: '1.45' }}>
                              {remedy.instructions}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 3. EXERCISE & PHYSICAL ACTIVITY ADJUSTMENTS */}
                  <div className="card" style={{ borderLeft: '4px solid #f97316', background: '#fff7ed' }}>
                    <div className="card-header" style={{ marginBottom: '0.65rem' }}>
                      <h3 className="card-title" style={{ fontSize: '1.15rem', color: '#c2410c', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Dumbbell size={20} color="#f97316" /> Gentle Exercises & Physical Rest Guidance
                      </h3>
                    </div>
                    <p style={{ fontSize: '0.86rem', color: '#9a3412', marginBottom: '0.85rem' }}>
                      Essential stretching, posture, and pacing adjustments tailored to your current symptoms:
                    </p>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
                      {safeArray(assessmentResult.exercises || assessmentResult.exercise_guidance || []).slice(0, 2).map((ex, i) => (
                        <div key={i} style={{
                          background: '#ffffff',
                          padding: '0.85rem 1rem',
                          borderRadius: '8px',
                          border: '1px solid #fed7aa',
                          boxShadow: '0 1px 2px rgba(0,0,0,0.02)'
                        }}>
                          <div style={{ fontWeight: '700', fontSize: '0.92rem', color: '#9a3412', marginBottom: '0.25rem' }}>
                            🏃 {safeText(ex.name || ex)}
                          </div>
                          {ex.instructions && (
                            <div style={{ fontSize: '0.84rem', color: '#334155', lineHeight: '1.45' }}>
                              {ex.instructions}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 4. DIET & HYDRATION PLAN */}
                  <div className="card" style={{ borderLeft: '4px solid #06b6d4', background: '#ecfeff' }}>
                    <div className="card-header" style={{ marginBottom: '0.75rem' }}>
                      <h3 className="card-title" style={{ fontSize: '1.18rem', color: '#0e7490', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Droplets size={20} color="#06b6d4" /> Diet & Hydration Guidance
                      </h3>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
                      {/* Hydration */}
                      <div style={{ background: '#ffffff', padding: '1rem', borderRadius: '8px', border: '1px solid #a5f3fc' }}>
                        <h4 style={{ fontSize: '0.95rem', color: '#0e7490', marginBottom: '0.4rem', fontWeight: '700' }}>
                          💧 Hydration Target: {assessmentResult.hydration_advice?.daily_target || "2.5 to 3.0 Liters daily"}
                        </h4>
                        <div style={{ fontSize: '0.85rem', color: '#334155', marginBottom: '0.5rem' }}>
                          <strong>Recommended:</strong> {safeArray(assessmentResult.hydration_advice?.recommended_fluids || ["Filtered water", "Electrolyte fluids", "Warm broths"]).join(', ')}
                        </div>
                        {assessmentResult.hydration_advice?.clinical_tips && (
                          <div style={{ fontSize: '0.82rem', color: '#64748b' }}>
                            <strong>Tip:</strong> {assessmentResult.hydration_advice.clinical_tips}
                          </div>
                        )}
                      </div>

                      {/* Diet */}
                      <div style={{ background: '#ffffff', padding: '1rem', borderRadius: '8px', border: '1px solid #a5f3fc' }}>
                        <h4 style={{ fontSize: '0.95rem', color: '#0e7490', marginBottom: '0.4rem', fontWeight: '700' }}>
                          🥗 Nutritional Advice
                        </h4>
                        <div style={{ fontSize: '0.85rem', color: '#166534', marginBottom: '0.35rem' }}>
                          <strong>Recommended Foods:</strong> {safeArray(assessmentResult.diet_guidance?.recommended || ["Warm vegetable broths", "Easily digestible grains", "Fresh fruits"]).slice(0, 3).join(', ')}
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#b91c1c' }}>
                          <strong>Foods to Limit:</strong> {safeArray(assessmentResult.diet_guidance?.avoid || ["Greasy/fried foods", "Excessive caffeine", "High refined sugars"]).slice(0, 3).join(', ')}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 5. RECOMMENDED MEDICAL TESTS */}
                  {assessmentResult.test_guidance?.length > 0 && (
                    <div className="card" style={{ borderLeft: '4px solid #6366f1', background: '#eef2ff' }}>
                      <div className="card-header" style={{ marginBottom: '0.75rem' }}>
                        <h3 className="card-title" style={{ fontSize: '1.18rem', color: '#4338ca', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <Activity size={20} color="#6366f1" /> Recommended Medical Tests (When Considered)
                        </h3>
                      </div>
                      <p style={{ fontSize: '0.88rem', color: '#3730a3', marginBottom: '1rem' }}>
                        Targeted clinical tests to discuss with your doctor if symptoms persist or warrant confirmation:
                      </p>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                        {safeArray(assessmentResult.test_guidance).map((t, i) => (
                          <div key={i} style={{ background: '#ffffff', padding: '0.85rem', borderRadius: '8px', border: '1px solid #c7d2fe' }}>
                            <div style={{ fontWeight: '700', fontSize: '0.94rem', color: '#312e81' }}>
                              🔬 {safeText(t.test_name || t.name || t)}
                            </div>
                            <div style={{ fontSize: '0.85rem', color: '#334155', marginTop: '0.25rem' }}>
                              <strong>Purpose:</strong> {safeText(t.purpose || "Diagnostic evaluation")}
                            </div>
                            {t.when_considered && (
                              <div style={{ fontSize: '0.82rem', color: '#4b5563', marginTop: '0.2rem' }}>
                                <strong>Clinical Timing:</strong> {safeText(t.when_considered)}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 6. PREVENTION & ROOT CAUSE (WHY IT HAPPENS) */}
                  <div className="card" style={{ borderLeft: '4px solid #8b5cf6', background: '#faf5ff' }}>
                    <div className="card-header" style={{ marginBottom: '0.45rem' }}>
                      <h3 className="card-title" style={{ fontSize: '1.15rem', color: '#6d28d9', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <BookOpen size={20} color="#8b5cf6" /> Why It Happens & Prevention Guide
                      </h3>
                    </div>
                    <p style={{ fontSize: '0.88rem', color: '#334155', lineHeight: '1.55', marginBottom: '0.75rem' }}>
                      {assessmentResult.why_it_happens || "This symptom occurs as a physiological response to mild inflammation or strain as your immune defenses work to restore normal balance."}
                    </p>

                    <div style={{ fontSize: '0.84rem', fontWeight: '700', color: '#6d28d9', marginBottom: '0.35rem' }}>
                      🛡️ Essential Preventive Habits:
                    </div>
                    <ul style={{ paddingLeft: '1.25rem', margin: 0, fontSize: '0.85rem', color: '#4b5563', lineHeight: '1.5' }}>
                      {safeArray(assessmentResult.prevention_tips || []).slice(0, 3).map((tip, i) => (
                        <li key={i} style={{ marginBottom: '0.25rem' }}>{safeText(tip)}</li>
                      ))}
                    </ul>
                  </div>

                  {/* 7. RED FLAGS & SAFETY PRECAUTIONS */}
                  <div className="card" style={{ borderLeft: '4px solid #ef4444', background: '#fef2f2' }}>
                    <div className="card-header" style={{ marginBottom: '0.45rem' }}>
                      <h3 className="card-title" style={{ fontSize: '1.15rem', color: '#b91c1c', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <AlertTriangle size={18} color="#ef4444" /> Safety Precautions & Warning Signs
                      </h3>
                    </div>
                    <p style={{ fontSize: '0.85rem', color: '#991b1b', marginBottom: '0.65rem' }}>
                      Important red flags that require in-person medical evaluation:
                    </p>
                    <ul style={{ paddingLeft: '1.25rem', margin: 0, fontSize: '0.85rem', color: '#7f1d1d', lineHeight: '1.5' }}>
                      {safeArray(assessmentResult.when_to_see_doctor || [
                        "Fever exceeds 102°F (38.9°C) or lasts more than 3 consecutive days",
                        "Shortness of breath, rapid breathing, or chest tightness while resting",
                        "Inability to retain fluids, severe vomiting, or signs of dehydration (dark urine, dizziness)",
                        "Symptoms fail to improve after 7 to 10 days, or suddenly worsen"
                      ]).slice(0, 4).map((rule, i) => (
                        <li key={i} style={{ marginBottom: '0.25rem' }}>{safeText(rule)}</li>
                      ))}
                    </ul>
                  </div>

                  {/* SAFETY DISCLAIMER */}
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'center', padding: '0.5rem' }}>
                    ⚖️ <strong>Safety Disclaimer:</strong> AI Virtual Doctor is a clinical decision-support assistant and does not provide an independent confirmed medical diagnosis or prescription. Your summary is pending review by your physician in the Doctor Portal.
                  </div>

                  {/* ACTION BUTTONS */}
                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                    <button className="btn btn-primary" onClick={() => onNavigateTab('assessments')}>
                      View Full Clinical Report in Previous Assessments <ArrowRight size={16} />
                    </button>
                    <button className="btn btn-secondary" onClick={() => { setViewMode('history'); loadHistory(); }}>
                      <History size={15} /> View All Past Consultations
                    </button>
                    <button className="btn btn-secondary" onClick={handleRestart}>
                      <RotateCcw size={15} /> Start New Consultation
                    </button>
                  </div>

                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
