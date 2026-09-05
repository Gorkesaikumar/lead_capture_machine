// Development-only fixture: exercise the real auth and realtime providers.
import React, { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from '../src/contexts/AuthContext';
import { RealtimeProvider, useRealtime, useRealtimeEvent } from '../src/contexts/RealtimeContext';

const test = window as any;
const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
test.received = [];
test.invalidations = [];
const invalidate = client.invalidateQueries.bind(client);
client.invalidateQueries = ((options: any) => {
  test.invalidations.push(options.queryKey);
  return invalidate(options);
}) as typeof client.invalidateQueries;

function Probe() {
  const realtime = useRealtime();
  test.realtime = realtime;
  useRealtimeEvent('*', (payload, event) => test.received.push({ payload, type: event.type }));
  return <output data-testid="status">{realtime.status}</output>;
}

function Harness() {
  const auth = useAuth();
  const [mounted, setMounted] = useState(true);
  const [revision, setRevision] = useState(0);
  test.controls = { auth, setMounted, rerender: () => setRevision(value => value + 1) };
  return <><span data-testid="revision">{revision}</span><span data-testid="identity">{auth.user?.workspace?.id || 'none'}</span>
    {mounted && <RealtimeProvider><Probe /></RealtimeProvider>}</>;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode><QueryClientProvider client={client}><AuthProvider><Harness /></AuthProvider></QueryClientProvider></StrictMode>,
);
