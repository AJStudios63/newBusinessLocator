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
import { MapPin, X } from "lucide-react";
import { STAGES, BUSINESS_TYPES, type MapFilters } from "@/lib/types";

const COUNTIES = [
  "Cheatham",
  "Coffee",
  "Davidson",
  "Dickson",
  "Franklin",
  "Maury",
  "Montgomery",
  "Putnam",
  "Robertson",
  "Rutherford",
  "Sumner",
  "Williamson",
  "Wilson",
];

interface MapFiltersBarProps {
  filters: MapFilters;
  onFilterChange: (filters: MapFilters) => void;
  totalGeocoded: number;
  totalWithoutCoords: number;
}

const DEFAULT_FILTERS: MapFilters = {};

function hasActiveFilters(filters: MapFilters): boolean {
  return !!(
    filters.stage ||
    filters.county ||
    filters.businessType ||
    filters.minScore !== undefined ||
    filters.maxScore !== undefined
  );
}

export function MapFiltersBar({
  filters,
  onFilterChange,
  totalGeocoded,
  totalWithoutCoords,
}: MapFiltersBarProps) {
  const isFiltered = hasActiveFilters(filters);

  return (
    <div className="absolute top-4 left-4 right-4 z-[1000] pointer-events-none">
      <div className="glass-strong rounded-xl p-3 shadow-lg pointer-events-auto inline-flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 text-sm font-medium">
          <MapPin className="h-4 w-4 text-primary" />
          <span>
            {totalGeocoded} leads ({totalWithoutCoords} without coordinates)
          </span>
        </div>

        <Select
          value={filters.stage || "all"}
          onValueChange={(value) =>
            onFilterChange({ ...filters, stage: value === "all" ? undefined : value })
          }
        >
          <SelectTrigger className="w-[150px] glass-subtle">
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
          <SelectTrigger className="w-[150px] glass-subtle">
            <SelectValue placeholder="All Counties" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Counties</SelectItem>
            {COUNTIES.map((county) => (
              <SelectItem key={county} value={county}>
                {county}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={filters.businessType || "all"}
          onValueChange={(value) =>
            onFilterChange({ ...filters, businessType: value === "all" ? undefined : value })
          }
        >
          <SelectTrigger className="w-[150px] glass-subtle">
            <SelectValue placeholder="All Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {BUSINESS_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {type}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="flex items-center gap-2">
          <Input
            type="number"
            placeholder="Min"
            className="w-[70px] glass-subtle"
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
          <span className="text-muted-foreground text-xs">to</span>
          <Input
            type="number"
            placeholder="Max"
            className="w-[70px] glass-subtle"
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
          <span className="text-xs text-muted-foreground">Score</span>
        </div>

        {isFiltered && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
            onClick={() => onFilterChange(DEFAULT_FILTERS)}
          >
            <X className="h-3 w-3 mr-1" />
            Clear Filters
          </Button>
        )}
      </div>
    </div>
  );
}
