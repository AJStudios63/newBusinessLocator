"use client";

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
import { Download } from "lucide-react";
import { getExportUrl } from "@/lib/api";

interface LeadFiltersProps {
  filters: LeadFilters;
  onFilterChange: (filters: LeadFilters) => void;
  counties: string[];
}

export function LeadFiltersBar({ filters, onFilterChange, counties }: LeadFiltersProps) {
  return (
    <div className="flex flex-wrap gap-4 items-center">
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

      <Input
        type="number"
        placeholder="Min Score"
        className="w-[120px]"
        value={filters.minScore || ""}
        onChange={(e) =>
          onFilterChange({
            ...filters,
            minScore: e.target.value ? parseInt(e.target.value) : undefined,
          })
        }
      />

      <Button variant="outline" asChild>
        <a href={getExportUrl(filters)} download>
          <Download className="mr-2 h-4 w-4" />
          Export CSV
        </a>
      </Button>
    </div>
  );
}
