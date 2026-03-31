"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { LeadTable } from "@/components/lead-table";
import { LeadDetailPanel } from "@/components/lead-detail-panel";
import { getLeadsByBatch, bulkUpdateLeads, bulkDeleteLeads } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { ArrowLeft, Loader2, Trash2 } from "lucide-react";
import { useState } from "react";
import { STAGES, type Lead, type Stage } from "@/lib/types";

interface BatchPageProps {
  params: { id: string };
}

export default function BatchPage({ params }: BatchPageProps) {
  const { id } = params;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [bulkStage, setBulkStage] = useState<Stage | "">("");
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["batch", id],
    queryFn: () => getLeadsByBatch(id),
  });

  const bulkUpdateMutation = useMutation({
    mutationFn: () => {
      const ids = data?.leads.map((l) => l.id) || [];
      return bulkUpdateLeads(ids, { stage: bulkStage as string });
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["batch", id] });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      toast.success(`Updated ${result.updated.length} leads`);
      setBulkStage("");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to update leads");
    },
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: () => {
      const ids = data?.leads.map((l) => l.id) || [];
      return bulkDeleteLeads(ids);
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["batch", id] });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      toast.success(`Deleted ${result.deleted.length} leads`);
      setShowDeleteDialog(false);
      router.push("/leads");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to delete leads");
      setShowDeleteDialog(false);
    },
  });

  if (isLoading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppShell>
    );
  }

  if (error || !data) {
    return (
      <AppShell>
        <div className="space-y-6">
          <Button variant="ghost" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <div className="text-center py-12">
            <p className="text-muted-foreground">Batch not found or no leads in this batch.</p>
          </div>
        </div>
      </AppShell>
    );
  }

  const sourceUrl = data.leads[0]?.source_url;
  const sourceType = data.leads[0]?.source_type;

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Batch View</h1>
            <p className="text-sm text-muted-foreground">
              {data.count} leads extracted together
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 p-4 glass rounded-xl">
          <div className="flex-1 space-y-1">
            <p className="text-sm">
              <span className="text-xs uppercase tracking-wider text-muted-foreground">Batch ID:</span>{" "}
              <code className="text-xs font-mono text-primary/70">{id}</code>
            </p>
            {sourceType && (
              <p className="text-sm">
                <span className="text-xs uppercase tracking-wider text-muted-foreground">Source Type:</span>{" "}
                <Badge variant="outline" className="text-xs">{sourceType}</Badge>
              </p>
            )}
            {sourceUrl && (
              <p className="text-sm">
                <span className="text-xs uppercase tracking-wider text-muted-foreground">Source URL:</span>{" "}
                <a
                  href={sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:text-primary/80 hover:underline break-all transition-colors"
                >
                  {sourceUrl}
                </a>
              </p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Select
              value={bulkStage}
              onValueChange={(v) => setBulkStage(v as Stage)}
            >
              <SelectTrigger className="w-[150px] glass-subtle">
                <SelectValue placeholder="Move all to..." />
              </SelectTrigger>
              <SelectContent>
                {STAGES.map((stage) => (
                  <SelectItem key={stage} value={stage}>
                    {stage}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              onClick={() => bulkUpdateMutation.mutate()}
              disabled={!bulkStage || bulkUpdateMutation.isPending}
            >
              Apply
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => setShowDeleteDialog(true)}
              disabled={bulkDeleteMutation.isPending}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Batch
            </Button>
          </div>
        </div>

        <LeadTable leads={data.leads} onRowClick={setSelectedLead} />

        <LeadDetailPanel
          lead={selectedLead}
          open={!!selectedLead}
          onClose={() => setSelectedLead(null)}
        />

        <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <DialogContent className="glass-strong">
            <DialogHeader>
              <DialogTitle>Delete Entire Batch</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete all {data.count} leads from this batch?
                This action can be undone by an administrator.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => bulkDeleteMutation.mutate()}
                disabled={bulkDeleteMutation.isPending}
              >
                {bulkDeleteMutation.isPending ? "Deleting..." : "Delete Batch"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppShell>
  );
}
