"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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

  const mutation = useMutation({
    mutationFn: triggerPipelineRun,
    onSuccess: () => {
      toast.success("Pipeline started");
      refetchStatus();
    },
    onError: () => {
      toast.error("Failed to start pipeline");
    },
  });

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleString();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "running":
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Pipeline</h1>
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
            <CardHeader>
              <CardTitle className="text-lg">Latest Result</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(status.last_result.status)}
                    <span className="font-medium capitalize">
                      {status.last_result.status}
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Run ID</p>
                  <p className="font-medium">{status.last_result.run_id || "—"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Found</p>
                  <p className="font-medium">{status.last_result.leads_found ?? "—"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">New</p>
                  <p className="font-medium">{status.last_result.leads_new ?? "—"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Duplicates</p>
                  <p className="font-medium">{status.last_result.leads_dupes ?? "—"}</p>
                </div>
              </div>
              {status.last_result.error && (
                <p className="mt-4 text-sm text-red-500">
                  Error: {status.last_result.error}
                </p>
              )}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Run History</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead>Finished</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Found</TableHead>
                    <TableHead className="text-right">New</TableHead>
                    <TableHead className="text-right">Dupes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs?.runs.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell>{run.id}</TableCell>
                      <TableCell>{formatDate(run.run_started_at)}</TableCell>
                      <TableCell>{formatDate(run.run_finished_at)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getStatusIcon(run.status)}
                          <Badge
                            variant={
                              run.status === "completed"
                                ? "default"
                                : run.status === "failed"
                                ? "destructive"
                                : "secondary"
                            }
                          >
                            {run.status}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">{run.leads_found}</TableCell>
                      <TableCell className="text-right">{run.leads_new}</TableCell>
                      <TableCell className="text-right">{run.leads_dupes}</TableCell>
                    </TableRow>
                  ))}
                  {(!runs?.runs || runs.runs.length === 0) && (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                        No pipeline runs yet
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
