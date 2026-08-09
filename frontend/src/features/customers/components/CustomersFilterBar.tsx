import { useSearchParams } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";
import { useState, useEffect } from "react";

export function CustomersFilterBar() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("search") || "");

  useEffect(() => {
    const timer = setTimeout(() => {
      const current = Object.fromEntries(searchParams.entries());
      if (search) {
        current.search = search;
      } else {
        delete current.search;
      }
      current.page = "1";
      setSearchParams(current);
    }, 400);
    return () => clearTimeout(timer);
  }, [search, searchParams, setSearchParams]);

  return (
    <div className="flex flex-col sm:flex-row gap-3 items-center justify-between p-1">
      <div className="relative w-full sm:max-w-md">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
        <Input 
          type="search" 
          placeholder="Search by name, email, or phone..." 
          className="pl-9 bg-white border-gray-200 shadow-sm w-full"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
    </div>
  );
}