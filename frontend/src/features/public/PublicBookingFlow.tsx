import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { usePublicBookingLink, usePublicAvailability, useConfirmPublicBooking } from "@/api/publicBookings.queries";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { format, parseISO } from "date-fns";
import { CheckCircle2, Calendar as CalendarIcon, AlertCircle, ChevronRight, Camera, User, Phone, Mail, FileText, Check, ArrowLeft } from "lucide-react";

type Step = "loading" | "service" | "details" | "date" | "customer" | "review" | "success";

export default function PublicBookingFlow() {
  const { token } = useParams<{ token: string }>();
  
  const [step, setStep] = useState<Step>("loading");
  
  // Selection state
  const [selectedServiceId, setSelectedServiceId] = useState<string | null>(null);
  const [selectedPackageId, setSelectedPackageId] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  
  // Customer form state
  const [customerName, setCustomerName] = useState("");
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [email, setEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [formError, setFormError] = useState("");
  const [conflictError, setConflictError] = useState<string | null>(null);

  const { data: linkInfo, isLoading: isLoadingLink, isError: isLinkError } = usePublicBookingLink(token || "");
  
  useEffect(() => {
    if (linkInfo && !isLoadingLink && !isLinkError) {
      if (!linkInfo.service) {
        setStep("service");
      } else {
        setSelectedServiceId(linkInfo.service.id);
        if (linkInfo.package) {
          setSelectedPackageId(linkInfo.package.id);
        }
        if (linkInfo.customer_name) {
            setCustomerName(linkInfo.customer_name);
        }
        setStep("date");
      }
    }
  }, [linkInfo, isLoadingLink, isLinkError]);

  const dateStr = selectedDate ? format(selectedDate, "yyyy-MM-dd") : undefined;
  
  const activeServiceId = linkInfo?.service?.id || selectedServiceId;
  const { data: availability, isLoading: isLoadingSlots } = usePublicAvailability(token || "", dateStr, activeServiceId);

  const confirmBooking = useConfirmPublicBooking();

  if (isLoadingLink || step === "loading") {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-500">
        <div className="w-10 h-10 border-4 border-slate-100 border-t-slate-800 rounded-full animate-spin mb-6" />
        <p className="text-sm tracking-wide uppercase text-slate-400 font-medium">Preparing your session...</p>
      </div>
    );
  }

  if (isLinkError || !linkInfo) {
    return (
      <Card className="border-red-100 shadow-sm mt-12 max-w-md mx-auto">
        <CardContent className="pt-8 pb-8 text-center px-6">
          <div className="w-14 h-14 rounded-full bg-red-50 text-red-500 flex items-center justify-center mx-auto mb-5">
            <AlertCircle className="w-7 h-7" />
          </div>
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Link Unavailable</h2>
          <p className="text-slate-500 text-sm">
            This booking link is invalid, expired, or has already been used. Please contact the studio for a new link.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (linkInfo.is_used) {
    const booking = linkInfo.booking;
    return (
      <div className="flex flex-col items-center justify-center text-center mt-16 px-4 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-2xl mx-auto">
        <div className="w-24 h-24 rounded-full bg-slate-900 text-white flex items-center justify-center mb-8 shadow-xl">
          <CheckCircle2 className="w-12 h-12" />
        </div>
        <h1 className="text-4xl font-semibold tracking-tight text-slate-900 mb-3">Booking Confirmed</h1>
        <p className="text-slate-600 text-lg mb-10 max-w-md">
          {linkInfo.customer_name ? `Thank you, ${linkInfo.customer_name.split(' ')[0]}. ` : ""}Your session is confirmed!
        </p>
        
        {booking && (
          <Card className="w-full text-left shadow-md rounded-2xl border-slate-200 overflow-hidden">
            <CardContent className="p-8 space-y-6 bg-slate-50/50">
              <div>
                <p className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-1.5">Date</p>
                <p className="text-xl font-semibold text-slate-900">{format(parseISO(booking.starts_at), "d MMMM yyyy")}</p>
              </div>
              <div className="border-t border-slate-200 pt-6">
                <p className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-1.5">Time</p>
                <p className="text-xl font-semibold text-slate-900">{format(parseISO(booking.starts_at), "h:mm a")}</p>
              </div>
              <div className="border-t border-slate-200 pt-6">
                <p className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-1.5">Service</p>
                <p className="text-xl font-semibold text-slate-900">{booking.package_name ? `${booking.service_name} - ${booking.package_name}` : booking.service_name}</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  const activeService = linkInfo.service || linkInfo.available_services?.find((s: any) => s.id === selectedServiceId);
  const activePackage = linkInfo.package || (activeService?.packages?.find((p: any) => p.id === selectedPackageId));

  const serviceName = activePackage?.name ? `${activeService?.name} - ${activePackage.name}` : activeService?.name || "Service";
  const servicePrice = activePackage?.price || activeService?.base_price || 0;
  const serviceDuration = activePackage?.effective_duration_minutes || activeService?.duration_minutes || 0;
  const inclusions = activePackage?.inclusions || [];

  const handleCustomerSubmit = () => {
    setFormError("");
    if (!customerName.trim()) {
      setFormError("Full Name is required.");
      return;
    }
    if (!whatsappNumber.trim()) {
      setFormError("WhatsApp Number is required for confirmation.");
      return;
    }
    setStep("review");
  };

  const handleConfirm = async () => {
    if (!selectedSlot || !token || !activeServiceId) return;
    
    setConflictError(null);
    try {
      await confirmBooking.mutateAsync({
        token,
        starts_at: selectedSlot,
        customer_name: customerName.trim(),
        customer_phone: whatsappNumber.trim(),
        customer_email: email.trim() || undefined,
        customer_notes: notes.trim(),
        service_id: activeServiceId,
        package_id: selectedPackageId || undefined,
      });
      setStep("success");
    } catch (error: any) {
      if (error.response?.status === 409) {
        setConflictError("That time slot was just booked by someone else. Please choose another available slot.");
        setStep("date");
        setSelectedSlot(null);
      } else {
        setConflictError(error.response?.data?.message || "An error occurred while booking. Please try again.");
      }
    }
  };

  // --- Step 0: SERVICE SELECTION ---
  if (step === "service") {
    const services = linkInfo.available_services || [];
    if (services.length === 0) {
      return (
        <Card className="border-slate-200 shadow-sm mt-12 max-w-md mx-auto">
          <CardContent className="pt-8 pb-8 text-center px-6">
            <div className="w-14 h-14 rounded-full bg-slate-50 text-slate-400 flex items-center justify-center mx-auto mb-5">
              <Camera className="w-7 h-7" />
            </div>
            <h2 className="text-xl font-semibold text-slate-900 mb-2">No Services Available</h2>
            <p className="text-slate-500 text-sm">
              There are currently no services available for online booking. Please contact the studio directly.
            </p>
          </CardContent>
        </Card>
      );
    }
    
    return (
      <div className="space-y-8 animate-in slide-in-from-bottom-4 duration-500 pb-10 max-w-2xl mx-auto">
        <div className="text-center space-y-2 mt-4">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Select a Service</h1>
          <p className="text-slate-500">Choose the type of photoshoot you'd like to book.</p>
        </div>
        
        <div className="grid gap-4">
          {services.map((svc: any) => (
            <Card 
              key={svc.id} 
              className="cursor-pointer border-slate-200 hover:border-slate-800 hover:shadow-md transition-all duration-300"
              onClick={() => {
                setSelectedServiceId(svc.id);
                if (svc.packages && svc.packages.length > 0) {
                  setSelectedPackageId(svc.packages[0].id);
                } else {
                  setSelectedPackageId(null);
                }
                setStep("details");
              }}
            >
              <CardContent className="p-6 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-medium text-slate-900">{svc.name}</h3>
                  <div className="flex items-center gap-4 mt-2">
                    <span className="text-slate-900 font-medium">₹{svc.base_price}</span>
                    <span className="text-slate-400 text-sm">{svc.duration_minutes} min</span>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-slate-300" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // --- Step 1: SERVICE DETAILS ---
  if (step === "details") {
    return (
      <div className="space-y-8 animate-in slide-in-from-right-4 duration-300 pb-10 max-w-2xl mx-auto mt-4">
        <Button variant="ghost" className="text-slate-500 h-8 px-0 hover:bg-transparent hover:text-slate-900 -ml-2" onClick={() => setStep("service")}>
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Services
        </Button>
        
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900 mb-3">{serviceName}</h1>
            <p className="text-slate-500 leading-relaxed">{activeService?.description || "Professional photography session tailored to your needs."}</p>
          </div>

          <div className="flex flex-wrap gap-4 border-y border-slate-100 py-6">
            <div className="bg-slate-50 px-4 py-3 rounded-lg border border-slate-100">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1 font-medium">Price</p>
              <p className="text-lg font-semibold text-slate-900">₹{servicePrice}</p>
            </div>
            <div className="bg-slate-50 px-4 py-3 rounded-lg border border-slate-100">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1 font-medium">Duration</p>
              <p className="text-lg font-semibold text-slate-900">{serviceDuration} minutes</p>
            </div>
          </div>

          {activeService?.packages && activeService.packages.length > 0 && (
            <div className="space-y-4 pt-2">
              <h3 className="text-sm font-medium text-slate-900 uppercase tracking-wider">Select Package</h3>
              <div className="grid gap-3">
                {activeService.packages.map((pkg: any) => (
                  <div 
                    key={pkg.id} 
                    onClick={() => setSelectedPackageId(pkg.id)}
                    className={`cursor-pointer border rounded-xl p-5 transition-all duration-200 flex justify-between items-center ${selectedPackageId === pkg.id ? 'border-slate-900 bg-slate-900 text-white shadow-md' : 'border-slate-200 hover:border-slate-400 bg-white'}`}
                  >
                    <div>
                      <h4 className={`font-medium ${selectedPackageId === pkg.id ? 'text-white' : 'text-slate-900'}`}>{pkg.name}</h4>
                      <p className={`text-sm mt-1 ${selectedPackageId === pkg.id ? 'text-slate-300' : 'text-slate-500'}`}>{pkg.inclusions?.length || 0} inclusions</p>
                    </div>
                    <div className={`font-semibold ${selectedPackageId === pkg.id ? 'text-white' : 'text-slate-900'}`}>
                      ₹{pkg.price}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {inclusions.length > 0 && (
            <div className="space-y-4 pt-4">
              <h3 className="text-sm font-medium text-slate-900 uppercase tracking-wider">What's Included</h3>
              <ul className="space-y-3">
                {inclusions.map((item: string, i: number) => (
                  <li key={i} className="flex items-start gap-3 text-slate-600">
                    <Check className="w-5 h-5 text-slate-900 shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="pt-6">
            <Button onClick={() => setStep("date")} size="lg" className="w-full text-md h-14 rounded-xl shadow-md">
              Book this Session
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // --- Step 2: DATE & TIME ---
  if (step === "date") {
    return (
      <div className="space-y-8 animate-in slide-in-from-right-4 duration-300 pb-[calc(5rem+env(safe-area-inset-bottom))] max-w-2xl mx-auto mt-4">
        {!linkInfo.service && (
          <Button variant="ghost" className="text-slate-500 h-8 px-0 hover:bg-transparent hover:text-slate-900 -ml-2" onClick={() => setStep("details")}>
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to Details
          </Button>
        )}
        
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Select Date & Time</h1>
          <p className="text-slate-500">When would you like to schedule your {serviceName}?</p>
        </div>

        {conflictError && (
          <div className="flex gap-3 p-4 bg-red-50 text-red-700 border border-red-200 rounded-lg">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <div>
              <h4 className="font-semibold text-sm">Slot Unavailable</h4>
              <p className="text-sm">{conflictError}</p>
            </div>
          </div>
        )}

        <div className="space-y-4">
          <Label className="text-slate-900 font-medium">Date</Label>
          <input 
            type="date" 
            min={format(new Date(), "yyyy-MM-dd")} 
            className="flex h-14 w-full rounded-xl border border-slate-200 bg-white px-4 py-2 text-md ring-offset-white file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 disabled:cursor-not-allowed disabled:opacity-50 transition-colors hover:border-slate-300" 
            value={selectedDate ? format(selectedDate, "yyyy-MM-dd") : ""} 
            onChange={(e) => { 
              if(e.target.value) { 
                setSelectedDate(parseISO(e.target.value)); 
                setSelectedSlot(null); 
              } 
            }} 
          />
        </div>

        <div className="space-y-4 pt-4 border-t border-slate-100">
          <Label className="text-slate-900 font-medium flex items-center gap-2">
            Available Slots
          </Label>
          
          {isLoadingSlots ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[1,2,3,4,5,6].map(i => <div key={i} className="h-14 bg-slate-100 rounded-xl animate-pulse" />)}
            </div>
          ) : availability?.slots?.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {availability.slots.map((slot: any) => (
                <button
                  key={slot.starts_at}
                  onClick={() => setSelectedSlot(slot.starts_at)}
                  className={`
                    p-4 text-sm font-medium rounded-xl border transition-all duration-200 flex items-center justify-center
                    ${selectedSlot === slot.starts_at 
                      ? 'border-slate-900 bg-slate-900 text-white shadow-md scale-[1.02]' 
                      : 'border-slate-200 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50'}
                  `}
                >
                  {format(parseISO(slot.starts_at), "h:mm a")}
                </button>
              ))}
            </div>
          ) : (
            <div className="text-center p-10 border border-dashed border-slate-200 rounded-xl text-slate-500 bg-slate-50">
              No availability for {selectedDate ? format(selectedDate, "MMM d, yyyy") : "this date"}.
            </div>
          )}
        </div>

        {selectedSlot && (
          <div className="fixed bottom-0 left-0 right-0 p-4 pb-[env(safe-area-inset-bottom,1rem)] bg-white border-t shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.1)] z-10 animate-in slide-in-from-bottom-4">
            <div className="max-w-2xl mx-auto flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500 mb-0.5">{format(parseISO(selectedSlot), "EEEE, MMM d")}</p>
                <p className="text-lg font-semibold text-slate-900">{format(parseISO(selectedSlot), "h:mm a")}</p>
              </div>
              <Button onClick={() => setStep("customer")} size="lg" className="px-8 h-12 rounded-xl shadow-md text-md">
                Continue
              </Button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // --- Step 3: CUSTOMER INFO ---
  if (step === "customer") {
    return (
      <div className="space-y-8 animate-in slide-in-from-right-4 duration-300 pb-[calc(5rem+env(safe-area-inset-bottom))] max-w-2xl mx-auto mt-4">
        <Button variant="ghost" className="text-slate-500 h-8 px-0 hover:bg-transparent hover:text-slate-900 -ml-2" onClick={() => setStep("date")}>
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Time Selection
        </Button>
        
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Your Details</h1>
          <p className="text-slate-500">Please provide your contact information to secure your booking.</p>
        </div>

        {formError && (
          <div className="p-4 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
            {formError}
          </div>
        )}

        <div className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-slate-900">Full Name *</Label>
            <div className="relative">
              <User className="absolute left-3.5 top-3.5 h-5 w-5 text-slate-400" />
              <Input 
                id="name" 
                placeholder="John Doe" 
                value={customerName} 
                onChange={e => setCustomerName(e.target.value)} 
                className="pl-11 h-12 rounded-xl text-md"
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="whatsapp" className="text-slate-900">WhatsApp Number *</Label>
            <div className="relative">
              <Phone className="absolute left-3.5 top-3.5 h-5 w-5 text-slate-400" />
              <Input 
                id="whatsapp" 
                type="tel" 
                placeholder="+91 99999 99999" 
                value={whatsappNumber} 
                onChange={e => setWhatsappNumber(e.target.value)} 
                className="pl-11 h-12 rounded-xl text-md"
              />
            </div>
            <p className="text-xs text-slate-500 pl-1">Required for booking confirmation and updates.</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email" className="text-slate-900">Email Address (Optional)</Label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-3.5 h-5 w-5 text-slate-400" />
              <Input 
                id="email" 
                type="email" 
                placeholder="john@example.com" 
                value={email} 
                onChange={e => setEmail(e.target.value)} 
                className="pl-11 h-12 rounded-xl text-md"
              />
            </div>
          </div>

          <div className="space-y-2 pt-2">
            <Label htmlFor="notes" className="text-slate-900">Any special requests? (Optional)</Label>
            <div className="relative">
              <FileText className="absolute left-3.5 top-3.5 h-5 w-5 text-slate-400" />
              <Textarea 
                id="notes" 
                placeholder="Let us know if you have any specific requirements..." 
                className="pl-11 pt-3.5 min-h-[120px] rounded-xl text-md resize-none"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                maxLength={500}
              />
            </div>
          </div>
        </div>

        <div className="fixed bottom-0 left-0 right-0 p-4 pb-[env(safe-area-inset-bottom,1rem)] bg-white border-t shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.1)] z-10 animate-in slide-in-from-bottom-4">
          <div className="max-w-2xl mx-auto">
            <Button onClick={handleCustomerSubmit} size="lg" className="w-full h-12 rounded-xl shadow-md text-md">
              Review Booking
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // --- Step 4: REVIEW ---
  if (step === "review") {
    return (
      <div className="space-y-8 animate-in slide-in-from-right-4 duration-300 pb-[calc(5rem+env(safe-area-inset-bottom))] max-w-2xl mx-auto mt-4">
        <Button variant="ghost" className="text-slate-500 h-8 px-0 hover:bg-transparent hover:text-slate-900 -ml-2" onClick={() => setStep("customer")} disabled={confirmBooking.isPending}>
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Details
        </Button>
        
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Review Booking</h1>
          <p className="text-slate-500">Please confirm your session details.</p>
        </div>

        <Card className="shadow-md rounded-2xl border-slate-200 overflow-hidden">
          <div className="bg-slate-900 text-white p-6">
            <h3 className="text-xl font-medium mb-1">{serviceName}</h3>
            <p className="text-slate-300">{serviceDuration} minutes</p>
          </div>
          <CardContent className="p-0 divide-y divide-slate-100">
            <div className="p-6 grid grid-cols-[30px_1fr] gap-3 items-start">
              <CalendarIcon className="w-5 h-5 text-slate-400 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-1">Date & Time</p>
                <p className="text-lg font-medium text-slate-900">{selectedSlot ? format(parseISO(selectedSlot), "EEEE, MMMM d, yyyy") : ""}</p>
                <p className="text-slate-600 mt-0.5">{selectedSlot ? format(parseISO(selectedSlot), "h:mm a") : ""}</p>
              </div>
            </div>
            
            <div className="p-6 grid grid-cols-[30px_1fr] gap-3 items-start">
              <User className="w-5 h-5 text-slate-400 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-1">Customer</p>
                <p className="font-medium text-slate-900">{customerName}</p>
                <p className="text-slate-600 mt-0.5">{whatsappNumber}</p>
                {email && <p className="text-slate-600 mt-0.5">{email}</p>}
              </div>
            </div>

            <div className="p-6 grid grid-cols-2 gap-4 items-center bg-slate-50">
              <p className="font-medium text-slate-900">Total Price</p>
              <p className="text-xl font-semibold text-slate-900 text-right">₹{servicePrice}</p>
            </div>
          </CardContent>
        </Card>

        {conflictError && (
          <div className="flex gap-3 p-4 bg-red-50 text-red-700 border border-red-200 rounded-lg">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <p className="text-sm">{conflictError}</p>
          </div>
        )}

        <div className="fixed bottom-0 left-0 right-0 p-4 pb-[env(safe-area-inset-bottom,1rem)] bg-white border-t shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.1)] z-10 animate-in slide-in-from-bottom-4">
          <div className="max-w-2xl mx-auto flex gap-3">
            <Button className="flex-1 h-14 rounded-xl shadow-md text-md text-lg font-medium" onClick={handleConfirm} disabled={confirmBooking.isPending}>
              {confirmBooking.isPending ? <div className="w-5 h-5 border-2 border-slate-200 border-t-white rounded-full animate-spin" /> : "Confirm Booking"}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // --- Step 5: SUCCESS ---
  if (step === "success") {
    return (
      <div className="flex flex-col items-center justify-center text-center mt-16 px-4 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-2xl mx-auto">
        <div className="w-24 h-24 rounded-full bg-slate-900 text-white flex items-center justify-center mb-8 shadow-xl">
          <CheckCircle2 className="w-12 h-12" />
        </div>
        <h1 className="text-4xl font-semibold tracking-tight text-slate-900 mb-3">Booking Confirmed</h1>
        <p className="text-slate-600 text-lg mb-10 max-w-md">
          Thank you, {customerName.split(' ')[0]}. Your session has been successfully booked.
        </p>
        
        <Card className="w-full text-left shadow-md rounded-2xl border-slate-200 overflow-hidden">
          <CardContent className="p-8 space-y-6 bg-slate-50/50">
            <div>
              <p className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-1.5">Date</p>
              <p className="text-xl font-semibold text-slate-900">{selectedSlot ? format(parseISO(selectedSlot), "d MMMM yyyy") : ""}</p>
            </div>
            <div className="border-t border-slate-200 pt-6">
              <p className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-1.5">Time</p>
              <p className="text-xl font-semibold text-slate-900">{selectedSlot ? format(parseISO(selectedSlot), "h:mm a") : ""}</p>
            </div>
            <div className="border-t border-slate-200 pt-6">
              <p className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-1.5">Service</p>
              <p className="text-xl font-semibold text-slate-900">{serviceName}</p>
            </div>
          </CardContent>
        </Card>

        <p className="mt-8 text-slate-500 text-sm">
          A confirmation will be sent to your WhatsApp shortly.
        </p>
      </div>
    );
  }

  return null;
}
