import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from './contexts/AuthContext';
import { RealtimeProvider } from './contexts/RealtimeContext';
import AppShell from './layouts/AppShell';
import ProtectedRoute from './components/common/ProtectedRoute';
import Login from './features/auth/Login';
import Overview from './features/dashboard/Overview';
import LeadsList from './features/leads/LeadsList';
import LeadDetail from './features/leads/LeadDetail';
import CustomersList from './features/customers/CustomersList';
import ServicesList from './features/services/ServicesList';
import AvailabilitySettings from './features/availability/AvailabilitySettings';
import BookingCalendar from './features/calendar/BookingCalendar';
import BookingsList from './features/bookings/BookingsList';
import LeadTriggersSettings from './features/leads/LeadTriggersSettings';
import IntegrationsDashboard from './features/integrations/IntegrationsDashboard';
import AnalyticsDashboard from './features/analytics/AnalyticsDashboard';
import PublicBookingLayout from "./features/public/PublicBookingLayout";
import PublicBookingFlow from "./features/public/PublicBookingFlow";
import CustomerDetail from './features/customers/CustomerDetail';
import DesignSystemShowcase from './features/showcase/DesignSystemShowcase';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RealtimeProvider>
          <BrowserRouter>
          <Routes>
        <Route path="/book" element={<PublicBookingLayout />}>
          <Route path=":token" element={<PublicBookingFlow />} />
        </Route>
            <Route path="/login" element={<Login />} />
            
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<AppShell />}>
                <Route index element={<Overview />} />
          <Route path="leads" element={<LeadsList />} />
                <Route path="leads/:id" element={<LeadDetail />} />
                
                <Route path="conversations" element={<div className="p-8">Conversations</div>} />
                <Route path="customers" element={<CustomersList />} />
                <Route path="customers/:id" element={<CustomerDetail />} />
                
                <Route path="calendar" element={<BookingCalendar />} />
                <Route path="bookings" element={<BookingsList />} />
                <Route path="availability" element={<AvailabilitySettings />} />
                
                <Route path="services" element={<ServicesList />} />
                
                <Route path="triggers" element={<LeadTriggersSettings />} />
                <Route path="integrations" element={<IntegrationsDashboard />} />
                
                <Route path="analytics" element={<AnalyticsDashboard />} />
                
                {/* Temporary Showcase Route */}
                <Route path="design-system" element={<DesignSystemShowcase />} />
                
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster position="bottom-right" />
        </RealtimeProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;













