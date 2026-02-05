"use client";

import { useState } from "react";
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
import { toast } from "sonner";
import { bulkUpdateLeads } from "@/lib/api";
import { STAGES, type Lead, type Stage } from "@/lib/types";

interface LeadTableProps {
  leads: Lead[];
  onRowClick: (lead: Lead) => void;
}

export function LeadTable({ leads, onRowClick }: LeadTableProps) {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkStage, setBulkStage] = useState<Stage | "">("");
  const queryClient = useQueryClient();

  const bulkMutation = useMutation({
    mutationFn: () => bulkUpdateLeads(Array.from(selectedIds), bulkStage as string),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      toast.success(`Updated ${data.updated.length} leads`);
      setSelectedIds(new Set());
      setBulkStage("");
    },
    onError: () => {
      toast.error("Failed to update leads");
    },
  });

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
        <div className="flex items-center gap-4 p-3 bg-muted rounded-md">
          <span className="text-sm font-medium">
            {selectedIds.size} selected
          </span>
          <Select
            value={bulkStage}
            onValueChange={(v) => setBulkStage(v as Stage)}
          >
            <SelectTrigger className="w-[150px]">
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
            onClick={() => bulkMutation.mutate()}
            disabled={!bulkStage || bulkMutation.isPending}
          >
            Apply
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

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]">
                <Checkbox
                  checked={selectedIds.size === leads.length && leads.length > 0}
                  onCheckedChange={toggleAll}
                />
              </TableHead>
              <TableHead>Business Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>City</TableHead>
              <TableHead>County</TableHead>
              <TableHead className="text-right">Score</TableHead>
              <TableHead>Stage</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {leads.map((lead) => (
              <TableRow
                key={lead.id}
                className="cursor-pointer hover:bg-muted/50"
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
                  <Badge variant="outline">{lead.business_type || "other"}</Badge>
                </TableCell>
                <TableCell>{lead.city || "—"}</TableCell>
                <TableCell>{lead.county || "—"}</TableCell>
                <TableCell className="text-right">{lead.pos_score}</TableCell>
                <TableCell>
                  <Badge>{lead.stage}</Badge>
                </TableCell>
              </TableRow>
            ))}
            {leads.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  No leads found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
