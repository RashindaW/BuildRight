import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../../context/AuthProvider";
import type { Role } from "../../types";

/**
 * Gate a route by authentication and (optionally) role.
 * Pass `roles` with the set of roles allowed to view the route
 * (include higher tiers explicitly, e.g. ["manager", "admin"]).
 */
export function ProtectedRoute({
  children,
  roles,
}: {
  children: ReactNode;
  roles?: Role[];
}) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-8 text-center text-gray-500">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}
