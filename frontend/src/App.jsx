import React, { useState, useEffect, Component } from 'react';
import Navbar from './components/Navbar';
import DisclaimerBanner from './components/DisclaimerBanner';
import ConsentModal from './components/ConsentModal';
import LoginView from './views/LoginView';
import PatientPortal from './portals/patient/PatientPortal';
import DoctorPortal from './portals/doctor/DoctorPortal';
import { getUser, getAuthToken, removeAuthToken, removeUser } from './api';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error("Smart Health AI UI caught error:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '2rem', maxWidth: '600px', margin: '3rem auto', background: '#fff', borderRadius: '12px', border: '1px solid #fecaca', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
          <h2 style={{ color: '#b91c1c', marginBottom: '0.75rem' }}>Something went wrong</h2>
          <p style={{ color: '#4b5563', fontSize: '0.9rem', marginBottom: '1.25rem' }}>
            A rendering error occurred while displaying this view. Your session and data are safe.
          </p>
          <button
            className="btn btn-primary"
            onClick={() => { this.setState({ hasError: false }); window.location.reload(); }}
          >
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [showConsentModal, setShowConsentModal] = useState(false);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const token = getAuthToken();
    const user = getUser();
    if (token && user) {
      setCurrentUser(user);
    }
    setInitialized(true);

    const handleAuthChanged = () => {
      const u = getUser();
      setCurrentUser(u);
    };

    window.addEventListener("auth-changed", handleAuthChanged);
    return () => window.removeEventListener("auth-changed", handleAuthChanged);
  }, []);

  const handleLogout = () => {
    removeAuthToken();
    removeUser();
    setCurrentUser(null);
  };

  if (!initialized) {
    return null;
  }

  return (
    <div className="app-container">
      {/* Prominent Persistent Medical Disclaimer Banner */}
      <DisclaimerBanner />

      {/* Main Navbar */}
      <Navbar
        currentUser={currentUser}
        onLogout={handleLogout}
        onOpenConsent={() => setShowConsentModal(true)}
      />

      {/* Body Content */}
      <ErrorBoundary>
        {!currentUser ? (
          <LoginView onLoginSuccess={(u) => setCurrentUser(u)} />
        ) : currentUser.role === 'doctor' ? (
          <DoctorPortal currentUser={currentUser} />
        ) : (
          <PatientPortal currentUser={currentUser} />
        )}
      </ErrorBoundary>

      {/* AI Consent Modal */}
      <ConsentModal
        isOpen={showConsentModal}
        onClose={() => setShowConsentModal(false)}
        onConsentUpdated={(status) => console.log("Consent updated:", status)}
      />
    </div>
  );
}
