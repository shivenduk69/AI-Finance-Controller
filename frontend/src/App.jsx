import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

// Common Layout Elements
import Sidebar from './components/common/Sidebar';
import TopHeader from './components/common/TopHeader';
import FloatingAIAssistant from './components/ai/FloatingAIAssistant';

// Auth Pages
import LoginPage from './pages/auth/LoginPage';

// Merchant Pages (11 views)
import MerchantDashboardPage from './pages/merchant/MerchantDashboardPage';
import TransactionsLedgerPage from './pages/merchant/TransactionsLedgerPage';
import ExceptionsQueuePage from './pages/merchant/ExceptionsQueuePage';
import SettlementsLedgerPage from './pages/merchant/SettlementsLedgerPage';
import BankReconciliationPage from './pages/merchant/BankReconciliationPage';
import TaxAuditPage from './pages/merchant/TaxAuditPage';
import AIChatPage from './pages/merchant/AIChatPage';
import CashForecastingPage from './pages/merchant/CashForecastingPage';
import ReportsExportPage from './pages/merchant/ReportsExportPage';
import StoreSettingsPage from './pages/merchant/StoreSettingsPage';
import HelpdeskTicketsPage from './pages/merchant/HelpdeskTicketsPage';

// Admin Pages (13 views)
import AdminDashboardPage from './pages/admin/AdminDashboardPage';
import MerchantsRegistryPage from './pages/admin/MerchantsRegistryPage';
import StoresManagementPage from './pages/admin/StoresManagementPage';
import AdminTransactionsPage from './pages/admin/AdminTransactionsPage';
import AdminExceptionsReviewPage from './pages/admin/AdminExceptionsReviewPage';
import AdminSettlementsPage from './pages/admin/AdminSettlementsPage';
import AdminTicketsPage from './pages/admin/AdminTicketsPage';
import AdminNotificationsPage from './pages/admin/AdminNotificationsPage';
import AdminAIOpsPage from './pages/admin/AdminAIOpsPage';
import AdminKnowledgeBasePage from './pages/admin/AdminKnowledgeBasePage';
import AdminUserAccessPage from './pages/admin/AdminUserAccessPage';
import AdminAuditTrailPage from './pages/admin/AdminAuditTrailPage';
import AdminPlatformSettingsPage from './pages/admin/AdminPlatformSettingsPage';

function ProtectedLayout() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F9FC] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-semibold text-slate-500 font-outfit uppercase tracking-wider">
            Loading Workspace...
          </span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex min-h-screen bg-[#F7F9FC]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopHeader />
        <main className="flex-1 p-6 md:p-8 overflow-y-auto">
          <Routes>
            {/* Merchant Views */}
            <Route path="/" element={<MerchantDashboardPage />} />
            <Route path="/transactions" element={<TransactionsLedgerPage />} />
            <Route path="/exceptions" element={<ExceptionsQueuePage />} />
            <Route path="/settlements" element={<SettlementsLedgerPage />} />
            <Route path="/bank" element={<BankReconciliationPage />} />
            <Route path="/tax" element={<TaxAuditPage />} />
            <Route path="/insights" element={<AIChatPage />} />
            <Route path="/forecast" element={<CashForecastingPage />} />
            <Route path="/reports" element={<ReportsExportPage />} />
            <Route path="/settings" element={<StoreSettingsPage />} />
            <Route path="/tickets" element={<HelpdeskTicketsPage />} />

            {/* Admin Console Views */}
            <Route path="/admin" element={<AdminDashboardPage />} />
            <Route path="/admin/merchants" element={<MerchantsRegistryPage />} />
            <Route path="/admin/stores" element={<StoresManagementPage />} />
            <Route path="/admin/transactions" element={<AdminTransactionsPage />} />
            <Route path="/admin/exceptions" element={<AdminExceptionsReviewPage />} />
            <Route path="/admin/settlements" element={<AdminSettlementsPage />} />
            <Route path="/admin/tickets" element={<AdminTicketsPage />} />
            <Route path="/admin/notifications" element={<AdminNotificationsPage />} />
            <Route path="/admin/ai" element={<AdminAIOpsPage />} />
            <Route path="/admin/kb" element={<AdminKnowledgeBasePage />} />
            <Route path="/admin/users" element={<AdminUserAccessPage />} />
            <Route path="/admin/audit" element={<AdminAuditTrailPage />} />
            <Route path="/admin/config" element={<AdminPlatformSettingsPage />} />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>

      {/* Persistent Floating AI Assistant */}
      <FloatingAIAssistant />
    </div>
  );
}

export default function App() {
  const { user, loading } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={!loading && user ? <Navigate to={user.role === 'ADMIN' ? '/admin' : '/'} replace /> : <LoginPage />}
      />
      <Route path="/*" element={<ProtectedLayout />} />
    </Routes>
  );
}
