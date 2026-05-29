import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthProvider";
import { useToast } from "../context/ToastProvider";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) return toast("Password must be at least 8 characters", "error");
    setBusy(true);
    try {
      await register(email, password, name);
      nav("/");
    } catch (err) {
      toast((err as Error).message || "Registration failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-sm px-4 py-12">
      <h1 className="mb-6 text-2xl font-bold">Create account</h1>
      <form onSubmit={submit} className="card space-y-4 p-6">
        <input className="w-full rounded-lg border border-gray-300 px-3 py-2" placeholder="Full name (optional)"
          value={name} onChange={(e) => setName(e.target.value)} />
        <input className="w-full rounded-lg border border-gray-300 px-3 py-2" type="email" placeholder="Email"
          value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="w-full rounded-lg border border-gray-300 px-3 py-2" type="password" placeholder="Password (min 8 chars)"
          value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button className="btn-primary w-full" disabled={busy}>{busy ? "…" : "Sign up"}</button>
      </form>
      <p className="mt-4 text-center text-sm text-gray-500">
        Have an account? <Link to="/login" className="text-brand-600">Log in</Link>
      </p>
    </div>
  );
}
