import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "./client";

// --- Weekly Availability ---
export function useWeeklyAvailability() {
  return useQuery({
    queryKey: ["weekly-availability"],
    queryFn: async () => {
      const { data } = await apiClient.get("/scheduling/weekly/");
      return data.results || [];
    },
  });
}

export function useCreateWeeklyAvailability() {
  return useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await apiClient.post("/scheduling/weekly/", payload);
      return data;
    },
  });
}

export function useDeleteWeeklyAvailability() {
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/scheduling/weekly/${id}/`);
    },
  });
}

// --- Blocked Periods ---
export function useBlockedPeriods() {
  return useQuery({
    queryKey: ["blocked-periods"],
    queryFn: async () => {
      const { data } = await apiClient.get("/scheduling/blocked-periods/");
      return data.results || [];
    },
  });
}

export function useCreateBlockedPeriod() {
  return useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await apiClient.post("/scheduling/blocked-periods/", payload);
      return data;
    },
  });
}

export function useDeleteBlockedPeriod() {
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/scheduling/blocked-periods/${id}/`);
    },
  });
}

// --- Holidays ---
export function useHolidays() {
  return useQuery({
    queryKey: ["holidays"],
    queryFn: async () => {
      const { data } = await apiClient.get("/scheduling/holidays/");
      return data.results || [];
    },
  });
}

export function useCreateHoliday() {
  return useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await apiClient.post("/scheduling/holidays/", payload);
      return data;
    },
  });
}

export function useDeleteHoliday() {
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/scheduling/holidays/${id}/`);
    },
  });
}