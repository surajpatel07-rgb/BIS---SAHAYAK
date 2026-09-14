import { useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import {
  Building2,
  FileSearch,
  LayoutDashboard,
  LogOut,
  MessageSquarePlus,
  MessagesSquare,
  Settings as SettingsIcon,
  ShieldCheck,
  User as UserIcon,
} from "lucide-react";
import { useAuth, type UserMode } from "../context/AuthContext";
import { api } from "../services/api";
import { useQuery } from "@tanstack/react-query";

const MODES: { id: UserMode; label: string; icon: typeof UserIcon; hint: string }[] = [
  { id: "consumer", label: "Consumer", icon: UserIcon, hint: "Simple guidance, safety, ISI mark" },
  { id: "industry", label: "Industry", icon: Building2, hint: "Compliance, certification, testing" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, mode, setMode, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { conversationId } = useParams();
  const [search, setSearch] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const conversations = useQuery({
    queryKey: ["conversations", search],
    queryFn: () => api.conversations(search),
  });

  const nav = (path: string) => {
    navigate(path);
    setSidebarOpen(false);
  };

  const activeConvId = Number(conversationId) || null;

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-72 transform bg-brand-900 text-white transition-transform lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex items-center gap-3 px-5 pt-5 pb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10">
              <ShieldCheck className="h-6 w-6 text-saffron" />
            </div>
            <div>
              <div className="text-lg font-bold leading-tight">BIS Buddy</div>
              <div className="text-[11px] text-white/60">Standards & BIS Services</div>
            </div>
          </div>

          {/* Mode switch */}
          <div className="px-4 pb-3">
            <div className="rounded-xl bg-white/5 p-1.5">
              <div className="grid grid-cols-2 gap-1">
                {MODES.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setMode(m.id)}
                    title={m.hint}
                    className={`flex items-center justify-center gap-1.5 rounded-lg px-2 py-2 text-sm font-medium transition ${
                      mode === m.id
                        ? "bg-white text-brand-800 shadow"
                        : "text-white/70 hover:bg-white/10"
                    }`}
                  >
                    <m.icon className="h-4 w-4" />
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* New chat */}
          <div className="px-4">
            <button
              onClick={() => nav("/chat")}
              className="flex w-full items-center gap-2 rounded-xl bg-saffron px-3 py-2.5 text-sm font-semibold text-brand-900 transition hover:brightness-110"
            >
              <MessageSquarePlus className="h-4 w-4" />
              New Chat
            </button>
          </div>

          {/* Recent chats */}
          <div className="mt-4 px-4">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search chats..."
              className="w-full rounded-lg bg-white/10 px-3 py-2 text-sm text-white placeholder-white/40 outline-none focus:bg-white/15"
            />
          </div>
          <div className="thin-scroll mt-2 flex-1 overflow-y-auto px-3 pb-4">
            <div className="flex items-center gap-2 px-2 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-white/40">
              <MessagesSquare className="h-3.5 w-3.5" /> Recent Chats
            </div>
            {(conversations.data ?? []).map((c) => (
              <button
                key={c.id}
                onClick={() => nav(`/chat/${c.id}`)}
                className={`block w-full truncate rounded-lg px-3 py-2 text-left text-sm transition ${
                  activeConvId === c.id
                    ? "bg-white/15 text-white"
                    : "text-white/75 hover:bg-white/10"
                }`}
                title={c.title}
              >
                <span className="mr-1.5 text-[10px] uppercase text-white/40">
                  {c.mode === "industry" ? "IND" : "CON"}
                </span>
                {c.title}
              </button>
            ))}
            {conversations.data && conversations.data.length === 0 && (
              <div className="px-3 py-2 text-sm text-white/40">No conversations yet</div>
            )}
          </div>

          {/* Nav links */}
          <div className="border-t border-white/10 px-4 py-3">
            <div className="space-y-1">
              {[
                { to: "/documents", label: "Documents", icon: FileSearch },
                ...(user?.role === "admin"
                  ? [{ to: "/admin", label: "Admin Dashboard", icon: LayoutDashboard }]
                  : []),
                { to: "/settings", label: "Settings", icon: SettingsIcon },
              ].map((item) => (
                <button
                  key={item.to}
                  onClick={() => nav(item.to)}
                  className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition ${
                    location.pathname.startsWith(item.to)
                      ? "bg-white/15 text-white"
                      : "text-white/75 hover:bg-white/10"
                  }`}
                >
                  <item.icon className="h-4 w-4" /> {item.label}
                </button>
              ))}
            </div>
            <div className="mt-3 flex items-center justify-between rounded-lg bg-white/5 px-3 py-2">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{user?.name}</div>
                <div className="truncate text-[11px] text-white/50">
                  {user?.email} {user?.role === "admin" && "· admin"}
                </div>
              </div>
              <button
                onClick={logout}
                title="Logout"
                className="rounded-lg p-2 text-white/60 hover:bg-white/10 hover:text-white"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile overlay + top bar */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center justify-between border-b bg-white px-4 py-2.5 lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-lg p-2 hover:bg-slate-100"
            aria-label="Open menu"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 6h18M3 12h18M3 18h18" strokeLinecap="round" />
            </svg>
          </button>
          <span className="font-bold text-brand-800">BIS Buddy</span>
          <div className="w-9" />
        </div>
        <main className="min-h-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
