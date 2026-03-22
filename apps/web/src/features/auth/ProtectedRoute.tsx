import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { canAccessAdmin, hasAnyRole } from "./permissions";

export function ProtectedRoute({ children, roles, fallbackTo }: { children: JSX.Element; roles?: string[]; fallbackTo?: string }) {
  const { isAuthenticated, ready, user } = useAuth();
  const location = useLocation();

  if (!ready) {
    return (
      <div className="app-shell">
        <main className="page-grid">
          <div className="card">Checking your session...</div>
        </main>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (roles?.length && !hasAnyRole(user, roles)) {
    const fallbackPath = fallbackTo ?? (canAccessAdmin(user) ? "/admin" : "/");
    return <Navigate to={fallbackPath} replace />;
  }

  return children;
}
