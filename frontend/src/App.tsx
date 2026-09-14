import { Navigate, Route, Routes } from "react-router-dom";
import { type ReactNode } from "react";
import { useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import LandingPage from "./pages/Landing";
import LoginPage from "./pages/Login";
import RegisterPage from "./pages/Register";
import ChatPage from "./pages/Chat";
import DocumentsPage from "./pages/Documents";
import DocumentDetailPage from "./pages/DocumentDetail";
import AdminPage from "./pages/Admin";
import SettingsPage from "./pages/Settings";

function RequireAuth({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireAdmin({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/chat" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/chat"
          element={
            <RequireAuth>
              <Layout>
                <ChatPage />
              </Layout>
            </RequireAuth>
          }
        />
        <Route
          path="/chat/:conversationId"
          element={
            <RequireAuth>
              <Layout>
                <ChatPage />
                </Layout>
            </RequireAuth>
          }
        />
        <Route
          path="/documents"
          element={
            <RequireAuth>
              <Layout>
                <DocumentsPage />
              </Layout>
            </RequireAuth>
          }
        />
        <Route
          path="/documents/:documentId"
          element={
            <RequireAuth>
              <Layout>
                <DocumentDetailPage />
              </Layout>
            </RequireAuth>
          }
        />
        <Route
          path="/admin"
          element={
            <RequireAdmin>
              <Layout>
                <AdminPage />
              </Layout>
            </RequireAdmin>
          }
        />
        <Route
          path="/settings"
          element={
            <RequireAuth>
              <Layout>
                <SettingsPage />
              </Layout>
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
  );
}
