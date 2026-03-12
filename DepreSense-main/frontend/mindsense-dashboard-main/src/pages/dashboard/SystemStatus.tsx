import { useEffect, useState, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, Server, Database, Cpu, CheckCircle, XCircle, RefreshCw } from "lucide-react";
import { getSystemStatus, type SystemStatusResponse } from "@/lib/api";

interface SystemMetric {
  name: string;
  status: string;
  uptime: string;
  icon: typeof Server;
}

const REFRESH_INTERVAL_MS = 30_000; // 30 seconds

const SystemStatus = () => {
  // ── State ────────────────────────────────────────────────
  const [systemMetrics, setSystemMetrics] = useState<SystemMetric[]>([
    { name: "API Server", status: "Loading…", uptime: "—", icon: Server },
    { name: "Database", status: "Loading…", uptime: "—", icon: Database },
    { name: "ML Model", status: "Loading…", uptime: "—", icon: Cpu },
  ]);
  const [totalAnalysesToday, setTotalAnalysesToday] = useState<number | null>(null);
  const [avgProcessingTime, setAvgProcessingTime] = useState<number | null>(null);
  const [modelVersion, setModelVersion] = useState<string>("—");
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Fetch system status ──────────────────────────────────
  const fetchStatus = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const data: SystemStatusResponse = await getSystemStatus();

      // Build metrics from response
      const metrics: SystemMetric[] = [
        {
          name: "API Server",
          status: data.api.status === "operational" ? "Operational" : "Offline",
          uptime: data.api.uptime,
          icon: Server,
        },
        {
          name: "Database",
          status: data.database.status === "operational" ? "Operational" : "Offline",
          uptime: data.database.uptime,
          icon: Database,
        },
        {
          name: "ML Model",
          status: data.model.status === "operational" ? "Operational" : "Unavailable",
          uptime: data.model.uptime,
          icon: Cpu,
        },
      ];

      setSystemMetrics(metrics);
      setTotalAnalysesToday(data.metrics.totalAnalysesToday);
      setAvgProcessingTime(data.metrics.avgProcessingTime);
      setModelVersion(data.metrics.modelVersion);
      setLastRefreshed(new Date());
    } catch {
      // API is unreachable — mark everything as offline / connection error
      setSystemMetrics([
        { name: "API Server", status: "Offline", uptime: "Connection error", icon: Server },
        { name: "Database", status: "Offline", uptime: "Connection error", icon: Database },
        { name: "ML Model", status: "Unavailable", uptime: "Connection error", icon: Cpu },
      ]);
      setTotalAnalysesToday(null);
      setAvgProcessingTime(null);
      setModelVersion("—");
      setLastRefreshed(new Date());
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  // ── On mount + auto-refresh every 30s ────────────────────
  useEffect(() => {
    fetchStatus();

    intervalRef.current = setInterval(fetchStatus, REFRESH_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchStatus]);

  // ── Helpers ──────────────────────────────────────────────
  const isOperational = (status: string) =>
    status.toLowerCase() === "operational";

  const StatusIcon = ({ status }: { status: string }) =>
    isOperational(status) ? (
      <CheckCircle className="h-5 w-5 text-success" />
    ) : (
      <XCircle className="h-5 w-5 text-destructive" />
    );

  const statusColor = (status: string) =>
    isOperational(status) ? "text-success" : "text-destructive";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">System Status</h1>
          <p className="text-muted-foreground">Monitor system health and performance</p>
        </div>
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          {lastRefreshed && (
            <span>
              Last updated: {lastRefreshed.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={fetchStatus}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 rounded-md border border-input bg-background px-3 py-1.5 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {systemMetrics.map((metric) => (
          <Card key={metric.name}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">{metric.name}</CardTitle>
              <metric.icon className="h-5 w-5 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <StatusIcon status={metric.status} />
                <span className={`text-lg font-semibold ${statusColor(metric.status)}`}>
                  {metric.status}
                </span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">Uptime: {metric.uptime}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            System Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-lg bg-muted/50 p-4">
              <span>Total Analyses Today</span>
              <span className="text-2xl font-bold text-primary">
                {totalAnalysesToday !== null ? totalAnalysesToday : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-muted/50 p-4">
              <span>Average Processing Time</span>
              <span className="text-2xl font-bold text-primary">
                {avgProcessingTime !== null ? `${avgProcessingTime}s` : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-muted/50 p-4">
              <span>Model Version</span>
              <span className="text-2xl font-bold text-primary">{modelVersion}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SystemStatus;
