"use client";

import { useRef, useEffect } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Badge } from "@/components/ui/badge";
import type { Lead } from "@/lib/types";

function getScoreColor(score: number): string {
  if (score >= 70) return "bg-emerald-500/15 text-emerald-400 border-emerald-500/20";
  if (score >= 50) return "bg-amber-500/15 text-amber-400 border-amber-500/20";
  if (score >= 30) return "bg-blue-500/15 text-blue-400 border-blue-500/20";
  return "bg-slate-500/15 text-slate-400 border-slate-500/20";
}

interface KanbanCardProps {
  lead: Lead;
  onClick: () => void;
}

export function KanbanCard({ lead, onClick }: KanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: lead.id });

  const justDragged = useRef(false);

  useEffect(() => {
    if (isDragging) justDragged.current = true;
  }, [isDragging]);

  const handleClick = () => {
    if (justDragged.current) {
      justDragged.current = false;
      return;
    }
    onClick();
  };

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      role="button"
      aria-label={`${lead.business_name}, score ${lead.pos_score}, ${lead.city || "unknown city"}`}
      className="glass rounded-lg p-3 space-y-2 cursor-grab active:cursor-grabbing glow-hover transition-all duration-200"
      onClick={handleClick}
    >
      <p className="font-medium text-sm line-clamp-2">{lead.business_name}</p>
      <div className="flex items-center gap-2 flex-wrap">
        <Badge variant="outline" className="text-xs">
          {lead.business_type || "other"}
        </Badge>
        <Badge variant="outline" className={`text-xs ${getScoreColor(lead.pos_score)}`}>
          {lead.pos_score}
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground">
        {lead.city || "Unknown"}{lead.county ? `, ${lead.county}` : ""}
      </p>
    </div>
  );
}
