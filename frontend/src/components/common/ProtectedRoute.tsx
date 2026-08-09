import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { LoadingSkeleton } from './states/LoadingSkeleton';
import { PageContainer } from './layout/PageContainer';

export default function ProtectedRoute() {
  const { user, isLoading } = useAuth();
  
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

  return <Outlet />;
}