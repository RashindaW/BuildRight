import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthProvider";
import { useCart } from "../../hooks/useCart";
import { useUiStore } from "../../store/uiStore";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm ${isActive ? "font-medium text-brand-700" : "text-gray-600 hover:text-gray-900"}`;

export function Navbar() {
  const { user, logout } = useAuth();
  const { data: cart } = useCart();
  const setCartOpen = useUiStore((s) => s.setCartOpen);
  const nav = useNavigate();

  return (
    <header className="sticky top-0 z-30 border-b bg-white/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-xl font-bold text-brand-700">
          🤖 Smart Handy Man
          <span className="badge bg-amber-100 font-normal text-amber-700">Sandbox</span>
        </Link>
        <NavLink to="/" end className={linkClass}>
          Products
        </NavLink>
        <NavLink to="/about" className={linkClass}>
          About
        </NavLink>
        <NavLink to="/how-to-test" className={linkClass}>
          How to test
        </NavLink>
        {user && (
          <NavLink to="/orders" className={linkClass}>
            My Orders
          </NavLink>
        )}
        {(user?.role === "manager" || user?.role === "admin") && (
          <NavLink to="/manager" className={linkClass}>
            Dashboard
          </NavLink>
        )}
        {user?.role === "admin" && (
          <NavLink to="/admin" className={linkClass}>
            Admin
          </NavLink>
        )}

        <div className="ml-auto flex items-center gap-3">
          {/* cart is available to guests + users */}
          <button className="relative" onClick={() => setCartOpen(true)} aria-label="Open cart">
            🛒
            {cart && cart.item_count > 0 && (
              <span className="absolute -right-2 -top-2 rounded-full bg-brand-600 px-1.5 text-xs text-white">
                {cart.item_count}
              </span>
            )}
          </button>
          {user ? (
            <>
              <span className="hidden text-sm text-gray-600 sm:inline">{user.email}</span>
              <button
                className="btn-ghost"
                onClick={async () => {
                  await logout();
                  nav("/");
                }}
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-ghost">
                Log in
              </Link>
              <Link to="/register" className="btn-primary">
                Sign up
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
