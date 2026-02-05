"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { STAGES, type LeadFilters } from "@/lib/types";
import { Download, Search, X } from "lucide-react";
import { getExportUrl } from "@/lib/api";

interface LeadFiltersProps {
  filters: LeadFilters;
  onFilterChange: (filters: LeadFilters) => void;
  counties: string[];
}

export function LeadFiltersBar({ filters, onFilterChange, counties }: LeadFiltersProps) {
  const [searchInput, setSearchInput] = useState(filters.q || "");

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchInput !== (filters.q || "")) {
        onFilterChange({ ...filters, q: searchInput || undefined });
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchInput]);

  // Sync searchInput when filters.q changes externally
  useEffect(() => {
    if (filters.q !== searchInput) {
      setSearchInput(filters.q || "");
    }
  }, [filters.q]);

  const clearSearch = useCallback(() => {
    setSearchInput("");
    onFilterChange({ ...filters, q: undefined });
  }, [filters, onFilterChange]);

  return (
    <div className="flex flex-wrap gap-4 items-center">
      {/* Search box */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          type="text"
          placeholder="Search businesses..."
          className="w-[220px] pl-9 pr-8"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        {searchInput && (
          <button
            onClick={clearSearch}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <Select
        value={filters.stage || "all"}
        onValueChange={(value) =>
          onFilterChange({ ...filters, stage: value === "all" ? undefined : value })
        }
      >
        <SelectTrigger className="w-[150px]">
          <SelectValue placeholder="All Stages" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Stages</SelectItem>
          {STAGES.map((stage) => (
            <SelectItem key={stage} value={stage}>
              {stage}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.county || "all"}
        onValueChange={(value) =>
          onFilterChange({ ...filters, county: value === "all" ? undefined : value })
        }
      >
        <SelectTrigger className="w-[150px]">
          <SelectValue placeholder="All Counties" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Counties</SelectItem>
          {counties.map((county) => (
            <SelectItem key={county} value={county}>
              {county}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Score range */}
      <div className="flex items-center gap-2">
        <Input
          type="number"
          placeholder="Min"
          className="w-[80px]"
          min={0}
          max={100}
          value={filters.minScore ?? ""}
          onChange={(e) =>
            onFilterChange({
              ...filters,
              minScore: e.target.value ? parseInt(e.target.value) : undefined,
            })
          }
        />
        <span className="text-muted-foreground">-</span>
        <Input
          type="number"
          placeholder="Max"
          className="w-[80px]"
          min={0}
          max={100}
          value={filters.maxScore ?? ""}
          onChange={(e) =>
            onFilterChange({
              ...filters,
              maxScore: e.target.value ? parseInt(e.target.value) : undefined,
            })
          }
        />
        <span className="text-sm text-muted-foreground">Score</span>
      </div>

      <Button variant="outline" asChild>
        <a href={getExportUrl(filters)} download>
          <Download className="mr-2 h-4 w-4" />
          Export CSV
        </a>
      </Button>
    </div>
  );
}
