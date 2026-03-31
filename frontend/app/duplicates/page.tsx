"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import {
  getDuplicates,
  scanForDuplicates,
  updateDuplicateSuggestion,
  mergeLeads,
} from "@/lib/api";
import { Loader2, RefreshCw, Check, X, GitMerge } from "lucide-react";
import type { DuplicateSuggestion, Lead } from "@/lib/types";
import { ScoreBadge } from "@/components/score-badge";
import { formatLocalDate } from "@/lib/utils";

const MERGEABLE_FIELDS = [
  { key: "business_name", label: "Business Name" },
  { key: "address", label: "Address" },
  { key: "city", label: "City" },
  { key: "county", label: "County" },
  { key: "zip_code", label: "ZIP Code" },
  { key: "business_type", label: "Business Type" },
] as const;

export default function DuplicatesPage() {
  const queryClient = useQueryClient();
  const [selectedSuggestion, setSelectedSuggestion] = useState<DuplicateSuggestion | null>(null);
  const [mergeChoices, setMergeChoices] = useState<Record<string, "a" | "b">>({});
  const [keepLead, setKeepLead] = useState<"a" | "b">("a");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["duplicates"],
    queryFn: () => getDuplicates(50),
  });

  const scanMutation = useMutation({
    mutationFn: () => scanForDuplicates(0.7),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["duplicates"] });
      queryClient.invalidateQueries({ queryKey: ["duplicatesCount"] });
      toast.success(`Found ${result.new_suggestions} new potential duplicates`);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to scan for duplicates");
    },
  });

  const dismissMutation = useMutation({
    mutationFn: (suggestionId: number) => updateDuplicateSuggestion(suggestionId, "dismissed"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["duplicates"] });
      queryClient.invalidateQueries({ queryKey: ["duplicatesCount"] });
      toast.success("Suggestion dismissed");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to dismiss suggestion");
    },
  });

  const mergeMutation = useMutation({
    mutationFn: () => {
      if (!selectedSuggestion) return Promise.reject("No suggestion selected");
      const keepId = keepLead === "a" ? selectedSuggestion.lead_a.id : selectedSuggestion.lead_b.id;
      const mergeId = keepLead === "a" ? selectedSuggestion.lead_b.id : selectedSuggestion.lead_a.id;

      const fieldChoices: Record<string, string> = {};
      for (const field of MERGEABLE_FIELDS) {
        const choice = mergeChoices[field.key];
        if (choice) {
          const sourceLead = choice === "a" ? selectedSuggestion.lead_a : selectedSuggestion.lead_b;
          const value = sourceLead[field.key as keyof Lead];
          if (value) fieldChoices[field.key] = value as string;
        }
      }

      return mergeLeads({
        keep_id: keepId,
        merge_id: mergeId,
        field_choices: Object.keys(fieldChoices).length > 0 ? fieldChoices : undefined,
        suggestion_id: selectedSuggestion.id,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["duplicates"] });
      queryClient.invalidateQueries({ queryKey: ["duplicatesCount"] });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      toast.success("Leads merged successfully");
      setSelectedSuggestion(null);
      setMergeChoices({});
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to merge leads");
    },
  });

  const openMergeDialog = (suggestion: DuplicateSuggestion) => {
    setSelectedSuggestion(suggestion);
    setKeepLead("a");
    const defaultChoices: Record<string, "a" | "b"> = {};
    for (const field of MERGEABLE_FIELDS) {
      const valueA = suggestion.lead_a[field.key as keyof Lead];
      const valueB = suggestion.lead_b[field.key as keyof Lead];
      if (valueA && !valueB) defaultChoices[field.key] = "a";
      else if (!valueA && valueB) defaultChoices[field.key] = "b";
      else defaultChoices[field.key] = suggestion.lead_a.pos_score >= suggestion.lead_b.pos_score ? "a" : "b";
    }
    setMergeChoices(defaultChoices);
  };

  if (isLoading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppShell>
    );
  }

  const suggestions = data?.suggestions || [];

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Duplicate Detection</h1>
            <p className="text-muted-foreground mt-1">
              Review and merge potential duplicate leads
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Button onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending}>
              {scanMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Scanning...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Scan for Duplicates
                </>
              )}
            </Button>
          </div>
        </div>

        {suggestions.length === 0 ? (
          <Card>
            <CardContent className="py-16 text-center">
              <p className="text-muted-foreground">No duplicate suggestions to review.</p>
              <p className="text-sm text-muted-foreground mt-2">
                Click &quot;Scan for Duplicates&quot; to find potential matches.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {suggestions.map((suggestion) => (
              <Card key={suggestion.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-3">
                      <span className="text-gradient font-bold">
                        {Math.round(suggestion.similarity_score * 100)}%
                      </span>
                      <span className="text-muted-foreground font-normal">match</span>
                    </CardTitle>
                    <Badge variant="outline" className="text-xs">
                      {formatLocalDate(suggestion.created_at)}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-2 gap-4">
                    <LeadCard lead={suggestion.lead_a} label="Lead A" />
                    <LeadCard lead={suggestion.lead_b} label="Lead B" />
                  </div>
                  <div className="flex justify-end gap-2 mt-4">
                    <Button
                      variant="outline"
                      onClick={() => dismissMutation.mutate(suggestion.id)}
                      disabled={dismissMutation.isPending}
                    >
                      <X className="mr-2 h-4 w-4" />
                      Not a Duplicate
                    </Button>
                    <Button onClick={() => openMergeDialog(suggestion)}>
                      <GitMerge className="mr-2 h-4 w-4" />
                      Merge
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Merge Dialog */}
        <Dialog open={!!selectedSuggestion} onOpenChange={(open) => !open && setSelectedSuggestion(null)}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto glass-strong custom-scrollbar">
            <DialogHeader>
              <DialogTitle>Merge Leads</DialogTitle>
              <DialogDescription>
                Choose which lead to keep and select field values from either lead.
              </DialogDescription>
            </DialogHeader>

            {selectedSuggestion && (
              <div className="space-y-6">
                <div>
                  <Label className="text-base font-medium">Which lead should be kept?</Label>
                  <RadioGroup
                    value={keepLead}
                    onValueChange={(v) => setKeepLead(v as "a" | "b")}
                    className="mt-2"
                  >
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="a" id="keep-a" />
                      <Label htmlFor="keep-a" className="flex items-center gap-2">
                        Lead A: {selectedSuggestion.lead_a.business_name}
                        <ScoreBadge lead={selectedSuggestion.lead_a} showLabel={false} />
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="b" id="keep-b" />
                      <Label htmlFor="keep-b" className="flex items-center gap-2">
                        Lead B: {selectedSuggestion.lead_b.business_name}
                        <ScoreBadge lead={selectedSuggestion.lead_b} showLabel={false} />
                      </Label>
                    </div>
                  </RadioGroup>
                </div>

                <div className="space-y-4">
                  <Label className="text-base font-medium">Field Values</Label>
                  <p className="text-sm text-muted-foreground">
                    For each field, choose which lead&apos;s value to keep:
                  </p>

                  <div className="space-y-3">
                    {MERGEABLE_FIELDS.map((field) => {
                      const valueA = selectedSuggestion.lead_a[field.key as keyof Lead] as string | null;
                      const valueB = selectedSuggestion.lead_b[field.key as keyof Lead] as string | null;

                      return (
                        <div key={field.key} className="grid grid-cols-3 gap-2 items-center">
                          <Label className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">{field.label}</Label>
                          <button
                            onClick={() => setMergeChoices((prev) => ({ ...prev, [field.key]: "a" }))}
                            className={`p-2 text-left rounded-lg transition-all ${
                              mergeChoices[field.key] === "a"
                                ? "glass ring-2 ring-primary/50"
                                : "glass-subtle hover:bg-accent/5"
                            }`}
                          >
                            <span className="text-sm">{valueA || "—"}</span>
                            {mergeChoices[field.key] === "a" && (
                              <Check className="h-4 w-4 inline ml-2 text-primary" />
                            )}
                          </button>
                          <button
                            onClick={() => setMergeChoices((prev) => ({ ...prev, [field.key]: "b" }))}
                            className={`p-2 text-left rounded-lg transition-all ${
                              mergeChoices[field.key] === "b"
                                ? "glass ring-2 ring-primary/50"
                                : "glass-subtle hover:bg-accent/5"
                            }`}
                          >
                            <span className="text-sm">{valueB || "—"}</span>
                            {mergeChoices[field.key] === "b" && (
                              <Check className="h-4 w-4 inline ml-2 text-primary" />
                            )}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={() => setSelectedSuggestion(null)}>
                Cancel
              </Button>
              <Button onClick={() => mergeMutation.mutate()} disabled={mergeMutation.isPending}>
                {mergeMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Merging...
                  </>
                ) : (
                  <>
                    <GitMerge className="mr-2 h-4 w-4" />
                    Merge Leads
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppShell>
  );
}

function LeadCard({ lead, label }: { lead: Lead; label: string }) {
  return (
    <div className="p-4 glass-subtle rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</span>
        <ScoreBadge lead={lead} />
      </div>
      <h3 className="font-semibold">{lead.business_name}</h3>
      <div className="mt-2 text-sm space-y-1">
        <p><span className="text-muted-foreground">Type:</span> {lead.business_type || "—"}</p>
        <p><span className="text-muted-foreground">Address:</span> {lead.address || "—"}</p>
        <p><span className="text-muted-foreground">City:</span> {lead.city || "—"}</p>
        <p><span className="text-muted-foreground">County:</span> {lead.county || "—"}</p>
        <div><span className="text-muted-foreground">Stage:</span> <Badge variant="secondary" className="text-xs">{lead.stage}</Badge></div>
      </div>
    </div>
  );
}
