import { useSearchParams } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, X } from "lucide-react";
import { useState, useEffect, useCallback } from "react";

export function LeadsFilterBar() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("search") || "");

  const updateParams = useCallback((updates: Record<string, string | null>) => {
    const current = Object.fromEntries(searchParams.entries());
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null) {
        delete current[key];
      } else {
        current[key] = value;
      }
    });
    setSearchParams(current);
  }, [searchParams, setSearchParams]);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      updateParams({ search: search || null, page: "1" });
    }, 400);
    return () => clearTimeout(timer);
  }, [search, updateParams]);

  const handleClear = () => {
    setSearch("");
    setSearchParams({});
  };

  const hasFilters = Array.from(searchParams.entries()).length > 0;

  return (
    <div className="flex flex-col sm:flex-row gap-3 items-center justify-between p-1">
      <div className="relative w-full sm:max-w-md">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
        <Input 
          type="search" 
          placeholder="Search leads..." 
          className="pl-9 bg-white border-gray-200 shadow-sm w-full"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <div className="flex flex-wrap gap-2 w-full sm:w-auto">
        <Select 
          value={searchParams.get("source") || ""} 
          onValueChange={(val) => updateParams({ source: val === "all" ? null : val, page: "1" })}
        >
          <SelectTrigger className="w-[130px] bg-white border-gray-200 shadow-sm text-slate-700">
            <SelectValue placeholder="Source" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Sources</SelectItem>
            <SelectItem value="INSTAGRAM">Instagram</SelectItem>
            <SelectItem value="WHATSAPP">WhatsApp</SelectItem>
            <SelectItem value="WEBSITE">Website</SelectItem>
          </SelectContent>
        </Select>

        <Select 
          value={searchParams.get("status") || ""} 
          onValueChange={(val) => updateParams({ status: val === "all" ? null : val, page: "1" })}
        >
          <SelectTrigger className="w-[140px] bg-white border-gray-200 shadow-sm text-slate-700">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="NEW">New</SelectItem>
            <SelectItem value="CONTACTED">Contacted</SelectItem>
            <SelectItem value="QUALIFIED">Qualified</SelectItem>
            <SelectItem value="CONVERTED">Converted</SelectItem>
            <SelectItem value="LOST">Lost</SelectItem>
          </SelectContent>
        </Select>

        {hasFilters && (
          <Button variant="ghost" onClick={handleClear} className="text-slate-500 px-3">
            <X className="h-4 w-4 mr-2" />
            Clear
          </Button>
        )}
      </div>
    </div>
  );
}