"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { AppShell } from "@/components/app-shell";
import { StatsCards } from "@/components/stats-cards";
import { TypePieChart, CountyBarChart, StageBarChart } from "@/components/charts";
import { getStats, triggerPipelineRun, getPipelineStatus, getDuplicatesCount } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Loader2, Play, Copy, ArrowRight, Clock, Zap, TrendingUp } from "lucide-react";
import Link from "next/link";
import { formatLocalDateTime } from "@/lib/utils";

export default function DashboardPage() {
  const queryClient = useQueryClient();

  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });

  const { data: pipelineStatus, refetch: refetchStatus } = useQuery({
    queryKey: ["pipelineStatus"],
    queryFn: getPipelineStatus,
    refetchInterval: (query) => {
      return query.state.data?.running ? 2000 : false;
    },
  });

  useEffect(() => {
    if (pipelineStatus && !pipelineStatus.running) {
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    }
  }, [pipelineStatus?.running]);

  const { data: duplicatesData } = useQuery({
    queryKey: ["duplicatesCount"],
    queryFn: getDuplicatesCount,
  });

  const handleRunPipeline = async () => {
    try {
      await triggerPipelineRun();
      toast.success("Pipeline started");
      refetchStatus();
    } catch {
      toast.error("Failed to start pipeline");
    }
  };

  if (isLoading || !stats) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Monitor your lead pipeline and business intelligence
            </p>
          </div>
          <Button
            onClick={handleRunPipeline}
            disabled={pipelineStatus?.running}
            size="lg"
          >
            {pipelineStatus?.running ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run Pipeline
              </>
            )}
          </Button>
        </div>

        {/* Stats */}
        <StatsCards stats={stats} />

        {/* Charts */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <TypePieChart data={stats.by_type} />
          <CountyBarChart data={stats.by_county} />
          <StageBarChart data={stats.by_stage} />
        </div>

        {/* Bottom row: Alerts & Info */}
        <div className="grid gap-6 md:grid-cols-2">
          {duplicatesData && duplicatesData.count > 0 && (
            <Card className="border-warning/20">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <div className="h-8 w-8 rounded-lg bg-warning/15 flex items-center justify-center">
                    <Copy className="h-4 w-4 text-warning" />
                  </div>
                  Potential Duplicates
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold tracking-tight">
                  {duplicatesData.count}
                </p>
                <p className="text-sm text-muted-foreground mb-4">
                  leads to review and merge
                </p>
                <Link href="/duplicates">
                  <Button variant="outline" size="sm">
                    Review Now
                    <ArrowRight className="ml-2 h-3.5 w-3.5" />
                  </Button>
                </Link>
              </CardContent>
            </Card>
          )}

          {stats.last_run && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <div className="h-8 w-8 rounded-lg bg-primary/15 flex items-center justify-center">
                    <Clock className="h-4 w-4 text-primary" />
                  </div>
                  Last Pipeline Run
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground text-xs uppercase tracking-wider mb-1">Started</p>
                    <p className="font-medium">
                      {formatLocalDateTime(stats.last_run.run_started_at)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs uppercase tracking-wider mb-1">Status</p>
                    <p className="font-medium capitalize flex items-center gap-1.5">
                      {stats.last_run.status === "completed" ? (
                        <Zap className="h-3.5 w-3.5 text-success" />
                      ) : (
                        <TrendingUp className="h-3.5 w-3.5 text-warning" />
                      )}
                      {stats.last_run.status}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs uppercase tracking-wider mb-1">Found</p>
                    <p className="font-medium">{stats.last_run.leads_found}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs uppercase tracking-wider mb-1">New</p>
                    <p className="font-medium">{stats.last_run.leads_new}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </AppShell>
  );
}
