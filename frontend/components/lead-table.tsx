"use client";

import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { bulkUpdateLeads, bulkDeleteLeads } from "@/lib/api";
import { STAGES, type Lead, type Stage } from "@/lib/types";
import { Trash2 } from "lucide-react";
import { ScoreCell } from "@/components/score-badge";

interface LeadTableProps {
  leads: Lead[];
  onRowClick: (lead: Lead) => void;
}

export function LeadTable({ leads, onRowClick }: LeadTableProps) {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkStage, setBulkStage] = useState<Stage | "">("");
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const queryClient = useQueryClient();

  const bulkUpdateMutation = useMutation({
    mutationFn: () => bulkUpdateLeads(Array.from(selectedIds), { stage: bulkStage as string }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      toast.success(`Updated ${data.updated.length} leads`);
      setSelectedIds(new Set());
      setBulkStage("");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to update leads");
    },
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: () => bulkDeleteLeads(Array.from(selectedIds)),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      toast.success(`Deleted ${data.deleted.length} leads`);
      setSelectedIds(new Set());
      setShowDeleteDialog(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to delete leads");
      setShowDeleteDialog(false);
    },
  });

  useEffect(() => {
    setSelectedIds(new Set());
  }, [leads]);

  const toggleAll = () => {
    if (selectedIds.size === leads.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(leads.map((l) => l.id)));
    }
  };

  const toggleOne = (id: number) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  return (
    <div className="space-y-4">
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-4 p-3 glass rounded-lg animate-slide-in">
          <span className="text-sm font-medium text-primary">
            {selectedIds.size} selected
          </span>
          <Select
            value={bulkStage}
            onValueChange={(v) => setBulkStage(v as Stage)}
          >
            <SelectTrigger className="w-[150px] glass-subtle">
              <SelectValue placeholder="Move to..." />
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
            Delete
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setSelectedIds(new Set())}
          >
            Clear
          </Button>
        </div>
      )}

      <div className="rounded-xl glass overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-b border-border/50 hover:bg-transparent">
              <TableHead className="w-[40px]">
                <Checkbox
                  checked={selectedIds.size === leads.length && leads.length > 0}
                  onCheckedChange={toggleAll}
                />
              </TableHead>
              <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Business Name</TableHead>
              <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Type</TableHead>
              <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">City</TableHead>
              <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">County</TableHead>
              <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold text-right">Quality</TableHead>
              <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Stage</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {leads.map((lead) => (
              <TableRow
                key={lead.id}
                className="cursor-pointer border-b border-border/30 hover:bg-accent/5 transition-colors"
                onClick={() => onRowClick(lead)}
              >
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <Checkbox
                    checked={selectedIds.has(lead.id)}
                    onCheckedChange={() => toggleOne(lead.id)}
                  />
                </TableCell>
                <TableCell className="font-medium">{lead.business_name}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-xs">
                    {lead.business_type || "other"}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{lead.city || "—"}</TableCell>
                <TableCell className="text-muted-foreground">{lead.county || "—"}</TableCell>
                <TableCell className="text-right">
                  <ScoreCell score={lead.pos_score} />
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className="text-xs">{lead.stage}</Badge>
                </TableCell>
              </TableRow>
            ))}
            {leads.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                  No leads found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent className="glass-strong">
          <DialogHeader>
            <DialogTitle>Delete Leads</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete {selectedIds.size} lead{selectedIds.size === 1 ? "" : "s"}?
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
              {bulkDeleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
