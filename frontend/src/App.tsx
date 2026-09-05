import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from './contexts/AuthContext';
import { RealtimeProvider } from './contexts/RealtimeContext';
import { Loader2 } from 'lucide-react';
import AppShell from './layouts/AppShell';
import ProtectedRoute from './components/common/ProtectedRoute';
import PrivacyPolicy from './features/legal/PrivacyPolicy';

const HomePage = React.lazy(() => import('./features/marketing/HomePage'));
const Login = React.lazy(() => import('./features/auth/Login'));
const Signup = React.lazy(() => import('./features/auth/Signup'));
const ForgotPassword = React.lazy(() => import('./features/auth/ForgotPassword'));
const ResetPassword = React.lazy(() => import('./features/auth/ResetPassword'));
const VerifyEmail = React.lazy(() => import('./features/auth/VerifyEmail'));
const OnboardingFlow = React.lazy(() => import('./features/onboarding/OnboardingFlow'));
const Overview = React.lazy(() => import('./features/dashboard/Overview'));
const LeadsList = React.lazy(() => import("./features/leads/LeadsList"));
const LeadDetail = React.lazy(() => import("./features/leads/LeadDetail"));

const LazyInboxLayout = React.lazy(() => import('./features/inbox').then(module => ({ default: module.InboxLayout })));

const CustomersList = React.lazy(() => import("./features/customers/CustomersList"));
const ServicesList = React.lazy(() => import('./features/services/ServicesList'));
const AvailabilitySettings = React.lazy(() => import('./features/availability/AvailabilitySettings'));
const BookingCalendar = React.lazy(() => import('./features/calendar/BookingCalendar'));
const BookingsList = React.lazy(() => import('./features/bookings/BookingsList'));
const AutomationsPage = React.lazy(() => import("./features/automations/AutomationsPage"));
const LeadTriggersSettings = React.lazy(() => import('./features/leads/LeadTriggersSettings'));

const ChannelsDashboard = React.lazy(() => import('./features/channels/ChannelsDashboard').then(module => ({ default: module.ChannelsDashboard })));
const WebsiteChannels = React.lazy(() => import('./features/channels/WebsiteChannels').then(module => ({ default: module.WebsiteChannels })));

const AnalyticsDashboard = React.lazy(() => import('./features/analytics/AnalyticsDashboard'));
const PublicBookingLayout = React.lazy(() => import("./features/public/PublicBookingLayout"));
const PublicBookingFlow = React.lazy(() => import("./features/public/PublicBookingFlow"));
const CustomerDetail = React.lazy(() => import('./features/customers/CustomerDetail'));
const TeamPage = React.lazy(() => import('./features/team/TeamPage'));
const AcceptInvitation = React.lazy(() => import('./features/team/AcceptInvitation'));
const SettingsLayout = React.lazy(() => import('./features/settings/SettingsLayout'));
const OrganizationSettings = React.lazy(() => import('./features/settings/OrganizationSettings'));
const SecuritySettings = React.lazy(() => import('./features/settings/SecuritySettings'));
const NotificationSettings = React.lazy(() => import('./features/settings/NotificationSettings'));
const SubscriptionPage = React.lazy(() => import('./features/subscription/SubscriptionPage'));

// Super Admin Module Imports
const AdminRouteGuard = React.lazy(() => import('./features/admin/AdminRouteGuard'));
const AdminLayout = React.lazy(() => import('./layouts/AdminLayout'));
const AdminLogin = React.lazy(() => import('./features/admin/AdminLogin'));
const AdminDashboard = React.lazy(() => import('./features/admin/AdminDashboard'));
const AdminUsers = React.lazy(() => import('./features/admin/AdminUsers'));
const AdminSubscriptions = React.lazy(() => import('./features/admin/AdminSubscriptions'));
const AdminRevenue = React.lazy(() => import('./features/admin/AdminRevenue'));
const AdminAuditLogs = React.lazy(() => import('./features/admin/AdminAuditLogs'));
const AdminSystemOverview = React.lazy(() => import('./features/admin/AdminSystemOverview'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function PlatformApp() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RealtimeProvider>
            <Suspense fallback={<div className="flex h-screen w-full items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-slate-400" /></div>}>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/book" element={<PublicBookingLayout />}>
                  <Route path=":token" element={<PublicBookingFlow />} />
                </Route>
                <Route path="/login" element={<Login />} />
                <Route path="/signup" element={<Signup />} />
                <Route path="/forgot-password" element={<ForgotPassword />} />
                <Route path="/reset-password" element={<ResetPassword />} />
                <Route path="/verify-email" element={<VerifyEmail />} />
                <Route path="/accept-invite" element={<AcceptInvitation />} />
                
                <Route element={<ProtectedRoute />}>
                  <Route path="/onboarding" element={<OnboardingFlow />} />

                  <Route path="/app" element={<AppShell />}>
                    <Route index element={<Overview />} />

                    <Route path="leads" element={<LeadsList />} />
                    <Route path="leads/:id" element={<LeadDetail />} />

                    <Route path="conversations" element={<LazyInboxLayout />} />
                    <Route path="customers" element={<CustomersList />} />
                    <Route path="customers/:id" element={<CustomerDetail />} />

                    <Route path="calendar" element={<BookingCalendar />} />
                    <Route path="bookings" element={<BookingsList />} />
                    <Route path="availability" element={<AvailabilitySettings />} />

                    <Route path="services" element={<ServicesList />} />

                    <Route path="automations" element={<AutomationsPage />} />
                    <Route path="triggers" element={<LeadTriggersSettings />} />

                    <Route path="analytics" element={<AnalyticsDashboard />} />

                    {/* Settings Navigation */}
                    <Route path="subscription" element={<Navigate to="/app/settings/subscription" replace />} />
                    <Route path="settings" element={<Navigate to="/app/settings/organization" replace />} />
                    <Route path="settings" element={<SettingsLayout />}>
                      <Route path="organization" element={<OrganizationSettings />} />
                      <Route path="team" element={<TeamPage />} />
                      <Route path="channels" element={<ChannelsDashboard />} />
                      <Route path="website" element={<WebsiteChannels />} />
                      <Route path="notifications" element={<NotificationSettings />} />
                      <Route path="security" element={<SecuritySettings />} />
                      <Route path="subscription" element={<SubscriptionPage />} />
                    </Route>

                    <Route path="*" element={<Navigate to="/app" replace />} />
                  </Route>
                </Route>

                {/* Super Admin Routes */}
                <Route path="/admin/login" element={<AdminLogin />} />
                <Route path="/admin" element={<AdminRouteGuard />}>
                  <Route element={<AdminLayout />}>
                    <Route index element={<AdminDashboard />} />
                    <Route path="users" element={<AdminUsers />} />
                    <Route path="subscriptions" element={<AdminSubscriptions />} />
                    <Route path="revenue" element={<AdminRevenue />} />
                    <Route path="analytics" element={<AdminDashboard />} />
                    <Route path="audit-logs" element={<AdminAuditLogs />} />
                    <Route path="system" element={<AdminSystemOverview />} />
                  </Route>
                </Route>
              </Routes>
            </Suspense>
          <Toaster position="bottom-right" />
        </RealtimeProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public legal content must never mount session restoration or authenticated sockets. */}
        <Route path="/privacy-policy" element={<PrivacyPolicy />} />
        <Route path="*" element={<PlatformApp />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
