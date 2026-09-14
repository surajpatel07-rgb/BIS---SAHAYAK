import { useQuery } from "@tanstack/react-query";
import { Building2, Info, ShieldCheck, User } from "lucide-react";
import { api } from "../services/api";
import { useAuth, type UserMode } from "../context/AuthContext";

export default function SettingsPage() {
  const { user, mode, setMode } = useAuth();
  const config = useQuery({ queryKey: ["config"], queryFn: api.publicConfig });

  const modes: { id: UserMode; label: string; icon: typeof User; desc: string }[] = [
    {
      id: "consumer",
      label: "Consumer",
      icon: User,
      desc: "Simple explanations, product safety, how to verify the ISI mark and file complaints.",
    },
    {
      id: "industry",
      label: "Industry / Manufacturer",
      icon: Building2,
      desc: "Precise guidance on standards, compliance steps, documentation, testing and procedures.",
    },
  ];

  return (
    <div className="thin-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-6">
        <h1 className="text-xl font-bold text-slate-900">Settings</h1>
        <p className="mb-6 text-sm text-slate-500">Assistant behaviour and account preferences.</p>

        {/* Mode */}
        <div className="mb-6 rounded-2xl border bg-white p-5">
          <h2 className="mb-1 font-bold text-slate-900">Assistant mode</h2>
          <p className="mb-4 text-sm text-slate-500">
            Controls the tone and focus of answers. You can switch any time from the sidebar.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {modes.map((m) => (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={`rounded-2xl border-2 p-4 text-left transition ${
                  mode === m.id
                    ? "border-brand-600 bg-brand-50"
                    : "border-slate-200 bg-white hover:border-brand-300"
                }`}
              >
                <m.icon
                  className={`mb-2 h-6 w-6 ${
                    mode === m.id ? "text-brand-600" : "text-slate-400"
                  }`}
                />
                <div className="font-semibold text-slate-800">{m.label}</div>
                <div className="mt-1 text-xs text-slate-500">{m.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Account */}
        <div className="mb-6 rounded-2xl border bg-white p-5">
          <h2 className="mb-3 font-bold text-slate-900">Account</h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Name</dt>
              <dd className="font-medium">{user?.name}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Email</dt>
              <dd className="font-medium">{user?.email}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Role</dt>
              <dd className="font-medium capitalize">{user?.role}</dd>
            </div>
          </dl>
        </div>

        {/* System */}
        <div className="rounded-2xl border bg-white p-5">
          <h2 className="mb-1 flex items-center gap-2 font-bold text-slate-900">
            <ShieldCheck className="h-5 w-5 text-brand-600" /> System status
          </h2>
          <p className="mb-3 text-sm text-slate-500">
            Runtime configuration of the AI pipeline (read-only).
          </p>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">LLM provider</dt>
              <dd className="font-medium">
                {config.data?.llm_provider === "gemini"
                  ? "Gemini (configured)"
                  : "Local fallback (no GEMINI_API_KEY set)"}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Embeddings</dt>
              <dd className="font-medium">{config.data?.embedding_provider ?? "…"}</dd>
            </div>
          </dl>
          <p className="mt-3 flex items-start gap-2 rounded-xl bg-sky-50 p-3 text-xs text-sky-800">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            When GEMINI_API_KEY is configured in the backend .env, answers become fully generative.
            Without it, BIS Buddy still answers using an extractive method over the same indexed
            documents — no functionality is faked.
          </p>
        </div>
      </div>
    </div>
  );
}
