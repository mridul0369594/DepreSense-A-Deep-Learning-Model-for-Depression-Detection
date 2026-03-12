import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { SessionProvider } from "@/contexts/SessionContext";
import PrivateRoute from "@/components/PrivateRoute";

// Auth pages
import Login from "./pages/Login";
import LoginOTP from "./pages/LoginOTP";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";

// Layouts
import ClinicianLayout from "./layouts/ClinicianLayout";
import AdminLayout from "./layouts/AdminLayout";

// Clinician Dashboard pages
import DashboardHome from "./pages/dashboard/DashboardHome";
import MDDDetection from "./pages/dashboard/MDDDetection";
import MDDResults from "./pages/dashboard/MDDResults";
import BDITest from "./pages/dashboard/BDITest";
import PatientHistory from "./pages/dashboard/PatientHistory";
import SystemStatus from "./pages/dashboard/SystemStatus";
import Settings from "./pages/dashboard/Settings";

// Admin pages
import UserManagement from "./pages/admin/UserManagement";
import SystemLogs from "./pages/admin/SystemLogs";
import AdminSettings from "./pages/admin/AdminSettings";

import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <SessionProvider>
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<Login />} />
            <Route path="/login-otp" element={<LoginOTP />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />

            {/* Clinician Dashboard Home (no sidebar) */}
            <Route
              path="/dashboard"
              element={
                <PrivateRoute allowedRole="clinician">
                  <DashboardHome />
                </PrivateRoute>
              }
            />

            {/* Clinician Sub-pages (with sidebar) */}
            <Route
              path="/dashboard"
              element={
                <PrivateRoute allowedRole="clinician">
                  <ClinicianLayout />
                </PrivateRoute>
              }
            >
              <Route path="mdd-detection" element={<MDDDetection />} />
              <Route path="mdd-results" element={<MDDResults />} />
              <Route path="bdi-test" element={<BDITest />} />
              <Route path="patient-history" element={<PatientHistory />} />
              <Route path="system-status" element={<SystemStatus />} />
              <Route path="settings" element={<Settings />} />
            </Route>

            {/* Admin Panel (Protected) */}
            <Route
              path="/admin"
              element={
                <PrivateRoute allowedRole="admin">
                  <AdminLayout />
                </PrivateRoute>
              }
            >
              <Route index element={<UserManagement />} />
              <Route path="logs" element={<SystemLogs />} />
              <Route path="settings" element={<AdminSettings />} />
            </Route>

            {/* Catch-all */}
            <Route path="*" element={<NotFound />} />
          </Routes>
          </SessionProvider>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
