"use client";

import { useState, useEffect } from "react";
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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { Save, Trash2 } from "lucide-react";
import type { LeadFilters } from "@/lib/types";

const PRESETS_STORAGE_KEY = "lead-filter-presets";

interface FilterPreset {
  id: string;
  name: string;
  filters: LeadFilters;
  createdAt: string;
}

interface FilterPresetsProps {
  currentFilters: LeadFilters;
  onApplyPreset: (filters: LeadFilters) => void;
}

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

function loadPresets(): FilterPreset[] {
  if (typeof window === "undefined") return [];
  try {
    const stored = localStorage.getItem(PRESETS_STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function savePresets(presets: FilterPreset[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(presets));
}

export function FilterPresets({ currentFilters, onApplyPreset }: FilterPresetsProps) {
  const [presets, setPresets] = useState<FilterPreset[]>([]);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [presetName, setPresetName] = useState("");

  // Load presets on mount
  useEffect(() => {
    setPresets(loadPresets());
  }, []);

  const handleSavePreset = () => {
    if (!presetName.trim()) {
      toast.error("Please enter a preset name");
      return;
    }

    const { limit: _l, page: _p, pageSize: _ps, ...filtersToSave } = currentFilters;
    const newPreset: FilterPreset = {
      id: generateId(),
      name: presetName.trim(),
      filters: filtersToSave,
      createdAt: new Date().toISOString(),
    };

    const updated = [...presets, newPreset];
    setPresets(updated);
    savePresets(updated);
    setShowSaveDialog(false);
    setPresetName("");
    toast.success(`Saved preset "${newPreset.name}"`);
  };

  const handleDeletePreset = (id: string) => {
    const preset = presets.find((p) => p.id === id);
    const updated = presets.filter((p) => p.id !== id);
    setPresets(updated);
    savePresets(updated);
    toast.success(`Deleted preset "${preset?.name}"`);
  };

  const handleApplyPreset = (id: string) => {
    const preset = presets.find((p) => p.id === id);
    if (preset) {
      const { limit: _l, page: _p, pageSize: _ps, ...cleanFilters } = preset.filters;
      onApplyPreset(cleanFilters);
      toast.success(`Applied preset "${preset.name}"`);
    }
  };

  const hasFiltersToSave = !!(
    currentFilters.stage ||
    currentFilters.county ||
    currentFilters.q ||
    currentFilters.minScore !== undefined ||
    currentFilters.maxScore !== undefined
  );

  return (
    <div className="flex items-center gap-2">
      {presets.length > 0 && (
        <Select onValueChange={handleApplyPreset}>
          <SelectTrigger className="w-[160px] glass-subtle">
            <SelectValue placeholder="Load preset..." />
          </SelectTrigger>
          <SelectContent>
            {presets.map((preset) => (
              <div key={preset.id} className="flex items-center justify-between pr-2">
                <SelectItem value={preset.id} className="flex-1">
                  {preset.name}
                </SelectItem>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeletePreset(preset.id);
                  }}
                  className="ml-2 text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            ))}
          </SelectContent>
        </Select>
      )}

      <Button
        variant="outline"
        size="sm"
        onClick={() => setShowSaveDialog(true)}
        disabled={!hasFiltersToSave}
        title={hasFiltersToSave ? "Save current filters" : "Apply filters first"}
      >
        <Save className="mr-2 h-4 w-4" />
        Save
      </Button>

      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogContent className="glass-strong">
          <DialogHeader>
            <DialogTitle>Save Filter Preset</DialogTitle>
            <DialogDescription>
              Save your current filters for quick access later.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Input
              placeholder="Preset name (e.g., Hot Davidson Leads)"
              value={presetName}
              onChange={(e) => setPresetName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSavePreset()}
            />
            <div className="mt-4 text-sm text-muted-foreground">
              <p className="font-medium mb-2">Current filters:</p>
              <ul className="list-disc list-inside space-y-1">
                {currentFilters.stage && <li>Stage: {currentFilters.stage}</li>}
                {currentFilters.county && <li>County: {currentFilters.county}</li>}
                {currentFilters.q && <li>Search: &quot;{currentFilters.q}&quot;</li>}
                {currentFilters.minScore !== undefined && (
                  <li>Min Score: {currentFilters.minScore}</li>
                )}
                {currentFilters.maxScore !== undefined && (
                  <li>Max Score: {currentFilters.maxScore}</li>
                )}
              </ul>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSaveDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleSavePreset}>Save Preset</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
