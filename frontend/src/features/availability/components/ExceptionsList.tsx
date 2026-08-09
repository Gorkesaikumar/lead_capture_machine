import { useState } from "react";
import { format } from "date-fns";
import { Calendar, Trash2, Clock, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useHolidays, useCreateHoliday, useDeleteHoliday, useBlockedPeriods, useCreateBlockedPeriod, useDeleteBlockedPeriod } from "@/api/scheduling.queries";
import { useServicesList } from "@/api/services.queries";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";

export function ExceptionsList() {
  const { data: holidays } = useHolidays();
  const { data: blocked } = useBlockedPeriods();
  const { data: services } = useServicesList();
  
  const createHoliday = useCreateHoliday();
  const deleteHoliday = useDeleteHoliday();
  const createBlocked = useCreateBlockedPeriod();
  const deleteBlocked = useDeleteBlockedPeriod();
  
  const queryClient = useQueryClient();

  const [holidayOpen, setHolidayOpen] = useState(false);
  const [hDate, setHDate] = useState("");
  const [hName, setHName] = useState("");

  const [blockedOpen, setBlockedOpen] = useState(false);
  const [bStart, setBStart] = useState("");
  const [bEnd, setBEnd] = useState("");
  const [bReason, setBReason] = useState("");
  const [bService, setBService] = useState("");

  const handleAddHoliday = async () => {
    if (!hDate || !hName) return toast.error("Date and name are required");
    try {
      await createHoliday.mutateAsync({ date: hDate, name: hName, is_active: true });
      toast.success("Holiday added");
      setHolidayOpen(false);
      setHDate(""); setHName("");
      queryClient.invalidateQueries({ queryKey: ["holidays"] });
    } catch {
      toast.error("Failed to add holiday");
    }
  };

  const handleAddBlocked = async () => {
    if (!bStart || !bEnd || !bReason) return toast.error("Start, end, and reason are required");
    if (new Date(bStart) >= new Date(bEnd)) return toast.error("End time must be after start time");
    try {
      await createBlocked.mutateAsync({ 
        starts_at: new Date(bStart).toISOString(), 
        ends_at: new Date(bEnd).toISOString(), 
        reason: bReason, 
        service: bService || null,
        is_active: true 
      });
      toast.success("Blocked period added");
      setBlockedOpen(false);
      setBStart(""); setBEnd(""); setBReason(""); setBService("");
      queryClient.invalidateQueries({ queryKey: ["blocked-periods"] });
    } catch {
      toast.error("Failed to add blocked period");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Holidays */}
      <div className="bg-white rounded-lg border shadow-sm flex flex-col">
        <div className="p-4 border-b flex justify-between items-center bg-slate-50/50">
          <div>
            <h3 className="font-semibold text-slate-800 flex items-center gap-2"><Calendar className="h-4 w-4 text-blue-500"/> Full Day Closures</h3>
            <p className="text-xs text-slate-500 mt-1">Studio is completely closed.</p>
          </div>
          <Button size="sm" onClick={() => setHolidayOpen(true)}><Plus className="mr-2 h-4 w-4" /> Add</Button>
        </div>
        <div className="p-0 flex-1 divide-y divide-slate-100">
          {holidays?.length === 0 && <div className="p-8 text-center text-slate-400 text-sm">No upcoming holidays.</div>}
          {holidays?.map((h: any) => (
            <div key={h.id} className="p-4 flex justify-between items-center hover:bg-slate-50">
              <div>
                <p className="font-medium text-slate-900 text-sm">{h.name}</p>
                <p className="text-xs text-slate-500">{format(new Date(h.date), "PPP")}</p>
              </div>
              <Button variant="ghost" size="icon" className="text-red-500" onClick={async () => {
                await deleteHoliday.mutateAsync(h.id);
                queryClient.invalidateQueries({ queryKey: ["holidays"] });
              }}><Trash2 className="h-4 w-4" /></Button>
            </div>
          ))}
        </div>
      </div>

      {/* Blocked Periods */}
      <div className="bg-white rounded-lg border shadow-sm flex flex-col">
        <div className="p-4 border-b flex justify-between items-center bg-slate-50/50">
          <div>
            <h3 className="font-semibold text-slate-800 flex items-center gap-2"><Clock className="h-4 w-4 text-slate-900"/> Blocked Time Windows</h3>
            <p className="text-xs text-slate-500 mt-1">Block specific hours for maintenance or events.</p>
          </div>
          <Button size="sm" onClick={() => setBlockedOpen(true)}><Plus className="mr-2 h-4 w-4" /> Add</Button>
        </div>
        <div className="p-0 flex-1 divide-y divide-slate-100">
          {blocked?.length === 0 && <div className="p-8 text-center text-slate-400 text-sm">No blocked periods.</div>}
          {blocked?.map((b: any) => (
            <div key={b.id} className="p-4 flex justify-between items-center hover:bg-slate-50">
              <div>
                <p className="font-medium text-slate-900 text-sm">{b.reason} {b.service && <span className="text-xs font-normal ml-2 bg-slate-100 px-2 py-0.5 rounded text-slate-600">Specific Service</span>}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {format(new Date(b.starts_at), "MMM d, h:mm a")} — {format(new Date(b.ends_at), "MMM d, h:mm a")}
                </p>
              </div>
              <Button variant="ghost" size="icon" className="text-red-500" onClick={async () => {
                await deleteBlocked.mutateAsync(b.id);
                queryClient.invalidateQueries({ queryKey: ["blocked-periods"] });
              }}><Trash2 className="h-4 w-4" /></Button>
            </div>
          ))}
        </div>
      </div>

      <Dialog open={holidayOpen} onOpenChange={setHolidayOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add Holiday Closure</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2"><label className="text-sm font-medium">Holiday Name</label><Input value={hName} onChange={e => setHName(e.target.value)} placeholder="e.g. Christmas" /></div>
            <div className="space-y-2"><label className="text-sm font-medium">Date</label><Input type="date" value={hDate} onChange={e => setHDate(e.target.value)} /></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setHolidayOpen(false)}>Cancel</Button><Button onClick={handleAddHoliday} className="bg-slate-900">Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={blockedOpen} onOpenChange={setBlockedOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Block Time Window</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2"><label className="text-sm font-medium">Reason</label><Input value={bReason} onChange={e => setBReason(e.target.value)} placeholder="e.g. Studio Maintenance" /></div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><label className="text-sm font-medium">Starts At</label><Input type="datetime-local" value={bStart} onChange={e => setBStart(e.target.value)} /></div>
              <div className="space-y-2"><label className="text-sm font-medium">Ends At</label><Input type="datetime-local" value={bEnd} onChange={e => setBEnd(e.target.value)} /></div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Restrict Specific Service (Optional)</label>
              <select className="w-full h-10 px-3 py-2 rounded-md border border-input bg-transparent text-sm" value={bService} onChange={e => setBService(e.target.value)}>
                <option value="">All Services (Complete Closure)</option>
                {services?.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setBlockedOpen(false)}>Cancel</Button><Button onClick={handleAddBlocked} className="bg-slate-900">Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
