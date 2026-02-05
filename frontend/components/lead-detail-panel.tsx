"use client";

import { useState, useEffect } from "react";
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
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { updateLead, updateLeadFields, getLeadsByBatch } from "@/lib/api";
import { STAGES, BUSINESS_TYPES, type Lead, type Stage, type LeadFieldUpdate } from "@/lib/types";
import { Pencil, X, Users, ExternalLink } from "lucide-react";
import Link from "next/link";
import { ScoreBadge } from "@/components/score-badge";

interface LeadDetailPanelProps {
  lead: Lead | null;
  open: boolean;
  onClose: () => void;
}

export function LeadDetailPanel({ lead, open, onClose }: LeadDetailPanelProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedFields, setEditedFields] = useState<LeadFieldUpdate>({});
  const [newStage, setNewStage] = useState<Stage | null>(null);
  const [note, setNote] = useState("");
  const [batchCount, setBatchCount] = useState<number | null>(null);
  const queryClient = useQueryClient();

  // Reset edit state when lead changes
  useEffect(() => {
    if (lead) {
      setIsEditing(false);
      setEditedFields({});
      setNewStage(null);
      setNote("");
      // Fetch batch count if lead has a batch_id
      if (lead.source_batch_id) {
        getLeadsByBatch(lead.source_batch_id).then((data) => {
          setBatchCount(data.count > 1 ? data.count - 1 : null);
        }).catch(() => setBatchCount(null));
      } else {
        setBatchCount(null);
      }
    }
  }, [lead?.id]);

  const stageMutation = useMutation({
    mutationFn: () =>
      updateLead(lead!.id, {
        stage: newStage || undefined,
        note: note || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      toast.success("Lead updated");
      setNewStage(null);
      setNote("");
      onClose();
    },
    onError: () => {
      toast.error("Failed to update lead");
    },
  });

  const fieldsMutation = useMutation({
    mutationFn: () => updateLeadFields(lead!.id, editedFields),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      toast.success("Lead fields updated");
      setIsEditing(false);
      setEditedFields({});
    },
    onError: () => {
      toast.error("Failed to update lead fields");
    },
  });

  const handleFieldChange = (field: keyof LeadFieldUpdate, value: string) => {
    setEditedFields((prev) => ({ ...prev, [field]: value }));
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedFields({});
  };

  if (!lead) return null;

  const getFieldValue = (field: keyof Lead) => {
    if (field in editedFields) {
      return editedFields[field as keyof LeadFieldUpdate] || "";
    }
    return lead[field] || "";
  };

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-[500px] sm:max-w-[500px] overflow-y-auto">
        <SheetHeader>
          <div className="flex items-center justify-between">
            {isEditing ? (
              <Input
                value={getFieldValue("business_name")}
                onChange={(e) => handleFieldChange("business_name", e.target.value)}
                className="text-lg font-semibold"
              />
            ) : (
              <SheetTitle>{lead.business_name}</SheetTitle>
            )}
            {!isEditing && (
              <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
                <Pencil className="h-4 w-4" />
              </Button>
            )}
          </div>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          <div className="flex items-center gap-2 flex-wrap">
            {isEditing ? (
              <Select
                value={getFieldValue("business_type") as string || "other"}
                onValueChange={(v) => handleFieldChange("business_type", v)}
              >
                <SelectTrigger className="w-[130px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {BUSINESS_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Badge variant="outline">{lead.business_type || "other"}</Badge>
            )}
            <Badge>{lead.stage}</Badge>
            <ScoreBadge lead={lead} />
            {batchCount !== null && lead.source_batch_id && (
              <Link href={`/batch/${lead.source_batch_id}`} onClick={onClose}>
                <Badge variant="outline" className="gap-1 cursor-pointer hover:bg-muted">
                  <Users className="h-3 w-3" />
                  +{batchCount} in batch
                  <ExternalLink className="h-3 w-3" />
                </Badge>
              </Link>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground mb-1">Address</p>
              {isEditing ? (
                <Input
                  value={getFieldValue("address")}
                  onChange={(e) => handleFieldChange("address", e.target.value)}
                  placeholder="Address"
                />
              ) : (
                <p>{lead.address || "—"}</p>
              )}
            </div>
            <div>
              <p className="text-muted-foreground mb-1">City</p>
              {isEditing ? (
                <Input
                  value={getFieldValue("city")}
                  onChange={(e) => handleFieldChange("city", e.target.value)}
                  placeholder="City"
                />
              ) : (
                <p>{lead.city || "—"}</p>
              )}
            </div>
            <div>
              <p className="text-muted-foreground mb-1">County</p>
              {isEditing ? (
                <Input
                  value={getFieldValue("county")}
                  onChange={(e) => handleFieldChange("county", e.target.value)}
                  placeholder="County"
                />
              ) : (
                <p>{lead.county || "—"}</p>
              )}
            </div>
            <div>
              <p className="text-muted-foreground mb-1">ZIP</p>
              {isEditing ? (
                <Input
                  value={getFieldValue("zip_code")}
                  onChange={(e) => handleFieldChange("zip_code", e.target.value)}
                  placeholder="ZIP Code"
                />
              ) : (
                <p>{lead.zip_code || "—"}</p>
              )}
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

          {/* Read-only fields */}
          <div className="text-sm text-muted-foreground space-y-1">
            <p>Fingerprint: <code className="text-xs">{lead.fingerprint}</code></p>
            <p>Created: {new Date(lead.created_at).toLocaleString()}</p>
            {lead.updated_at !== lead.created_at && (
              <p>Updated: {new Date(lead.updated_at).toLocaleString()}</p>
            )}
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

          {lead.notes && !isEditing && (
            <div>
              <p className="text-sm text-muted-foreground">Notes</p>
              <p className="text-sm whitespace-pre-wrap">{lead.notes}</p>
            </div>
          )}

          {isEditing ? (
            <div className="flex gap-2">
              <Button
                onClick={() => fieldsMutation.mutate()}
                disabled={fieldsMutation.isPending || Object.keys(editedFields).length === 0}
                className="flex-1"
              >
                {fieldsMutation.isPending ? "Saving..." : "Save Fields"}
              </Button>
              <Button variant="outline" onClick={handleCancelEdit}>
                <X className="h-4 w-4 mr-2" />
                Cancel
              </Button>
            </div>
          ) : (
            <>
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
                  onClick={() => stageMutation.mutate()}
                  disabled={stageMutation.isPending || (!newStage && !note)}
                  className="w-full"
                >
                  {stageMutation.isPending ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
