import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import Cases from "./pages/Cases";
import Investigation from "./pages/Investigation";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";
import Help from "./pages/Help";
import History from "./pages/History";
import SignatureVerification from "./pages/SignatureVerification";
import CopyMoveDetection from "./pages/CopyMoveDetection";
import Login, { RequireAuth } from "./pages/Login";
import { BackendProvider } from "./context/BackendConnectivity";
import { AuthProvider } from "./context/AuthContext";
import LegalPage from "./pages/LegalPage";

function App() {
  return (
    <BackendProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/privacy" element={<LegalPage type="privacy" />} />
            <Route path="/terms" element={<LegalPage type="terms" />} />
            <Route path="/cookies" element={<LegalPage type="cookies" />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
            <Route path="/cases" element={<RequireAuth><Cases /></RequireAuth>} />
            <Route path="/investigation" element={<RequireAuth><Investigation /></RequireAuth>} />
            <Route path="/reports" element={<RequireAuth><Reports /></RequireAuth>} />
            <Route path="/settings" element={<RequireAuth><Settings /></RequireAuth>} />
            <Route path="/help" element={<RequireAuth><Help /></RequireAuth>} />
            <Route path="/history" element={<RequireAuth><History /></RequireAuth>} />
            <Route path="/signature" element={<RequireAuth><SignatureVerification /></RequireAuth>} />
            <Route path="/signature-analysis" element={<RequireAuth><SignatureVerification /></RequireAuth>} />
            <Route path="/copy-move" element={<RequireAuth><CopyMoveDetection /></RequireAuth>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </BackendProvider>
  );
}

export default App;
