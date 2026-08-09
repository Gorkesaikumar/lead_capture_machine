import { useEffect } from "react";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetFooter } from "@/components/ui/sheet";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useCreateService, useUpdateService } from "@/api/services.queries";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

const formSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  description: z.string().optional(),
  duration_minutes: z.coerce.number().min(1, "Duration must be at least 1 minute"),
  buffer_before_minutes: z.coerce.number().min(0),
  buffer_after_minutes: z.coerce.number().min(0),
  base_price: z.coerce.number().min(0, "Base price cannot be negative"),
  is_active: z.boolean(),
  sort_order: z.coerce.number(),
});

type FormValues = z.infer<typeof formSchema>;

export function ServiceFormSheet({ open, onOpenChange, editingService }: { open: boolean, onOpenChange: (o: boolean) => void, editingService?: any }) {
  const isEditing = !!editingService;
  const queryClient = useQueryClient();
  const createService = useCreateService();
  const updateService = useUpdateService();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      description: "",
      duration_minutes: 60,
      buffer_before_minutes: 0,
      buffer_after_minutes: 0,
      base_price: 0,
      is_active: true,
      sort_order: 0,
    }
  });

  useEffect(() => {
    if (open) {
      if (editingService) {
        form.reset({
          name: editingService.name,
          description: editingService.description || "",
          duration_minutes: editingService.duration_minutes,
          buffer_before_minutes: editingService.buffer_before_minutes,
          buffer_after_minutes: editingService.buffer_after_minutes,
          base_price: parseFloat(editingService.base_price),
          is_active: editingService.is_active,
          sort_order: editingService.sort_order,
        });
      } else {
        form.reset({
          name: "", description: "", duration_minutes: 60, buffer_before_minutes: 0, buffer_after_minutes: 0, base_price: 0, is_active: true, sort_order: 0
        });
      }
    }
  }, [open, editingService, form]);

  const onSubmit = async (values: FormValues) => {
    try {
      if (isEditing) {
        await updateService.mutateAsync({ id: editingService.id, ...values });
        toast.success("Service updated successfully");
      } else {
        await createService.mutateAsync(values);
        toast.success("Service created successfully");
      }
      queryClient.invalidateQueries({ queryKey: ["services"] });
      onOpenChange(false);
    } catch {
      toast.error(isEditing ? "Failed to update service" : "Failed to create service");
    }
  };

  const isSubmitting = createService.isPending || updateService.isPending;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-[500px] overflow-y-auto">
        <SheetHeader className="mb-6">
          <SheetTitle>{isEditing ? "Edit Service" : "Add New Service"}</SheetTitle>
          <SheetDescription>Configure the core offerings and base pricing.</SheetDescription>
        </SheetHeader>
        
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit as any)} className="space-y-4">
            <FormField control={form.control as any} name="name" render={({ field }) => (
                <FormItem><FormLabel>Service Name</FormLabel><FormControl><Input placeholder="e.g. Baby Shoot" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control as any} name="description" render={({ field }) => (
                <FormItem><FormLabel>Description</FormLabel><FormControl><Textarea placeholder="Details about this service..." {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <div className="grid grid-cols-2 gap-4">
              <FormField control={form.control as any} name="duration_minutes" render={({ field }) => (
                <FormItem><FormLabel>Duration (mins)</FormLabel><FormControl><Input type="number" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control as any} name="base_price" render={({ field }) => (
                <FormItem><FormLabel>Base Price (INR)</FormLabel><FormControl><Input type="number" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <FormField control={form.control as any} name="buffer_before_minutes" render={({ field }) => (
                <FormItem><FormLabel>Buffer Before (mins)</FormLabel><FormControl><Input type="number" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control as any} name="buffer_after_minutes" render={({ field }) => (
                <FormItem><FormLabel>Buffer After (mins)</FormLabel><FormControl><Input type="number" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
            </div>
            <FormField control={form.control as any} name="sort_order" render={({ field }) => (
              <FormItem><FormLabel>Sort Order</FormLabel><FormControl><Input type="number" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control as any} name="is_active" render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4 shadow-sm">
                  <div className="space-y-0.5"><FormLabel className="text-base">Active Status</FormLabel><div className="text-sm text-slate-500">Visible and bookable by clients.</div></div>
                  <FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl>
                </FormItem>
            )} />
            <SheetFooter className="mt-8">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>Cancel</Button>
              <Button type="submit" className="bg-slate-900" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isEditing ? "Save Changes" : "Create Service"}
              </Button>
            </SheetFooter>
          </form>
        </Form>
      </SheetContent>
    </Sheet>
  );
}
