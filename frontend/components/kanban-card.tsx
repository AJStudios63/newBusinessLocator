"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Lead } from "@/lib/types";

function getScoreColor(score: number): string {
  if (score >= 70) return "bg-green-100 text-green-700 border-green-300";
  if (score >= 50) return "bg-yellow-100 text-yellow-700 border-yellow-300";
  if (score >= 30) return "bg-blue-100 text-blue-700 border-blue-300";
  return "bg-gray-100 text-gray-600 border-gray-300";
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

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <Card
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="cursor-grab active:cursor-grabbing"
      onClick={onClick}
    >
      <CardContent className="p-3 space-y-2">
        <p className="font-medium text-sm line-clamp-2">{lead.business_name}</p>
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="outline" className="text-xs">
            {lead.business_type || "other"}
          </Badge>
          <Badge variant="outline" className={`text-xs ${getScoreColor(lead.pos_score)}`}>
            {lead.pos_score}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">{lead.city || "Unknown"}</p>
      </CardContent>
    </Card>
  );
}
