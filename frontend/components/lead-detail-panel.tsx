"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { updateLead } from "@/lib/api";
import { STAGES, type Lead, type Stage } from "@/lib/types";

interface LeadDetailPanelProps {
  lead: Lead | null;
  open: boolean;
  onClose: () => void;
}

export function LeadDetailPanel({ lead, open, onClose }: LeadDetailPanelProps) {
  const [newStage, setNewStage] = useState<Stage | null>(null);
  const [note, setNote] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      updateLead(lead!.id, {
        stage: newStage || undefined,
        note: note || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      toast.success("Lead updated");
      setNewStage(null);
      setNote("");
      onClose();
    },
    onError: () => {
      toast.error("Failed to update lead");
    },
  });

  if (!lead) return null;

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-[500px] sm:max-w-[500px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{lead.business_name}</SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          <div className="flex items-center gap-2">
            <Badge variant="outline">{lead.business_type || "other"}</Badge>
            <Badge>{lead.stage}</Badge>
            <Badge variant="secondary">Score: {lead.pos_score}</Badge>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Address</p>
              <p>{lead.address || "—"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">City</p>
              <p>{lead.city || "—"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">County</p>
              <p>{lead.county || "—"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">ZIP</p>
              <p>{lead.zip_code || "—"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">License Date</p>
              <p>{lead.license_date || "—"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Source</p>
              <p>{lead.source_type || "—"}</p>
            </div>
          </div>

          {lead.source_url && (
            <div>
              <p className="text-sm text-muted-foreground">Source URL</p>
              <a
                href={lead.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:underline break-all"
              >
                {lead.source_url}
              </a>
            </div>
          )}

          {lead.notes && (
            <div>
              <p className="text-sm text-muted-foreground">Notes</p>
              <p className="text-sm whitespace-pre-wrap">{lead.notes}</p>
            </div>
          )}

          <hr />

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Update Stage</label>
              <Select
                value={newStage || lead.stage}
                onValueChange={(v) => setNewStage(v as Stage)}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STAGES.map((stage) => (
                    <SelectItem key={stage} value={stage}>
                      {stage}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium">Add Note</label>
              <Textarea
                className="mt-1"
                placeholder="Enter a note..."
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </div>

            <Button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending || (!newStage && !note)}
              className="w-full"
            >
              {mutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
