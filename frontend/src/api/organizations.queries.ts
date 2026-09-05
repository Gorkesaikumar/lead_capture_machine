import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  logo?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  timezone?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const useCurrentOrganization = () => {
  return useQuery({
    queryKey: ["current_organization"],
    queryFn: async (): Promise<Organization> => {
      const { data } = await apiClient.get("/organizations/current/");
      return data;
    },
  });
};

export const useUpdateOrganization = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: Partial<Organization>) => {
      const { data } = await apiClient.patch("/organizations/current/", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["current_organization"] });
    },
  });
};
