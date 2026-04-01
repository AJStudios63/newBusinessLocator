"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { AppShell } from "@/components/app-shell";
import { LeadDetailPanel } from "@/components/lead-detail-panel";
import { MapFiltersBar } from "@/components/map-filters";
import { getMapLeads, getLead, getGeocodeStatus, startGeocode } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import type { Lead, MapFilters } from "@/lib/types";

const LeadMap = dynamic(() => import("@/components/lead-map"), { ssr: false });

export default function MapPage() {
  const queryClient = useQueryClient();
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [filters, setFilters] = useState<MapFilters>({});
  const prevRunningRef = useRef<boolean | undefined>(undefined);

  const { data, isLoading } = useQuery({
    queryKey: ["map-leads", filters],
    queryFn: () => getMapLeads(filters),
  });

  const { data: geocodeStatus } = useQuery({
    queryKey: ["geocodeStatus"],
    queryFn: getGeocodeStatus,
    refetchInterval: (query) => {
      return query.state.data?.running ? 2000 : false;
    },
  });

  // When geocoding finishes, invalidate map data and show toast
  useEffect(() => {
    if (prevRunningRef.current === true && geocodeStatus?.running === false) {
      queryClient.invalidateQueries({ queryKey: ["map-leads"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      if (geocodeStatus.succeeded > 0) {
        toast.success(
          `Geocoding complete — ${geocodeStatus.succeeded} leads geocoded`
        );
      } else if (geocodeStatus.failed > 0) {
        toast.error("Geocoding failed — no leads were geocoded");
      } else {
        toast.info("No leads needed geocoding");
      }
    }
    prevRunningRef.current = geocodeStatus?.running;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geocodeStatus?.running, geocodeStatus?.succeeded, geocodeStatus?.failed, queryClient]);

  const geocodeMutation = useMutation({
    mutationFn: startGeocode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["geocodeStatus"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to start geocoding");
    },
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
            <LeadMap
              leads={data.leads}
              onLeadClick={handleLeadClick}
              geocodeStatus={geocodeStatus ?? null}
              totalWithoutCoords={data.total_without_coords}
              onStartGeocode={() => geocodeMutation.mutate()}
              isStarting={geocodeMutation.isPending}
            />
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
