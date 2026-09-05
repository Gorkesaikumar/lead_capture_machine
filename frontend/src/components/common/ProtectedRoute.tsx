import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { LoadingSkeleton } from './states/LoadingSkeleton';
import { PageContainer } from './layout/PageContainer';
import { Button } from '@/components/ui/button';

export default function ProtectedRoute() {
  const { user, isLoading, logout } = useAuth();
  
  if (isLoading) {
    return (
      <div className="h-screen w-full flex flex-col bg-white">
        <div className="h-14 border-b border-gray-100 bg-white shrink-0" />
        <div className="flex flex-1">
          <div className="w-64 border-r border-gray-100 hidden md:block" />
          <PageContainer>
            <LoadingSkeleton rows={5} />
          </PageContainer>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!user.workspace) {
    if (user.is_superuser || user.is_staff) {
      return <Navigate to="/admin" replace />;
    }
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
        <div className="max-w-md rounded-xl border border-slate-200 bg-white p-8 text-center space-y-4">
          <h1 className="text-xl font-semibold text-slate-900">Workspace access required</h1>
          <p className="text-sm text-slate-600">Your account does not have access to an active workspace. Ask your workspace owner to invite you or restore your access.</p>
          <Button onClick={logout}>Sign out</Button>
        </div>
      </div>
    );
  }

  return <Outlet />;
}
