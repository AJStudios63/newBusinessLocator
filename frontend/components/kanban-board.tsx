"use client";

import { useState } from "react";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { KanbanCard } from "./kanban-card";
import { Card, CardContent } from "@/components/ui/card";
import { updateLeadStage } from "@/lib/api";
import { STAGES, type Lead, type Stage, type KanbanData } from "@/lib/types";

interface KanbanBoardProps {
  data: KanbanData;
  onCardClick: (lead: Lead) => void;
}

export function KanbanBoard({ data, onCardClick }: KanbanBoardProps) {
  const [activeId, setActiveId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  const mutation = useMutation({
    mutationFn: ({ id, stage }: { id: number; stage: string }) =>
      updateLeadStage(id, stage),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
    onError: () => {
      toast.error("Failed to move lead");
    },
  });

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as number);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const leadId = active.id as number;
    const targetStage = over.id as Stage;

    // Find current stage of the lead
    let currentStage: Stage | null = null;
    for (const stage of STAGES) {
      if (data.columns[stage].some((l) => l.id === leadId)) {
        currentStage = stage;
        break;
      }
    }

    if (currentStage && currentStage !== targetStage && STAGES.includes(targetStage)) {
      mutation.mutate({ id: leadId, stage: targetStage });
    }
  };

  const activeLead = activeId
    ? STAGES.flatMap((s) => data.columns[s]).find((l) => l.id === activeId)
    : null;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4">
        {STAGES.map((stage) => (
          <div
            key={stage}
            id={stage}
            className="flex-shrink-0 w-72 bg-muted/50 rounded-lg p-3"
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm">{stage}</h3>
              <span className="text-xs text-muted-foreground">
                {data.columns[stage].length}
              </span>
            </div>
            <SortableContext
              id={stage}
              items={data.columns[stage].map((l) => l.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2 min-h-[100px]">
                {data.columns[stage].map((lead) => (
                  <KanbanCard
                    key={lead.id}
                    lead={lead}
                    onClick={() => onCardClick(lead)}
                  />
                ))}
              </div>
            </SortableContext>
          </div>
        ))}
      </div>
      <DragOverlay>
        {activeLead && (
          <Card className="w-72 opacity-80">
            <CardContent className="p-3">
              <p className="font-medium text-sm">{activeLead.business_name}</p>
            </CardContent>
          </Card>
        )}
      </DragOverlay>
    </DndContext>
  );
}
