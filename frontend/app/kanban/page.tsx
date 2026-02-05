"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { KanbanBoard } from "@/components/kanban-board";
import { LeadDetailPanel } from "@/components/lead-detail-panel";
import { getKanbanData } from "@/lib/api";
import { Loader2 } from "lucide-react";
import type { Lead } from "@/lib/types";

export default function KanbanPage() {
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["kanban"],
    queryFn: () => getKanbanData(),
  });

  return (
    <AppShell>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Kanban Board</h1>

        {isLoading || !data ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : (
          <KanbanBoard data={data} onCardClick={setSelectedLead} />
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
