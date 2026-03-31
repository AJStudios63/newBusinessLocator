"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { AppShell } from "@/components/app-shell";
import { LeadDetailPanel } from "@/components/lead-detail-panel";
import { MapFiltersBar } from "@/components/map-filters";
import { getMapLeads, getLead } from "@/lib/api";
import { Loader2 } from "lucide-react";
import type { Lead, MapFilters } from "@/lib/types";

const LeadMap = dynamic(() => import("@/components/lead-map"), { ssr: false });

export default function MapPage() {
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [filters, setFilters] = useState<MapFilters>({});

  const { data, isLoading } = useQuery({
    queryKey: ["map-leads", filters],
    queryFn: () => getMapLeads(filters),
  });

  const handleLeadClick = async (leadId: number) => {
    try {
      const fullLead = await getLead(leadId);
      setSelectedLead(fullLead);
    } catch {
      // Fallback to basic lead data from map if full fetch fails
      const mapLead = data?.leads.find((l) => l.id === leadId);
      if (mapLead) {
        setSelectedLead({
          ...mapLead,
          fingerprint: "",
          raw_type: null,
          address: null,
          state: "TN",
          zip_code: null,
          license_date: null,
          source_url: null,
          source_type: null,
          source_batch_id: null,
          notes: null,
          created_at: "",
          updated_at: "",
          contacted_at: null,
          closed_at: null,
        } as Lead);
      }
    }
  };

  return (
    <AppShell>
      <div className="-m-8 h-[calc(100vh)] relative">
        {isLoading || !data ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : (
          <>
            <LeadMap leads={data.leads} onLeadClick={handleLeadClick} />
            <MapFiltersBar
              filters={filters}
              onFilterChange={setFilters}
              totalGeocoded={data.total_geocoded}
              totalWithoutCoords={data.total_without_coords}
            />
          </>
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
