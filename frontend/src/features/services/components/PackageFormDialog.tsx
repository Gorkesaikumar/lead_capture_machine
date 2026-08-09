import { useEffect } from "react";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useCreatePackage, useUpdatePackage } from "@/api/services.queries";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

const formSchema = z.object({
  name: z.string().min(2, "Name is required"),
  description: z.string().optional(),
  price: z.coerce.number().min(0, "Price cannot be negative"),
  duration_minutes_override: z.coerce.number().nullable().optional(),
  inclusions: z.string().optional(),
  is_active: z.boolean(),
  sort_order: z.coerce.number(),
});

type FormValues = z.infer<typeof formSchema>;

export function PackageFormDialog({ open, onOpenChange, serviceId, editingPackage }: { open: boolean, onOpenChange: (o: boolean) => void, serviceId: string, editingPackage?: any }) {
  const isEditing = !!editingPackage;
  const queryClient = useQueryClient();
  const createPkg = useCreatePackage();
  const updatePkg = useUpdatePackage();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "", description: "", price: 0, duration_minutes_override: null, inclusions: "", is_active: true, sort_order: 0
    }
  });

  useEffect(() => {
    if (open) {
      if (editingPackage) {
        let inclusionsText = "";
        if (Array.isArray(editingPackage.inclusions)) {
          inclusionsText = editingPackage.inclusions.join("\n");
        }
        form.reset({
          name: editingPackage.name,
          description: editingPackage.description || "",
          price: parseFloat(editingPackage.price),
          duration_minutes_override: editingPackage.duration_minutes_override,
          inclusions: inclusionsText,
          is_active: editingPackage.is_active,
          sort_order: editingPackage.sort_order,
        });
      } else {
        form.reset({ name: "", description: "", price: 0, duration_minutes_override: null, inclusions: "", is_active: true, sort_order: 0 });
      }
    }
  }, [open, editingPackage, form]);

  const onSubmit = async (values: FormValues) => {
    try {
      const inclusionsArray = values.inclusions?.split("\n").map(s => s.trim()).filter(Boolean) || [];
      const payload = {
        ...values,
        service: serviceId,
        inclusions: inclusionsArray,
        duration_minutes_override: values.duration_minutes_override || null
      };

      if (isEditing) {
        await updatePkg.mutateAsync({ id: editingPackage.id, ...payload });
        toast.success("Package updated successfully");
      } else {
        await createPkg.mutateAsync(payload);
        toast.success("Package added successfully");
      }
      queryClient.invalidateQueries({ queryKey: ["services"] });
      onOpenChange(false);
    } catch {
      toast.error(isEditing ? "Failed to update package" : "Failed to create package");
    }
  };

  const isSubmitting = createPkg.isPending || updatePkg.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Package" : "Add Package"}</DialogTitle>
          <DialogDescription>Add pricing tiers and inclusions.</DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit as any)} className="space-y-4">
            <FormField control={form.control as any} name="name" render={({ field }) => (
              <FormItem><FormLabel>Package Name</FormLabel><FormControl><Input placeholder="e.g. Premium Tier" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <div className="grid grid-cols-2 gap-4">
              <FormField control={form.control as any} name="price" render={({ field }) => (
                <FormItem><FormLabel>Price (INR)</FormLabel><FormControl><Input type="number" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control as any} name="duration_minutes_override" render={({ field }) => (
                <FormItem><FormLabel>Duration Override</FormLabel><FormControl><Input type="number" placeholder="Optional" value={field.value || ""} onChange={field.onChange} /></FormControl><FormMessage /></FormItem>
              )} />
            </div>
            <FormField control={form.control as any} name="inclusions" render={({ field }) => (
              <FormItem><FormLabel>Inclusions (One per line)</FormLabel><FormControl><Textarea placeholder="50 Edited Photos&#10;1 Album" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control as any} name="is_active" render={({ field }) => (
              <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4 shadow-sm">
                <div className="space-y-0.5"><FormLabel>Active Status</FormLabel></div>
                <FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl>
              </FormItem>
            )} />
            <DialogFooter className="mt-4">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button type="submit" className="bg-slate-900">
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isEditing ? "Save" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
