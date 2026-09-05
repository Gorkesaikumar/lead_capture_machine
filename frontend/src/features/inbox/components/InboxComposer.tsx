import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

export function InboxComposer({ conversationId, channel, windowClosed }: { conversationId: string; channel: string; windowClosed: boolean }) {
  const cache = useQueryClient();
  const [text, setText] = useState("");
  const [template, setTemplate] = useState(false);
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("en_US");
  const [components, setComponents] = useState("[]");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const request = useRef<{ body: string; id: string } | null>(null);
  const send = useMutation({ mutationFn: async () => {
    const payload = template ? { template: { name, language, components: JSON.parse(components) } } : { text: text.trim() };
    const body = JSON.stringify(payload);
    if (request.current?.body !== body) request.current = { body, id: crypto.randomUUID() };
    return (await apiClient.post(`/conversations/${conversationId}/send/`, { ...payload, request_id: request.current.id })).data;
  }, onSuccess: () => { setText(""); setError(""); setNotice("Reply queued. Delivery status will appear in the conversation."); request.current = null; cache.invalidateQueries({ queryKey: ["conversations"] }); }, onError: (e: any) => { setNotice(""); setError(e.response?.data ? JSON.stringify(e.response.data) : "Request failed. Check the template configuration or retry."); } });
  return <form className="border-t bg-white p-4 space-y-3" onSubmit={e => { e.preventDefault(); send.mutate(); }}>
    {windowClosed && <p className="text-sm text-amber-800">The 24-hour reply window is closed.{channel === "WHATSAPP" ? " Use a Meta-approved template or wait for a new customer message." : " Wait for a new customer message."}</p>}
    {channel === "WHATSAPP" && <label className="flex gap-2 text-sm"><input type="checkbox" checked={template} onChange={e => setTemplate(e.target.checked)} />Use an approved WhatsApp template</label>}
    {template ? <><div className="flex gap-2"><Input aria-label="Approved template name" required value={name} onChange={e => setName(e.target.value)} placeholder="Approved template name" /><Input aria-label="Template language" required value={language} onChange={e => setLanguage(e.target.value)} /></div><Textarea aria-label="Template components JSON" value={components} onChange={e => setComponents(e.target.value)} /><p className="text-xs text-slate-500">Enter the template’s component parameters as JSON. Meta validates its approval, language and parameters.</p></> : <Textarea aria-label="Message" value={text} onChange={e => setText(e.target.value)} maxLength={1000} disabled={windowClosed} placeholder="Write a reply…" onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && text.trim() && !send.isPending && !windowClosed) { e.preventDefault(); send.mutate(); } }} />}
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}{notice && <p role="status" className="text-sm text-slate-500">{notice}</p>}
    <div className="flex justify-end"><Button type="submit" disabled={send.isPending || (!template && (windowClosed || !text.trim())) || (template && !name.trim())}>{send.isPending ? "Queueing…" : "Send reply"}</Button></div>
  </form>;
}
