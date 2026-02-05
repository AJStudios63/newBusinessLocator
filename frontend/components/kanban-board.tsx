"use client";

import { useState } from "react";
import {
  DndContext,
  DragOverlay,
  pointerWithin,
  rectIntersection,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  type DragEndEvent,
  type DragStartEvent,
  type CollisionDetection,
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

interface DroppableColumnProps {
  stage: Stage;
  leads: Lead[];
  onCardClick: (lead: Lead) => void;
}

function DroppableColumn({ stage, leads, onCardClick }: DroppableColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: stage });

  return (
    <div
      ref={setNodeRef}
      className={`flex-shrink-0 w-72 rounded-lg p-3 transition-colors ${
        isOver ? "bg-primary/10 ring-2 ring-primary" : "bg-muted/50"
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-sm">{stage}</h3>
        <span className="text-xs text-muted-foreground">{leads.length}</span>
      </div>
      <SortableContext
        id={stage}
        items={leads.map((l) => l.id)}
        strategy={verticalListSortingStrategy}
      >
        <div className="space-y-2 min-h-[100px]">
          {leads.map((lead) => (
            <KanbanCard
              key={lead.id}
              lead={lead}
              onClick={() => onCardClick(lead)}
            />
          ))}
        </div>
      </SortableContext>
    </div>
  );
}

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

  // Custom collision detection that prefers droppable columns over sortable items
  const collisionDetection: CollisionDetection = (args) => {
    // First check for pointer within droppables (columns)
    const pointerCollisions = pointerWithin(args);

    // Filter to only column droppables (string IDs that match stage names)
    const columnCollisions = pointerCollisions.filter(
      (collision) => typeof collision.id === "string" && STAGES.includes(collision.id as Stage)
    );

    // If we're over a column, use that
    if (columnCollisions.length > 0) {
      return columnCollisions;
    }

    // Otherwise fall back to rect intersection for cards
    return rectIntersection(args);
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as number);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const leadId = active.id as number;
    const overId = over.id;

    // Determine target stage - could be a stage name (string) or a lead id (number)
    let targetStage: Stage | null = null;

    if (typeof overId === "string" && STAGES.includes(overId as Stage)) {
      // Dropped directly on a column
      targetStage = overId as Stage;
    } else {
      // Dropped on another card - find which column that card is in
      for (const stage of STAGES) {
        if (data.columns[stage].some((l) => l.id === overId)) {
          targetStage = stage;
          break;
        }
      }
    }

    if (!targetStage) return;

    // Find current stage of the lead being dragged
    let currentStage: Stage | null = null;
    for (const stage of STAGES) {
      if (data.columns[stage].some((l) => l.id === leadId)) {
        currentStage = stage;
        break;
      }
    }

    if (currentStage && currentStage !== targetStage) {
      mutation.mutate({ id: leadId, stage: targetStage });
    }
  };

  const activeLead = activeId
    ? STAGES.flatMap((s) => data.columns[s]).find((l) => l.id === activeId)
    : null;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={collisionDetection}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4">
        {STAGES.map((stage) => (
          <DroppableColumn
            key={stage}
            stage={stage}
            leads={data.columns[stage]}
            onCardClick={onCardClick}
          />
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
