import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";

interface Workspace {
  id: string;
  name: string;
  role: "OWNER" | "ADMIN" | "MEMBER";
}

interface AdminUser {
  id: string | number;
  email: string;
  name?: string;
  full_name?: string;
  is_active?: boolean;
  is_staff?: boolean;
  is_superuser?: boolean;
  workspace: Workspace | null;
  role: "ADMIN";
}

interface AuthContextType {
  user: AdminUser | null;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<AdminUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchMe = async (token?: string) => {
    try {
      const currentToken = token || localStorage.getItem("authToken");
      if (!currentToken) throw new Error("No token");
      
      if (token) {
        localStorage.setItem("authToken", token);
      }
      
      const response = await apiClient.get("/auth/me/");
      const profile = response.data;
      if (!profile || typeof profile !== "object" || Array.isArray(profile)
        || !["string", "number"].includes(typeof profile.id)
        || typeof profile.email !== "string" || profile.is_active !== true
        || typeof profile.is_staff !== "boolean" || typeof profile.is_superuser !== "boolean"
        || !Array.isArray(profile.workspaces)) {
        throw new Error("Invalid current-user response");
      }
      const workspaces: Workspace[] = response.data.workspaces || [];
      const workspace = workspaces.find(item => item.id === localStorage.getItem("organizationId"))
        || workspaces[0] || null;
      if (workspace) {
        localStorage.setItem("organizationId", workspace.id);
      } else {
        localStorage.removeItem("organizationId");
      }
      setUser({ ...response.data, workspace, role: "ADMIN" });
    } catch (error) {
      localStorage.removeItem("authToken");
      localStorage.removeItem("organizationId");
      queryClient.clear();
      setUser(null);
      // Initial restoration can finish signed out; an explicit login must
      // reject so its caller cannot navigate after a failed profile request.
      if (token) throw error;
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMe();
  }, []);

  const login = async (token: string) => {
    setIsLoading(true);
    await queryClient.cancelQueries();
    queryClient.clear();
    localStorage.removeItem("organizationId");
    await fetchMe(token);
  };

  const logout = async () => {
    try {
      await apiClient.post("/auth/logout/");
    } catch {
      // Ignore network errors on logout
    } finally {
      localStorage.removeItem("authToken");
      localStorage.removeItem("organizationId");
      queryClient.clear();
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
