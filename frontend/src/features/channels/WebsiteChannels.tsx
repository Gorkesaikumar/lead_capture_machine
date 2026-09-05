import { useState } from "react";
import { useLeadForms, useCreateLeadForm, useUpdateLeadForm, useDeleteLeadForm, useLeadsList } from "@/api/leads.queries";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Plus, Code, Trash2, ArrowLeft, Copy, Globe, Eye, MoreVertical, Power, PowerOff } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";

import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { ErrorState } from "@/components/common/states/ErrorState";
import { EmptyState } from "@/components/common/states/EmptyState";

const getIntegrationCode = (publicId: string) => {
  let baseUrl = import.meta.env.VITE_API_BASE_URL || `${window.location.origin}/api/v1`;
  if (baseUrl.startsWith('/')) {
    baseUrl = `${window.location.origin}${baseUrl}`;
  }
  const apiUrl = `${baseUrl.replace(/\/$/, '')}/forms/${publicId}/submit/`;
  return `<form id="v4-lead-form" style="display:flex;flex-direction:column;gap:12px;max-width:400px;font-family:sans-serif;">
  <input type="text" name="name" placeholder="Name" required style="padding:8px;border:1px solid #ccc;border-radius:4px;" />
  <input type="email" name="email" placeholder="Email" style="padding:8px;border:1px solid #ccc;border-radius:4px;" />
  <input type="tel" name="phone" placeholder="Phone" style="padding:8px;border:1px solid #ccc;border-radius:4px;" />
  <textarea name="message" placeholder="Message" rows="4" style="padding:8px;border:1px solid #ccc;border-radius:4px;"></textarea>
  <button type="submit" style="padding:10px;background:#0f172a;color:white;border:none;border-radius:4px;cursor:pointer;">Submit</button>
</form>

<script>
document.getElementById('v4-lead-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());
  data.referrer = document.referrer;
  data.landing_page = window.location.href;

  try {
    const res = await fetch('${apiUrl}', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const result = await res.json();
    if(res.ok) {
      alert(result.message || "Success");
      form.reset();
    } else {
      alert("Error submitting form.");
    }
  } catch(err) {
    alert("Network error.");
  }
});
</script>`;
};

