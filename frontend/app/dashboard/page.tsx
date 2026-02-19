"use client";

import { useCallback, useEffect, useState } from "react";

import { AdminShell } from "../../components/admin-shell";
import { Card, Notice, SmallButton } from "../../components/ui";
import { apiRequest, formatBytes, formatDate } from "../../lib/api";

type AnalyticsOverview = {
  users: { total: number; active: number };
  nodes: { total: number; online: number };
  traffic: { total_bytes: number; per_day: Array<{ day: string; bytes: number }> };
};

type NodeItem = {
  id: string;
  server_id: string;
  status: string;
  desired_config_revision: number;
  applied_config_revision: number;
  last_apply_status: string;
  last_seen_at: string | null;
};

type Health = { status: string };

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [nodes, setNodes] = useState<NodeItem[]>([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthData, overviewData, nodesData] = await Promise.all([
        apiRequest<Health>("/api/v1/health"),
        apiRequest<AnalyticsOverview>("/api/v1/analytics/overview"),
        apiRequest<NodeItem[]>("/api/v1/nodes"),
      ]);
      setHealth(healthData);
      setOverview(overviewData);
      setNodes(nodesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  return (
    <AdminShell
      title="Dashboard"
      subtitle="Operational snapshot across users, nodes and traffic"
      actions={<SmallButton onClick={() => void loadData()}>Refresh</SmallButton>}
    >
      <Notice type="error" message={error} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="API Health">
          <p className="text-2xl font-semibold">{health?.status ?? (loading ? "loading..." : "unknown")}</p>
        </Card>
        <Card title="Users">
          <p className="text-2xl font-semibold">{overview ? `${overview.users.active}/${overview.users.total}` : "-"}</p>
          <p className="text-sm text-black/60">active / total</p>
        </Card>
        <Card title="Nodes">
          <p className="text-2xl font-semibold">{overview ? `${overview.nodes.online}/${overview.nodes.total}` : "-"}</p>
          <p className="text-sm text-black/60">online / total</p>
        </Card>
        <Card title="Total Traffic">
          <p className="text-2xl font-semibold">{overview ? formatBytes(overview.traffic.total_bytes) : "-"}</p>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Recent Node State">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Node</th>
                  <th>Status</th>
                  <th>Apply</th>
                  <th>Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {nodes.slice(0, 12).map((node) => (
                  <tr key={node.id}>
                    <td className="font-mono text-xs">{node.id.slice(0, 10)}</td>
                    <td>{node.status}</td>
                    <td>
                      {node.last_apply_status} ({node.applied_config_revision}/{node.desired_config_revision})
                    </td>
                    <td>{formatDate(node.last_seen_at)}</td>
                  </tr>
                ))}
                {nodes.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-black/50">
                      No nodes yet
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Traffic Per Day">
          <div className="space-y-2">
            {(overview?.traffic.per_day ?? []).slice(-12).map((item) => (
              <div key={item.day} className="flex items-center justify-between rounded-lg border border-black/10 px-3 py-2 text-sm">
                <span>{item.day}</span>
                <span className="font-medium">{formatBytes(item.bytes)}</span>
              </div>
            ))}
            {(overview?.traffic.per_day.length ?? 0) === 0 ? (
              <p className="text-sm text-black/55">No traffic records yet.</p>
            ) : null}
          </div>
        </Card>
      </div>
    </AdminShell>
  );
}
