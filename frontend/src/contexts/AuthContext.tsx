import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { apiClient } from "@/api/client";

interface AdminUser {
  id: string | number;
  email: string;
  name?: string;
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
      setUser({ ...response.data, role: "ADMIN" });
    } catch {
      localStorage.removeItem("authToken");
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMe();
  }, []);

  const login = async (token: string) => {
    setIsLoading(true);
    await fetchMe(token);
  };

  const logout = async () => {
    try {
      await apiClient.post("/auth/logout/");
    } catch {
      // Ignore network errors on logout
    } finally {
      localStorage.removeItem("authToken");
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
