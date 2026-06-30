import { Link, NavLink, useNavigate } from "react-router-dom";
import { Bot, ShoppingCart } from "lucide-react";
import { useAuth } from "../../context/AuthProvider";
import { useCart } from "../../hooks/useCart";
import { useUiStore } from "../../store/uiStore";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `relative text-sm transition-colors ${
    isActive ? "font-semibold text-brand-700" : "text-gray-600 hover:text-gray-900"
  }`;

export function Navbar() {
  const { user, logout } = useAuth();
  const { data: cart } = useCart();
  const setCartOpen = useUiStore((s) => s.setCartOpen);
  const nav = useNavigate();

  return (
    <header className="sticky top-0 z-30 border-b bg-white/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-lg font-bold tracking-tight text-gray-900">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-white shadow-sm">
            <Bot size={18} />
          </span>
          BuildRight <span className="text-brand-600">AI</span>
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
          <button
            className="relative grid h-9 w-9 place-items-center rounded-lg text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900"
            onClick={() => setCartOpen(true)}
            aria-label="Open cart"
          >
            <ShoppingCart size={20} />
            {cart && cart.item_count > 0 && (
              <span className="absolute -right-1 -top-1 grid h-5 min-w-[1.25rem] place-items-center rounded-full bg-brand-600 px-1 text-[0.7rem] font-semibold text-white shadow-sm">
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
