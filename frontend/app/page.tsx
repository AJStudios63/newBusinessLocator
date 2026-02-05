"use client";

import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { StatsCards } from "@/components/stats-cards";
import { TypePieChart, CountyBarChart } from "@/components/charts";
import { getStats, triggerPipelineRun, getPipelineStatus } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Loader2, Play } from "lucide-react";

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });

  const { data: pipelineStatus, refetch: refetchStatus } = useQuery({
    queryKey: ["pipelineStatus"],
    queryFn: getPipelineStatus,
    refetchInterval: (query) => {
      // Poll while pipeline is running
      return query.state.data?.running ? 2000 : false;
    },
  });

  const handleRunPipeline = async () => {
    try {
      await triggerPipelineRun();
      toast.success("Pipeline started");
      refetchStatus();
    } catch (error) {
      toast.error("Failed to start pipeline");
    }
  };

  if (isLoading || !stats) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <Button
            onClick={handleRunPipeline}
            disabled={pipelineStatus?.running}
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

        <StatsCards stats={stats} />

        <div className="grid gap-4 md:grid-cols-2">
          <TypePieChart data={stats.by_type} />
          <CountyBarChart data={stats.by_county} />
        </div>

        {stats.last_run && (
          <Card>
            <CardHeader>
              <CardTitle>Last Pipeline Run</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Started</p>
                  <p className="font-medium">
                    {new Date(stats.last_run.run_started_at).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Status</p>
                  <p className="font-medium capitalize">{stats.last_run.status}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Found</p>
                  <p className="font-medium">{stats.last_run.leads_found}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">New</p>
                  <p className="font-medium">{stats.last_run.leads_new}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
