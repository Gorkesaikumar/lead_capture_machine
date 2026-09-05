import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";

export default function AcceptInvitation() {
  const { user, isLoading } = useAuth();
  const [params] = useSearchParams();
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const cache = useQueryClient();
  const token = params.get("token");
  async function accept() {
    setPending(true);
    try {
      const response = await apiClient.post("/organizations/invitations/accept/", { token });
      await cache.cancelQueries();
      cache.clear();
      localStorage.setItem("organizationId", response.data.organization_id);
      window.location.assign("/app");
    } catch (e: any) { setMessage(e.response?.data?.detail || "Could not accept this invitation."); }
    finally { setPending(false); }
  }
  return <main className="max-w-lg mx-auto p-8 space-y-5"><h1 className="text-2xl font-semibold">Join your studio team</h1>{isLoading ? <p>Loading account…</p> : !token ? <p>This invitation link is incomplete.</p> : !user ? <p><Link className="underline" to="/login">Sign in</Link> with the invited email address, then reopen this invitation link. New users can <Link className="underline" to="/signup">create an account</Link> first.</p> : <><p>Signed in as {user.email}.</p><Button disabled={pending} onClick={accept}>{pending ? "Joining…" : "Accept invitation"}</Button></>}{message && <p role="alert">{message}</p>}</main>;
}
