import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useCreateLeadTrigger, useUpdateLeadTrigger } from "@/api/leads.queries";
import { useServicesList } from "@/api/services.queries";
import { toast } from "sonner";
import { useEffect } from "react";

const formSchema = z.object({
  phrase: z.string().min(2, "Phrase must be at least 2 characters").max(255),
  match_type: z.enum(["EXACT", "CONTAINS", "REGEX"]),
  service: z.string().nullable().optional(),
  priority: z.enum(["LOW", "MEDIUM", "HIGH", "URGENT"]),
  is_active: z.boolean().default(true),
});

type FormValues = z.infer<typeof formSchema>;

export function LeadTriggerFormSheet({ open, onOpenChange, triggerToEdit }: any) {
  const createTrigger = useCreateLeadTrigger();
  const updateTrigger = useUpdateLeadTrigger();
  const { data: services } = useServicesList();

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema) as any,
    defaultValues: {
      phrase: "",
      match_type: "CONTAINS",
      service: null,
      priority: "MEDIUM",
      is_active: true,
    }
  });

  useEffect(() => {
    if (triggerToEdit) {
      form.reset({
        phrase: triggerToEdit.phrase,
        match_type: triggerToEdit.match_type,
        service: triggerToEdit.service || null,
        priority: triggerToEdit.priority,
        is_active: triggerToEdit.is_active,
      });
    } else {
      form.reset({
        phrase: "",
        match_type: "CONTAINS",
        service: null,
        priority: "MEDIUM",
        is_active: true,
      });
    }
  }, [triggerToEdit, open, form]);

  const onSubmit = async (values: FormValues) => {
    try {
      if (triggerToEdit) {
        await updateTrigger.mutateAsync({ id: triggerToEdit.id, ...values });
        toast.success("Trigger updated");
      } else {
        await createTrigger.mutateAsync(values);
        toast.success("Trigger created");
      }
      onOpenChange(false);
    } catch {
      toast.error("Failed to save trigger");
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-[450px] overflow-y-auto">
        <SheetHeader className="mb-6">
          <SheetTitle>{triggerToEdit ? "Edit Lead Trigger" : "Create Lead Trigger"}</SheetTitle>
          <SheetDescription>
            These triggers evaluate incoming Instagram/WhatsApp messages to automatically create and qualify leads.
          </SheetDescription>
        </SheetHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="phrase"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Keyword / Phrase</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. baby shoot" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="match_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Match Type</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select match type" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="CONTAINS">Contains Keyword</SelectItem>
                      <SelectItem value="EXACT">Exact Match</SelectItem>
                      <SelectItem value="REGEX">Regular Expression</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="service"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Mapped Service (Optional)</FormLabel>
                  <Select onValueChange={(val) => field.onChange(val === "none" ? null : val)} value={field.value || "none"}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select mapped service" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="none">-- None --</SelectItem>
                      {services?.map((s: any) => (
                        <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="priority"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Assign Priority</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select priority" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="LOW">Low</SelectItem>
                      <SelectItem value="MEDIUM">Medium</SelectItem>
                      <SelectItem value="HIGH">High</SelectItem>
                      <SelectItem value="URGENT">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">Active</FormLabel>
                    <FormMessage />
                  </div>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />

            <div className="pt-4 border-t">
              <Button type="submit" className="w-full" disabled={createTrigger.isPending || updateTrigger.isPending}>
                {(createTrigger.isPending || updateTrigger.isPending) ? "Saving..." : "Save Trigger"}
              </Button>
            </div>
          </form>
        </Form>
      </SheetContent>
    </Sheet>
  );
}

