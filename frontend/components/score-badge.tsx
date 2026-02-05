"use client";

import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { HelpCircle } from "lucide-react";
import type { Lead } from "@/lib/types";

interface ScoreBadgeProps {
  lead: Lead;
  showLabel?: boolean;
}

function getScoreInfo(score: number): { label: string; color: string; bgColor: string } {
  if (score >= 70) {
    return { label: "Hot", color: "text-emerald-400", bgColor: "bg-emerald-500/15 border-emerald-500/20" };
  } else if (score >= 50) {
    return { label: "Warm", color: "text-amber-400", bgColor: "bg-amber-500/15 border-amber-500/20" };
  } else if (score >= 30) {
    return { label: "Cool", color: "text-blue-400", bgColor: "bg-blue-500/15 border-blue-500/20" };
  } else {
    return { label: "Cold", color: "text-slate-400", bgColor: "bg-slate-500/15 border-slate-500/20" };
  }
}

function estimateBreakdown(lead: Lead): {
  typeScore: number;
  sourceScore: number;
  addressScore: number;
  recencyScore: number;
} {
  const typeScores: Record<string, number> = {
    restaurant: 50, bar: 48, cafe: 45, retail: 45, liquor: 42,
    salon: 40, bakery: 40, spa: 38, food_service: 35, automotive: 25,
    services: 20, other: 10, consulting: 5, real_estate: 5, construction: 5,
  };
  const typeScore = typeScores[lead.business_type || "other"] || 10;

  const sourceScores: Record<string, number> = {
    license_table: 20, news_article: 15, search_snippet: 8,
  };
  const sourceScore = sourceScores[lead.source_type || ""] || 0;

  let addressScore = 0;
  if (lead.address && lead.city && lead.zip_code) addressScore = 15;
  else if (lead.address && lead.city) addressScore = 10;
  else if (lead.city) addressScore = 5;

  let recencyScore = 0;
  if (lead.license_date) {
    const licenseDate = new Date(lead.license_date);
    const daysAgo = Math.floor((Date.now() - licenseDate.getTime()) / (1000 * 60 * 60 * 24));
    if (daysAgo <= 7) recencyScore = 15;
    else if (daysAgo <= 14) recencyScore = 10;
    else if (daysAgo <= 30) recencyScore = 5;
  }

  return { typeScore, sourceScore, addressScore, recencyScore };
}

export function ScoreBadge({ lead, showLabel = true }: ScoreBadgeProps) {
  const score = lead.pos_score;
  const { label, color, bgColor } = getScoreInfo(score);
  const breakdown = estimateBreakdown(lead);

  return (
    <TooltipProvider>
      <Tooltip delayDuration={300}>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={`${bgColor} ${color} cursor-help gap-1`}
          >
            {showLabel && <span className="font-semibold">{label}</span>}
            <span>{score}</span>
            <HelpCircle className="h-3 w-3 opacity-60" />
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs p-3 glass-strong">
          <div className="space-y-2">
            <p className="font-semibold text-sm">Lead Quality Score</p>
            <p className="text-xs text-muted-foreground">
              POS system purchase likelihood and data reliability.
            </p>
            <div className="text-xs space-y-1.5 pt-1 border-t border-border/50">
              <div className="flex justify-between">
                <span>Business Type ({lead.business_type || "other"})</span>
                <span className="font-mono text-primary">{breakdown.typeScore}/50</span>
              </div>
              <div className="flex justify-between">
                <span>Source ({lead.source_type || "unknown"})</span>
                <span className="font-mono text-primary">{breakdown.sourceScore}/20</span>
              </div>
              <div className="flex justify-between">
                <span>Address Completeness</span>
                <span className="font-mono text-primary">{breakdown.addressScore}/15</span>
              </div>
              <div className="flex justify-between">
                <span>Recency</span>
                <span className="font-mono text-primary">{breakdown.recencyScore}/15</span>
              </div>
              <div className="flex justify-between pt-1 border-t border-border/50 font-semibold">
                <span>Total</span>
                <span className="font-mono">{score}/100</span>
              </div>
            </div>
            <div className="text-xs pt-1 border-t border-border/50">
              <span className="font-semibold">Guide:</span>
              <div className="grid grid-cols-2 gap-x-2 mt-1">
                <span className="text-emerald-400">70+ = Hot</span>
                <span className="text-amber-400">50-69 = Warm</span>
                <span className="text-blue-400">30-49 = Cool</span>
                <span className="text-slate-400">&lt;30 = Cold</span>
              </div>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function ScoreCell({ score }: { score: number }) {
  const { label, color } = getScoreInfo(score);

  return (
    <TooltipProvider>
      <Tooltip delayDuration={300}>
        <TooltipTrigger asChild>
          <span className={`font-medium cursor-help ${color}`}>
            {score}
          </span>
        </TooltipTrigger>
        <TooltipContent side="left" className="text-xs glass-strong">
          <p><span className="font-semibold">{label}</span> lead quality</p>
          <p className="text-muted-foreground">Click row for breakdown</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
