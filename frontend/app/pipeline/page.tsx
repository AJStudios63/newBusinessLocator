"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import { getPipelineRuns, getPipelineStatus, triggerPipelineRun } from "@/lib/api";
import { Loader2, Play, CheckCircle, XCircle, Clock } from "lucide-react";
import { formatLocalDateTime } from "@/lib/utils";

export default function PipelinePage() {
  const queryClient = useQueryClient();

  const { data: runs, isLoading } = useQuery({
    queryKey: ["pipelineRuns"],
    queryFn: () => getPipelineRuns(20),
  });

  const { data: status, refetch: refetchStatus } = useQuery({
    queryKey: ["pipelineStatus"],
    queryFn: getPipelineStatus,
    refetchInterval: (query) => {
      return query.state.data?.running ? 2000 : false;
    },
  });

  useEffect(() => {
    if (status && !status.running) {
      queryClient.invalidateQueries({ queryKey: ["pipelineRuns"] });
    }
  }, [status?.running]);

  const mutation = useMutation({
    mutationFn: triggerPipelineRun,
    onSuccess: () => {
      toast.success("Pipeline started");
      refetchStatus();
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to start pipeline");
    },
  });

  const formatDate = (dateStr: string | null) => {
    return formatLocalDateTime(dateStr) || "—";
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-emerald-400" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-400" />;
      case "running":
        return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Pipeline</h1>
            <p className="text-muted-foreground mt-1">
              ETL pipeline runs and execution history
            </p>
          </div>
          <Button
            onClick={() => mutation.mutate()}
            disabled={status?.running || mutation.isPending}
            size="lg"
          >
            {status?.running ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run Pipeline Now
              </>
            )}
          </Button>
        </div>

        {status?.last_result && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Latest Result</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Status</p>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(status.last_result.status)}
                    <span className="font-medium capitalize">
                      {status.last_result.status}
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Run ID</p>
                  <p className="font-medium font-mono text-sm">{status.last_result.run_id || "—"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Found</p>
                  <p className="font-medium text-lg">{status.last_result.leads_found ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">New</p>
                  <p className="font-medium text-lg">{status.last_result.leads_new ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Duplicates</p>
                  <p className="font-medium text-lg">{status.last_result.leads_dupes ?? "—"}</p>
                </div>
              </div>
              {status.last_result.error && (
                <p className="mt-4 text-sm text-destructive glass-subtle rounded-lg p-3">
                  Error: {status.last_result.error}
                </p>
              )}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Run History</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : (
              <div className="rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="border-b border-border/50 hover:bg-transparent">
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">ID</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Started</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Finished</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Status</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold text-right">Found</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold text-right">New</TableHead>
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground font-semibold text-right">Dupes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {runs?.runs.map((run) => (
                      <TableRow key={run.id} className="border-b border-border/30 hover:bg-accent/5 transition-colors">
                        <TableCell className="font-mono text-sm">{run.id}</TableCell>
                        <TableCell className="text-muted-foreground">{formatDate(run.run_started_at)}</TableCell>
                        <TableCell className="text-muted-foreground">{formatDate(run.run_finished_at)}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getStatusIcon(run.status)}
                            <Badge
                              variant={
                                run.status === "completed"
                                  ? "success"
                                  : run.status === "failed"
                                  ? "destructive"
                                  : "secondary"
                              }
                              className="text-xs"
                            >
                              {run.status}
                            </Badge>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-medium">{run.leads_found}</TableCell>
                        <TableCell className="text-right font-medium">{run.leads_new}</TableCell>
                        <TableCell className="text-right font-medium">{run.leads_dupes}</TableCell>
                      </TableRow>
                    ))}
                    {(!runs?.runs || runs.runs.length === 0) && (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                          No pipeline runs yet
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
