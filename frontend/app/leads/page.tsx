"use client";

import { useState, useMemo, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { LeadTable } from "@/components/lead-table";
import { LeadFiltersBar } from "@/components/lead-filters";
import { LeadDetailPanel } from "@/components/lead-detail-panel";
import { FilterPresets } from "@/components/filter-presets";
import { getLeads, getStats } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Loader2, X } from "lucide-react";
import type { Lead, LeadFilters } from "@/lib/types";

function LeadsPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  // Initialize filters from URL params
  const [filters, setFilters] = useState<LeadFilters>(() => {
    const initial: LeadFilters = { limit: 100 };
    const stage = searchParams.get("stage");
    const county = searchParams.get("county");
    const type = searchParams.get("type");
    const q = searchParams.get("q");
    const minScore = searchParams.get("minScore");
    const maxScore = searchParams.get("maxScore");

    if (stage) initial.stage = stage;
    if (county) initial.county = county;
    if (type) initial.stage = type; // Note: type filter maps to business_type
    if (q) initial.q = q;
    if (minScore) initial.minScore = parseInt(minScore);
    if (maxScore) initial.maxScore = parseInt(maxScore);

    return initial;
  });

  // Sync URL when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    if (filters.stage) params.set("stage", filters.stage);
    if (filters.county) params.set("county", filters.county);
    if (filters.q) params.set("q", filters.q);
    if (filters.minScore !== undefined) params.set("minScore", filters.minScore.toString());
    if (filters.maxScore !== undefined) params.set("maxScore", filters.maxScore.toString());

    const queryString = params.toString();
    const newUrl = queryString ? `/leads?${queryString}` : "/leads";

    // Only update URL if it's different (avoid infinite loop)
    if (window.location.pathname + window.location.search !== newUrl) {
      router.replace(newUrl, { scroll: false });
    }
  }, [filters, router]);

  const { data, isLoading } = useQuery({
    queryKey: ["leads", filters],
    queryFn: () => getLeads(filters),
  });

  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });

  const counties = useMemo(() => {
    if (!stats) return [];
    return Object.keys(stats.by_county).filter(Boolean).sort();
  }, [stats]);

  const hasActiveFilters = !!(filters.stage || filters.county || filters.q || filters.minScore !== undefined || filters.maxScore !== undefined);

  const clearFilters = () => {
    setFilters({ limit: 100 });
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Leads</h1>
          {hasActiveFilters && (
            <Button variant="outline" size="sm" onClick={clearFilters}>
              <X className="mr-2 h-4 w-4" />
              Clear Filters
            </Button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <LeadFiltersBar
            filters={filters}
            onFilterChange={setFilters}
            counties={counties}
          />
          <FilterPresets
            currentFilters={filters}
            onApplyPreset={setFilters}
          />
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : (
          <LeadTable
            leads={data?.leads || []}
            onRowClick={setSelectedLead}
          />
        )}

        <LeadDetailPanel
          lead={selectedLead}
          open={!!selectedLead}
          onClose={() => setSelectedLead(null)}
        />
      </div>
    </AppShell>
  );
}

export default function LeadsPage() {
  return (
    <Suspense
      fallback={
        <AppShell>
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        </AppShell>
      }
    >
      <LeadsPageContent />
    </Suspense>
  );
}