function CreateFormModal({ isOpen, onClose, onCreate, isPending }: any) {
  const [newFormName, setNewFormName] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const handleCreate = () => {
    onCreate({ name: newFormName, success_message: successMessage || "Thank you for your message. We will be in touch shortly." });
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => {
      if (!open) {
        setNewFormName("");
        setSuccessMessage("");
        onClose();
      }
    }}>
      <DialogContent className="max-w-4xl p-0 overflow-y-auto max-h-[90vh] bg-white">
        <div className="grid md:grid-cols-2">
          <div className="p-6 flex flex-col h-full border-b md:border-b-0 md:border-r border-slate-100">
            <DialogHeader className="mb-6">
              <DialogTitle className="text-xl">Create Lead Form</DialogTitle>
              <DialogDescription>
                Configure the fields and behavior for your new website form.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-5 flex-1">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-slate-900">Form Name</label>
                <Input
                  placeholder="e.g. Website Contact Page"
                  value={newFormName}
                  onChange={(e) => setNewFormName(e.target.value)}
                  className="w-full"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-slate-900">Success Message</label>
                <Input
                  placeholder="Thank you for your message..."
                  value={successMessage}
                  onChange={(e) => setSuccessMessage(e.target.value)}
                  className="w-full"
                />
                <p className="text-xs text-slate-500">Displayed to the user after they submit the form.</p>
              </div>
            </div>
            <DialogFooter className="mt-8 pt-4 border-t border-slate-100 flex-col sm:flex-row gap-2">
              <Button variant="outline" onClick={onClose} className="w-full sm:w-auto min-h-[44px]">Cancel</Button>
              <Button onClick={handleCreate} disabled={!newFormName.trim() || isPending} className="w-full sm:w-auto min-h-[44px]">
                {isPending ? "Creating..." : "Create Form"}
              </Button>
            </DialogFooter>
          </div>
          
          <div className="bg-slate-50/50 p-6 flex flex-col items-center justify-center relative min-h-[400px]">
            <div className="absolute top-4 left-4 text-xs font-semibold text-slate-400 uppercase tracking-widest">
              Live Preview
            </div>
            <div className="bg-white border border-slate-200 shadow-sm rounded-xl p-6 w-full max-w-sm mt-8">
              <form className="flex flex-col gap-3" onSubmit={(e) => e.preventDefault()}>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-700">Name</label>
                  <Input placeholder="John Doe" disabled className="bg-slate-50/50 w-full" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-700">Email</label>
                  <Input placeholder="john@example.com" disabled className="bg-slate-50/50 w-full" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-700">Phone</label>
                  <Input placeholder="(555) 000-0000" disabled className="bg-slate-50/50 w-full" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-700">Message</label>
                  <textarea 
                    className="flex min-h-[80px] w-full rounded-md border border-slate-200 bg-slate-50/50 px-3 py-2 text-sm shadow-sm" 
                    placeholder="How can we help?" 
                    disabled 
                  />
                </div>
                <Button className="w-full mt-2 min-h-[44px]" disabled>Submit</Button>
                {successMessage && (
                  <div className="mt-2 text-xs text-center text-green-600 bg-green-50 p-2 rounded-md">
                    {successMessage}
                  </div>
                )}
              </form>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function FormDetailView({ form, onBack, onToggleActive }: any) {
  const navigate = useNavigate();
  const { data: submissionsData, isLoading, error, refetch } = useLeadsList({ 
    source_channel: 'WEBSITE', 
    source_identifier: form.public_id 
  });
  
  const submissions = submissionsData?.results || submissionsData || [];
  const embedCode = getIntegrationCode(form.public_id);
  const apiUrl = `${window.location.origin}/api/v1/forms/${form.public_id}/submit/`;

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard!");
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack} className="rounded-full shrink-0">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-slate-900">{form.name}</h1>
            <Badge variant={form.is_active ? "default" : "secondary"} className={form.is_active ? "bg-emerald-500 hover:bg-emerald-600" : ""}>
              {form.is_active ? "Active" : "Disabled"}
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Created on {format(new Date(form.created_at), "MMMM d, yyyy")}
          </p>
        </div>
        <div className="ml-auto flex gap-2">
           <Button variant="outline" onClick={() => onToggleActive(form)}>
             {form.is_active ? <><PowerOff className="w-4 h-4 mr-2" /> Disable Form</> : <><Power className="w-4 h-4 mr-2" /> Enable Form</>}
           </Button>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Integration Instructions</CardTitle>
              <CardDescription>Follow these steps to add the form to your website.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="space-y-4 text-sm text-slate-700 bg-slate-50 p-4 rounded-lg border border-slate-100">
                  <p className="font-medium">1. Copy this code.</p>
                  <p className="font-medium">2. Add it to your website.</p>
                  <p className="font-medium">3. Publish your website.</p>
                  <p className="font-medium">4. Leads will appear in V4 Studio.</p>
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Embed Code</span>
                    <Button size="sm" variant="ghost" onClick={() => copyToClipboard(embedCode)}>
                      <Copy className="h-4 w-4 mr-2" /> Copy Code
                    </Button>
                  </div>
                  <div className="relative">
                    <pre className="bg-slate-900 text-slate-50 p-4 rounded-lg overflow-x-auto text-xs font-mono max-h-[300px] overflow-y-auto">
                      {embedCode}
                    </pre>
                  </div>
                </div>

                <div className="space-y-2 pt-4 border-t border-slate-100">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">API Endpoint URL</span>
                    <Button size="sm" variant="ghost" onClick={() => copyToClipboard(apiUrl)}>
                      <Copy className="h-4 w-4 mr-2" /> Copy URL
                    </Button>
                  </div>
                  <code className="block w-full p-3 bg-slate-100 rounded-md text-sm border border-slate-200 truncate">
                    {apiUrl}
                  </code>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Submissions</CardTitle>
              <CardDescription>{form.submissions_count !== undefined ? form.submissions_count : submissions.length} total leads captured</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <LoadingSkeleton rows={3} />
              ) : error ? (
                <ErrorState 
                  code="internal_server_error"
                  title="Failed to load submissions"
                  onRetry={refetch}
                />
              ) : submissions.length === 0 ? (
                <EmptyState
                  icon={<Globe className="h-6 w-6" />}
                  title="No submissions yet"
                  description="Leads will appear here once the form is active."
                />
              ) : (
                <div className="divide-y divide-slate-100">
                  {submissions.map((lead: any) => (
                    <div 
                      key={lead.id} 
                      className="py-3 group flex justify-between items-center cursor-pointer transition-colors" 
                      onClick={() => navigate(`/app/leads/${lead.id}`)}
                    >
                      <div>
                        <p className="font-medium text-sm text-slate-900 group-hover:text-blue-600 transition-colors">
                          {lead.customer?.display_name || lead.customer_name || "Unknown"}
                        </p>
                        <p className="text-xs text-slate-500">{format(new Date(lead.created_at), "MMM d, h:mm a")}</p>
                      </div>
                      <Badge variant="outline" className="text-[10px] uppercase bg-slate-50 group-hover:bg-blue-50 group-hover:border-blue-200">
                        {lead.status_display}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export function WebsiteChannels() {
  const { data: forms = [], isLoading, error, refetch } = useLeadForms();
  const createForm = useCreateLeadForm();
  const updateForm = useUpdateLeadForm();
  const deleteForm = useDeleteLeadForm();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedForm, setSelectedForm] = useState<any>(null);

  const handleCreate = async (payload: any) => {
    try {
      const newForm = await createForm.mutateAsync(payload);
      setIsCreateModalOpen(false);
      toast.success("Lead form created successfully");
      setSelectedForm(newForm); // Open the new form details immediately
    } catch (err) {
      toast.error("Failed to create form");
    }
  };

  const handleToggleActive = async (form: any) => {
    try {
      const updated = await updateForm.mutateAsync({
        id: form.id,
        is_active: !form.is_active,
      });
      toast.success(`Form ${!form.is_active ? 'activated' : 'disabled'}`);
      if (selectedForm && selectedForm.id === form.id) {
        setSelectedForm(updated);
      }
    } catch (err) {
      toast.error("Failed to update form status");
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this form? This cannot be undone.")) return;
    try {
      await deleteForm.mutateAsync(id);
      toast.success("Form deleted");
      if (selectedForm && selectedForm.id === id) {
        setSelectedForm(null);
      }
    } catch (err) {
      toast.error("Failed to delete form");
    }
  };

  if (isLoading) {
    return <LoadingSkeleton rows={5} />;
  }

  if (error) {
    return (
      <div className="p-4 md:p-8 max-w-6xl mx-auto">
        <ErrorState 
          code="internal_server_error"
          title="Failed to load forms"
          message="There was an error loading your website forms. Please try again."
          onRetry={refetch}
        />
      </div>
    );
  }

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto">
      {selectedForm ? (
        <FormDetailView 
          form={forms.find((f: any) => f.id === selectedForm.id) || selectedForm} 
          onBack={() => setSelectedForm(null)}
          onToggleActive={handleToggleActive}
          onDelete={handleDelete}
        />
      ) : (
        <div className="flex flex-col gap-8">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <h1 className="text-2xl font-semibold text-slate-900">Website Lead Capture</h1>
              <p className="text-sm text-slate-500 mt-1">
                Capture leads from your website and manage them inside V4 Studio.
              </p>
            </div>
            <Button onClick={() => setIsCreateModalOpen(true)} className="gap-2 w-full md:w-auto">
              <Plus className="h-4 w-4" />
              Create Form
            </Button>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            {forms.length === 0 ? (
              <EmptyState 
                icon={<Globe className="h-6 w-6" />}
                title="No website forms yet"
                description="Create a public form and embed it on your website to start capturing leads directly into V4 Studio."
                action={{ label: "Create your first form", onClick: () => setIsCreateModalOpen(true) }}
              />
            ) : (
              <div className="divide-y divide-slate-100">
                <div className="hidden md:grid grid-cols-12 gap-4 p-4 text-xs font-semibold text-slate-500 uppercase tracking-wider bg-slate-50/50">
                  <div className="col-span-4">Form Name</div>
                  <div className="col-span-2">Status</div>
                  <div className="col-span-2 text-center">Submissions</div>
                  <div className="col-span-3">Created Date</div>
                  <div className="col-span-1 text-right">Actions</div>
                </div>
                {forms.map((form: any) => (
                  <div key={form.id} className="flex flex-col md:grid md:grid-cols-12 gap-3 md:gap-4 p-4 items-start md:items-center hover:bg-slate-50/50 transition-colors relative">
                    {/* Form Name & Icon */}
                    <div className="col-span-4 flex items-center gap-3 w-full pr-8 md:pr-0">
                      <div className="h-8 w-8 rounded-md bg-blue-50 flex items-center justify-center text-blue-600 border border-blue-100 shrink-0">
                        <Code className="h-4 w-4" />
                      </div>
                      <div className="flex flex-col min-w-0 flex-1">
                        <span 
                          className="font-medium text-slate-900 truncate hover:text-blue-600 cursor-pointer"
                          onClick={() => setSelectedForm(form)}
                        >
                          {form.name}
                        </span>
                        <span className="text-xs text-slate-500 truncate md:hidden">
                          {format(new Date(form.created_at), "MMM d, yyyy")}
                        </span>
                      </div>
                    </div>
                    
                    {/* Mobile Actions Dropdown */}
                    <div className="absolute right-4 top-4 md:hidden">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreVertical className="h-4 w-4 text-slate-500" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => setSelectedForm(form)}>
                            <Eye className="w-4 h-4 mr-2" /> View Details
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setSelectedForm(form)}>
                            <Code className="w-4 h-4 mr-2" /> Integration
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => handleToggleActive(form)}>
                            {form.is_active ? <><PowerOff className="w-4 h-4 mr-2" /> Disable Form</> : <><Power className="w-4 h-4 mr-2" /> Enable Form</>}
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleDelete(form.id)} className="text-red-600 focus:text-red-600 focus:bg-red-50">
                            <Trash2 className="w-4 h-4 mr-2" /> Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>

                    {/* Mobile Row for Status & Submissions */}
                    <div className="flex items-center gap-4 md:contents w-full mt-1 md:mt-0">
                      <div className="col-span-2 flex items-center">
                        <Badge variant={form.is_active ? "default" : "secondary"} className={form.is_active ? "bg-emerald-500 hover:bg-emerald-600" : ""}>
                          {form.is_active ? "Active" : "Disabled"}
                        </Badge>
                      </div>

                      <div className="col-span-2 flex items-center gap-2 md:justify-center">
                        <span className="text-xs text-slate-500 md:hidden">Submissions:</span>
                        <Badge variant="outline" className="font-mono bg-white">
                          {form.submissions_count !== undefined ? form.submissions_count : 0}
                        </Badge>
                      </div>
                    </div>

                    {/* Desktop Created Date */}
                    <div className="col-span-3 hidden md:block text-sm text-slate-500">
                      {format(new Date(form.created_at), "MMM d, yyyy")}
                    </div>

                    {/* Desktop Actions */}
                    <div className="col-span-1 hidden md:flex justify-end">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreVertical className="h-4 w-4 text-slate-500" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => setSelectedForm(form)}>
                            <Eye className="w-4 h-4 mr-2" /> View Details
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setSelectedForm(form)}>
                            <Code className="w-4 h-4 mr-2" /> Integration
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => handleToggleActive(form)}>
                            {form.is_active ? <><PowerOff className="w-4 h-4 mr-2" /> Disable Form</> : <><Power className="w-4 h-4 mr-2" /> Enable Form</>}
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleDelete(form.id)} className="text-red-600 focus:text-red-600 focus:bg-red-50">
                            <Trash2 className="w-4 h-4 mr-2" /> Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <CreateFormModal 
        isOpen={isCreateModalOpen} 
        onClose={() => setIsCreateModalOpen(false)} 
        onCreate={handleCreate}
        isPending={createForm.isPending}
      />
    </div>
  );
}
