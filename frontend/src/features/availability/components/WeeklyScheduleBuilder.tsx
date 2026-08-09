import { useState } from "react";
import { useWeeklyAvailability, useCreateWeeklyAvailability, useDeleteWeeklyAvailability } from "@/api/scheduling.queries";
import { useQueryClient } from "@tanstack/react-query";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Trash2, Copy } from "lucide-react";
import { toast } from "sonner";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";

const DAYS = [
  { id: 0, label: "Monday" },
  { id: 1, label: "Tuesday" },
  { id: 2, label: "Wednesday" },
  { id: 3, label: "Thursday" },
  { id: 4, label: "Friday" },
  { id: 5, label: "Saturday" },
  { id: 6, label: "Sunday" }
];

export function WeeklyScheduleBuilder() {
  const { data: schedule, isLoading } = useWeeklyAvailability();
  const createAvail = useCreateWeeklyAvailability();
  const deleteAvail = useDeleteWeeklyAvailability();
  const queryClient = useQueryClient();

  const [newSlot, setNewSlot] = useState<{ dayId: number, start: string, end: string } | null>(null);

  const getPeriodsForDay = (dayId: number) => {
    return (schedule || []).filter((s: any) => s.weekday === dayId).sort((a: any, b: any) => a.start_time.localeCompare(b.start_time));
  };

  const handleAddSlot = async (dayId: number, start: string, end: string) => {
    if (!start || !end || start >= end) {
      toast.error("Invalid time period");
      return;
    }
    
    // Check overlaps
    const existing = getPeriodsForDay(dayId);
    const hasOverlap = existing.some((s: any) => 
      (start >= s.start_time.substring(0,5) && start < s.end_time.substring(0,5)) ||
      (end > s.start_time.substring(0,5) && end <= s.end_time.substring(0,5)) ||
      (start <= s.start_time.substring(0,5) && end >= s.end_time.substring(0,5))
    );

    if (hasOverlap) {
      toast.error("This period overlaps with an existing one");
      return;
    }

    try {
      await createAvail.mutateAsync({ weekday: dayId, start_time: start, end_time: end, is_active: true });
      setNewSlot(null);
      queryClient.invalidateQueries({ queryKey: ["weekly-availability"] });
    } catch {
      toast.error("Failed to add period");
    }
  };

  const handleDeleteSlot = async (id: string) => {
    try {
      await deleteAvail.mutateAsync(id);
      queryClient.invalidateQueries({ queryKey: ["weekly-availability"] });
    } catch {
      toast.error("Failed to delete period");
    }
  };

  const handleCopyMondayToWeekdays = async () => {
    const mondaySlots = getPeriodsForDay(0);
    if (mondaySlots.length === 0) {
      toast.error("Monday has no schedule to copy");
      return;
    }
    if (!confirm("This will overwrite schedules for Tuesday-Friday with Monday's schedule. Continue?")) return;

    try {
      for (let day = 1; day <= 4; day++) {
        const existing = getPeriodsForDay(day);
        for (const slot of existing) {
          await deleteAvail.mutateAsync(slot.id);
        }
        for (const slot of mondaySlots) {
          await createAvail.mutateAsync({ weekday: day, start_time: slot.start_time, end_time: slot.end_time, is_active: true });
        }
      }
      queryClient.invalidateQueries({ queryKey: ["weekly-availability"] });
      toast.success("Schedule copied successfully");
    } catch {
      toast.error("An error occurred while copying");
      queryClient.invalidateQueries({ queryKey: ["weekly-availability"] });
    }
  };

  if (isLoading) return <LoadingSkeleton rows={5} />;

  return (
    <div className="bg-white rounded-lg border shadow-sm">
      <div className="p-4 border-b flex justify-between items-center bg-slate-50/50">
        <h3 className="font-semibold text-slate-800">Standard Weekly Hours</h3>
        <Button variant="outline" size="sm" onClick={handleCopyMondayToWeekdays}>
          <Copy className="mr-2 h-4 w-4" /> Copy Mon to Weekdays
        </Button>
      </div>
      
      <div className="divide-y divide-gray-100">
        {DAYS.map(day => {
          const periods = getPeriodsForDay(day.id);
          const isOpen = periods.length > 0 || (newSlot?.dayId === day.id);

          return (
            <div key={day.id} className="p-5 flex flex-col md:flex-row gap-4 items-start md:items-center min-h-[80px]">
              <div className="w-48 flex items-center gap-3 shrink-0">
                <Switch 
                  checked={isOpen}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setNewSlot({ dayId: day.id, start: "09:00", end: "18:00" });
                    } else {
                      if(confirm(`Remove all periods for ${day.label}?`)) {
                        periods.forEach((p: any) => handleDeleteSlot(p.id));
                        setNewSlot(null);
                      }
                    }
                  }}
                />
                <span className="font-medium text-slate-900 w-24">{day.label}</span>
              </div>

              <div className="flex-1 flex flex-col gap-3">
                {!isOpen && <span className="text-slate-400 text-sm">Closed</span>}
                
                {periods.map((p: any) => (
                  <div key={p.id} className="flex items-center gap-3">
                    <div className="flex items-center gap-2 text-sm bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5">
                      <span className="text-slate-900 font-medium">{p.start_time.substring(0,5)}</span>
                      <span className="text-slate-400">—</span>
                      <span className="text-slate-900 font-medium">{p.end_time.substring(0,5)}</span>
                    </div>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-red-600" onClick={() => handleDeleteSlot(p.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}

                {newSlot?.dayId === day.id && (
                  <div className="flex items-center gap-3 mt-1">
                    <Input type="time" value={newSlot.start} onChange={e => setNewSlot({...newSlot, start: e.target.value})} className="w-32 h-9" />
                    <span className="text-slate-400">—</span>
                    <Input type="time" value={newSlot.end} onChange={e => setNewSlot({...newSlot, end: e.target.value})} className="w-32 h-9" />
                    <Button size="sm" onClick={() => handleAddSlot(day.id, newSlot.start, newSlot.end)}>Save</Button>
                    <Button variant="ghost" size="sm" onClick={() => setNewSlot(null)}>Cancel</Button>
                  </div>
                )}
                
                {isOpen && newSlot?.dayId !== day.id && (
                  <Button variant="ghost" size="sm" className="w-fit text-slate-500 mt-1 h-8" onClick={() => setNewSlot({ dayId: day.id, start: "", end: "" })}>
                    <Plus className="mr-2 h-3 w-3" /> Add period
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}