import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import Investigation from "./pages/Investigation";
import SignatureVerification from "./pages/SignatureVerification";
import CopyMoveDetection from "./pages/CopyMoveDetection";
function App() {

  return (
    <BrowserRouter>

      <Routes>

        {/* Dashboard */}
        <Route
          path="/"
          element={<Dashboard />}
        />

        {/* Investigation */}
        <Route
          path="/investigation"
          element={<Investigation />}
        />

        {/* Signature Verification */}
        <Route
          path="/signature"
          element={<SignatureVerification />}
        />

        {/* Unknown routes */}
        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />

        {/* Copy Move Detection */}
        <Route
          path="/copy-move"
          element={<CopyMoveDetection />}
        />

      </Routes>

    </BrowserRouter>
  );
}

export default App;