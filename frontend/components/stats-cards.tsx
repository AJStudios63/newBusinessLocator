"use client";

import type { Stats } from "@/lib/types";
import { Users, Target, Sparkles, CheckCircle2 } from "lucide-react";

interface StatsCardsProps {
  stats: Stats;
}

const statConfig = [
  {
    key: "total_leads" as const,
    label: "Total Leads",
    icon: Users,
    gradient: "from-blue-500/20 to-indigo-500/20",
    iconColor: "text-blue-400",
    getValue: (stats: Stats) => stats.total_leads,
  },
  {
    key: "avg_score" as const,
    label: "Avg Score",
    icon: Target,
    gradient: "from-purple-500/20 to-pink-500/20",
    iconColor: "text-purple-400",
    getValue: (stats: Stats) => stats.avg_score.toFixed(1),
  },
  {
    key: "new_leads" as const,
    label: "New Leads",
    icon: Sparkles,
    gradient: "from-emerald-500/20 to-teal-500/20",
    iconColor: "text-emerald-400",
    getValue: (stats: Stats) => stats.by_stage["New"] || 0,
  },
  {
    key: "qualified" as const,
    label: "Qualified",
    icon: CheckCircle2,
    gradient: "from-amber-500/20 to-orange-500/20",
    iconColor: "text-amber-400",
    getValue: (stats: Stats) => stats.by_stage["Qualified"] || 0,
  },
];

export function StatsCards({ stats }: StatsCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {statConfig.map((stat) => {
        const Icon = stat.icon;
        const value = stat.getValue(stats);
        return (
          <div
            key={stat.key}
            className="glass glow-hover rounded-xl p-5 transition-all duration-300 animate-slide-in"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-muted-foreground">
                {stat.label}
              </p>
              <div className={`h-9 w-9 rounded-lg bg-gradient-to-br ${stat.gradient} flex items-center justify-center`}>
                <Icon className={`h-4.5 w-4.5 ${stat.iconColor}`} />
              </div>
            </div>
            <div className="mt-3">
              <p className="text-3xl font-bold tracking-tight">{value}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
