import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthProvider";
import { useCart } from "../../hooks/useCart";
import { useUiStore } from "../../store/uiStore";

export function Navbar() {
  const { user, logout } = useAuth();
  const { data: cart } = useCart();
  const setCartOpen = useUiStore((s) => s.setCartOpen);
  const nav = useNavigate();

  return (
    <header className="sticky top-0 z-30 border-b bg-white/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
        <Link to="/" className="text-xl font-bold text-brand-600">
          BuildRight Hardware
        </Link>
        <Link to="/" className="text-sm text-gray-600 hover:text-gray-900">
          Products
        </Link>
        <Link to="/about" className="text-sm text-gray-600 hover:text-gray-900">
          About
        </Link>
        {user && (
          <Link to="/orders" className="text-sm text-gray-600 hover:text-gray-900">
            My Orders
          </Link>
        )}
        {(user?.role === "manager" || user?.role === "admin") && (
          <Link to="/manager" className="text-sm text-gray-600 hover:text-gray-900">
            Dashboard
          </Link>
        )}
        {user?.role === "admin" && (
          <Link to="/admin" className="text-sm text-gray-600 hover:text-gray-900">
            Admin
          </Link>
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
