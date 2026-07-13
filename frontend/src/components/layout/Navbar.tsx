import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { Menu, ShoppingCart, X } from "lucide-react";
import { Wordmark } from "../brand/Wordmark";
import { useAuth } from "../../context/AuthProvider";
import { useCart } from "../../hooks/useCart";
import { useUiStore } from "../../store/uiStore";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `relative text-sm transition-colors ${
    isActive ? "font-semibold text-brand-700" : "text-gray-600 hover:text-gray-900"
  }`;

const mobileLinkClass = ({ isActive }: { isActive: boolean }) =>
  `block rounded-lg px-3 py-2 text-sm transition-colors ${
    isActive ? "bg-brand-50 font-semibold text-brand-700" : "text-gray-700 hover:bg-gray-50"
  }`;

export function Navbar() {
  const { user, logout } = useAuth();
  const { data: cart } = useCart();
  const setCartOpen = useUiStore((s) => s.setCartOpen);
  const nav = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const links = [
    { to: "/", label: "Products", end: true, show: true },
    { to: "/about", label: "About", show: true },
    { to: "/how-to-test", label: "How to test", show: true },
    { to: "/orders", label: "My Orders", show: !!user },
    { to: "/manager", label: "Dashboard", show: user?.role === "manager" || user?.role === "admin" },
    { to: "/admin", label: "Admin", show: user?.role === "admin" },
  ].filter((l) => l.show);

  return (
    <header className="sticky top-0 z-30 border-b bg-white/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
        <Link to="/" aria-label="BuildRight AI home">
          <Wordmark />
        </Link>

        {/* Desktop links */}
        <div className="hidden items-center gap-4 md:flex">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={linkClass}>
              {l.label}
            </NavLink>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2 sm:gap-3">
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
              <span className="hidden text-sm text-gray-600 lg:inline">{user.email}</span>
              <button
                className="btn-ghost hidden md:inline-flex"
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
              <Link to="/login" className="btn-ghost hidden md:inline-flex">
                Log in
              </Link>
              <Link to="/register" className="btn-primary hidden md:inline-flex">
                Sign up
              </Link>
            </>
          )}
          {/* Mobile hamburger */}
          <button
            className="grid h-9 w-9 place-items-center rounded-lg text-gray-600 hover:bg-gray-100 md:hidden"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </nav>

      {/* Mobile menu panel */}
      {menuOpen && (
        <div className="animate-fade-in border-t bg-white px-4 py-3 md:hidden">
          <div className="space-y-1">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.end} className={mobileLinkClass} onClick={() => setMenuOpen(false)}>
                {l.label}
              </NavLink>
            ))}
          </div>
          <div className="mt-3 border-t pt-3">
            {user ? (
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm text-gray-500">{user.email}</span>
                <button
                  className="btn-ghost btn-sm"
                  onClick={async () => {
                    setMenuOpen(false);
                    await logout();
                    nav("/");
                  }}
                >
                  Log out
                </button>
              </div>
            ) : (
              <div className="flex gap-2">
                <Link to="/login" className="btn-ghost flex-1" onClick={() => setMenuOpen(false)}>
                  Log in
                </Link>
                <Link to="/register" className="btn-primary flex-1" onClick={() => setMenuOpen(false)}>
                  Sign up
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
