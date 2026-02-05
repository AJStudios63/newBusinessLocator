"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { LeadTable } from "@/components/lead-table";
import { LeadFiltersBar } from "@/components/lead-filters";
import { LeadDetailPanel } from "@/components/lead-detail-panel";
import { getLeads, getStats } from "@/lib/api";
import { Loader2 } from "lucide-react";
import type { Lead, LeadFilters } from "@/lib/types";

export default function LeadsPage() {
  const [filters, setFilters] = useState<LeadFilters>({ limit: 100 });
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

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

  return (
    <AppShell>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Leads</h1>

        <LeadFiltersBar
          filters={filters}
          onFilterChange={setFilters}
          counties={counties}
        />

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
