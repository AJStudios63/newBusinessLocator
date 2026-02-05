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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, X, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import type { Lead, LeadFilters } from "@/lib/types";

const PAGE_SIZE_OPTIONS = [25, 50, 100, 200];

function LeadsPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  const [filters, setFilters] = useState<LeadFilters>(() => {
    const initial: LeadFilters = { page: 1, pageSize: 50 };
    const stage = searchParams.get("stage");
    const county = searchParams.get("county");
    const q = searchParams.get("q");
    const minScore = searchParams.get("minScore");
    const maxScore = searchParams.get("maxScore");
    const page = searchParams.get("page");
    const pageSize = searchParams.get("pageSize");

    if (stage) initial.stage = stage;
    if (county) initial.county = county;
    if (q) initial.q = q;
    if (minScore) initial.minScore = parseInt(minScore);
    if (maxScore) initial.maxScore = parseInt(maxScore);
    if (page) initial.page = parseInt(page);
    if (pageSize) initial.pageSize = parseInt(pageSize);

    return initial;
  });

  useEffect(() => {
    const params = new URLSearchParams();
    if (filters.stage) params.set("stage", filters.stage);
    if (filters.county) params.set("county", filters.county);
    if (filters.q) params.set("q", filters.q);
    if (filters.minScore !== undefined) params.set("minScore", filters.minScore.toString());
    if (filters.maxScore !== undefined) params.set("maxScore", filters.maxScore.toString());
    if (filters.page && filters.page > 1) params.set("page", filters.page.toString());
    if (filters.pageSize && filters.pageSize !== 50) params.set("pageSize", filters.pageSize.toString());

    const queryString = params.toString();
    const newUrl = queryString ? `/leads?${queryString}` : "/leads";

    if (window.location.pathname + window.location.search !== newUrl) {
      router.replace(newUrl, { scroll: false });
    }
  }, [filters, router]);

  const handleFilterChange = (newFilters: LeadFilters) => {
    const filtersChanged =
      newFilters.stage !== filters.stage ||
      newFilters.county !== filters.county ||
      newFilters.q !== filters.q ||
      newFilters.minScore !== filters.minScore ||
      newFilters.maxScore !== filters.maxScore;

    if (filtersChanged) {
      setFilters({ ...newFilters, page: 1 });
    } else {
      setFilters(newFilters);
    }
  };

  const goToPage = (page: number) => {
    setFilters({ ...filters, page });
  };

  const handlePageSizeChange = (newPageSize: number) => {
    setFilters({ ...filters, pageSize: newPageSize, page: 1 });
  };

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
    setFilters({ page: 1, pageSize: filters.pageSize || 50 });
  };

  const currentPage = filters.page || 1;
  const pageSize = filters.pageSize || 50;
  const totalPages = data?.totalPages || 1;
  const total = data?.total || 0;

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Leads</h1>
            <p className="text-muted-foreground mt-1">
              {total} total leads in your pipeline
            </p>
          </div>
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
            onFilterChange={handleFilterChange}
            counties={counties}
          />
          <FilterPresets
            currentFilters={filters}
            onApplyPreset={handleFilterChange}
          />
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : (
          <>
            <LeadTable
              leads={data?.leads || []}
              onRowClick={setSelectedLead}
            />

            {/* Pagination */}
            <div className="flex items-center justify-between glass rounded-lg px-4 py-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>
                  {total > 0 ? ((currentPage - 1) * pageSize) + 1 : 0}–{Math.min(currentPage * pageSize, total)} of {total}
                </span>
                <span className="text-border">|</span>
                <span>Per page:</span>
                <Select
                  value={pageSize.toString()}
                  onValueChange={(v) => handlePageSizeChange(parseInt(v))}
                >
                  <SelectTrigger className="w-[65px] h-7 text-xs glass-subtle">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PAGE_SIZE_OPTIONS.map((size) => (
                      <SelectItem key={size} value={size.toString()}>
                        {size}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => goToPage(1)}
                  disabled={currentPage === 1}
                  title="First page"
                >
                  <ChevronsLeft className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => goToPage(currentPage - 1)}
                  disabled={currentPage === 1}
                  title="Previous page"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                </Button>
                <span className="px-3 text-sm font-medium">
                  {currentPage} / {totalPages}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => goToPage(currentPage + 1)}
                  disabled={currentPage >= totalPages}
                  title="Next page"
                >
                  <ChevronRight className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => goToPage(totalPages)}
                  disabled={currentPage >= totalPages}
                  title="Last page"
                >
                  <ChevronsRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
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

export default function LeadsPage() {
  return (
    <Suspense
      fallback={
        <AppShell>
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        </AppShell>
      }
    >
      <LeadsPageContent />
    </Suspense>
  );
}
