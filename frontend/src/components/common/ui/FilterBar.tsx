import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, Filter } from "lucide-react";

export function FilterBar() {
  return (
    <div className="flex flex-col sm:flex-row gap-3 items-center justify-between p-1">
      <div className="relative w-full sm:max-w-md">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
        <Input type="search" placeholder="Search..." className="pl-9 bg-white border-gray-200 shadow-sm w-full" />
      </div>
      <div className="flex gap-2 w-full sm:w-auto">
        <Button variant="outline" className="w-full sm:w-auto shadow-sm border-gray-200 text-slate-600 bg-white">
          <Filter className="mr-2 h-4 w-4" />
          More Filters
        </Button>
      </div>
    </div>
  );
}