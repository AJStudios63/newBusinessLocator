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
      className={`flex-shrink-0 w-72 rounded-xl p-3 transition-all duration-200 ${
        isOver
          ? "glass ring-2 ring-primary/50 shadow-lg shadow-primary/10"
          : "glass-subtle"
      }`}
    >
      <div className="flex items-center justify-between mb-3 px-1">
        <h3 className="font-semibold text-sm">{stage}</h3>
        <span className="text-xs text-muted-foreground glass-subtle rounded-full px-2 py-0.5">
          {leads.length}
        </span>
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

  const collisionDetection: CollisionDetection = (args) => {
    const pointerCollisions = pointerWithin(args);
    const columnCollisions = pointerCollisions.filter(
      (collision) => typeof collision.id === "string" && STAGES.includes(collision.id as Stage)
    );

    if (columnCollisions.length > 0) {
      return columnCollisions;
    }

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

    let targetStage: Stage | null = null;

    if (typeof overId === "string" && STAGES.includes(overId as Stage)) {
      targetStage = overId as Stage;
    } else {
      for (const stage of STAGES) {
        if (data.columns[stage].some((l) => l.id === overId)) {
          targetStage = stage;
          break;
        }
      }
    }

    if (!targetStage) return;

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
      <div className="flex gap-4 overflow-x-auto pb-4 custom-scrollbar">
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
          <div className="w-72 glass rounded-xl p-3 shadow-xl opacity-90">
            <p className="font-medium text-sm">{activeLead.business_name}</p>
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
