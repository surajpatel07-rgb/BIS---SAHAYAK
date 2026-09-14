import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/chat");
    } catch (err: any) {
      setError(err?.message ?? "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-full items-center justify-center bg-gradient-to-b from-brand-900 to-brand-700 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center text-white">
          <ShieldCheck className="mx-auto mb-2 h-10 w-10 text-saffron" />
          <h1 className="text-2xl font-bold">BIS Buddy</h1>
          <p className="text-sm text-white/60">
            Your AI Assistant for Indian Standards & BIS Services
          </p>
        </div>
        <form
          onSubmit={submit}
          className="space-y-4 rounded-2xl bg-white p-6 shadow-xl"
        >
          <h2 className="text-lg font-bold text-slate-900">Login</h2>
          {error && (
            <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
          )}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border px-3 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border px-3 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-xl bg-brand-600 py-2.5 font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <p className="text-center text-sm text-slate-500">
            No account?{" "}
            <Link to="/register" className="font-semibold text-brand-600 hover:underline">
              Register
            </Link>
          </p>
          <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-xs text-slate-500">
            <b>Demo accounts</b> (after running seed):<br />
            admin@bisbuddy.in / Admin@12345<br />
            demo@bisbuddy.in / Demo@12345
          </div>
        </form>
      </div>
    </div>
  );
}
