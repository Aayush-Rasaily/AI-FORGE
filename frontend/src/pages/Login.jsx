import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Lock, Shield, Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";

function Login() {
  const { login, loading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message || "Sign-in could not be completed.");
    }
  };

  return (
    <div className="forge-login">
      <form onSubmit={handleSubmit} className="forge-login-card">
        <div className="forge-login-brand">
          <span className="forge-brand-mark">
            <Shield className="h-5 w-5" />
          </span>
          <div>
            <h1>AI-FORGE</h1>
            <p>Forensic Intelligence</p>
          </div>
        </div>
        <label className="forge-field">
          <span>Email</span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label className="forge-field">
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error && <p className="forge-inline-error">{error}</p>}
        <button type="submit" className="forge-primary-action w-full" disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}
          Sign in
        </button>
      </form>
    </div>
  );
}

// Development remains explicitly opt-in; production fails closed unless the
// deployment deliberately opts out with VITE_AUTH_REQUIRED=false.
const AUTH_REQUIRED =
  import.meta.env.PROD
    ? import.meta.env.VITE_AUTH_REQUIRED !== "false"
    : import.meta.env.VITE_AUTH_REQUIRED === "true";

export function RequireAuth({ children }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!AUTH_REQUIRED) {
    return children;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}

export default Login;
