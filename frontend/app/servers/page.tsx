"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminShell } from "../../components/admin-shell";
import { Card, Notice, SmallButton } from "../../components/ui";
import { apiRequest, formatDate } from "../../lib/api";

type Server = {
  id: string;
  host: string;
  ip: string;
  provider: string;
  region: string;
  squad_id: string;
  status: string;
  price: number;
  currency: string;
  next_due_at: string | null;
  infra_status: string;
};

type InfraReport = {
  items: Array<{ provider: string; currency: string; servers: number; monthly_total: number }>;
  due: Array<{ server_id: string; host: string; next_due_at: string | null; infra_status: string; reminder_days_before: number }>;
};

export default function ServersPage() {
  const [servers, setServers] = useState<Server[]>([]);
  const [report, setReport] = useState<InfraReport | null>(null);
  const [providerFilter, setProviderFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  const providers = useMemo(() => Array.from(new Set(servers.map((server) => server.provider).filter(Boolean))), [servers]);
  const visible = useMemo(
    () => (providerFilter ? servers.filter((server) => server.provider === providerFilter) : servers),
    [servers, providerFilter],
  );

  const load = useCallback(async () => {
    setError(null);
    try {
      const [serverData, reportData] = await Promise.all([
        apiRequest<Server[]>("/api/v1/servers"),
        apiRequest<InfraReport>("/api/v1/infra-billing/report"),
      ]);
      setServers(serverData);
      setReport(reportData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load servers");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AdminShell title="Servers" subtitle="Inventory and infra-cost visibility" actions={<SmallButton onClick={() => void load()}>Refresh</SmallButton>}>
      <Notice type="error" message={error} />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Provider Spend Overview">
          <div className="space-y-2">
            {(report?.items ?? []).map((item) => (
              <div key={`${item.provider}-${item.currency}`} className="flex items-center justify-between rounded-lg border border-black/10 px-3 py-2">
                <div>
                  <p className="font-medium">{item.provider || "unknown"}</p>
                  <p className="text-xs text-black/55">{item.servers} servers</p>
                </div>
                <p className="font-semibold">
                  {item.monthly_total} {item.currency}
                </p>
              </div>
            ))}
            {(report?.items.length ?? 0) === 0 ? <p className="text-sm text-black/55">No provider data yet.</p> : null}
          </div>
        </Card>

        <Card title="Upcoming Payments">
          <div className="space-y-2">
            {(report?.due ?? []).map((due) => (
              <div key={due.server_id} className="rounded-lg border border-black/10 px-3 py-2 text-sm">
                <p className="font-medium">{due.host}</p>
                <p className="text-black/60">
                  {formatDate(due.next_due_at)} | status: {due.infra_status} | reminder: {due.reminder_days_before}d
                </p>
              </div>
            ))}
            {(report?.due.length ?? 0) === 0 ? <p className="text-sm text-black/55">No due records configured.</p> : null}
          </div>
        </Card>
      </div>

      <Card title="Server Inventory" right={<span className="text-sm text-black/60">{visible.length} shown</span>}>
        <div className="mb-3 flex items-center gap-2">
          <label className="label mb-0">Provider filter</label>
          <select className="select max-w-xs" value={providerFilter} onChange={(e) => setProviderFilter(e.target.value)}>
            <option value="">All</option>
            {providers.map((provider) => (
              <option key={provider} value={provider}>
                {provider}
              </option>
            ))}
          </select>
        </div>

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Host</th>
                <th>Provider / Region</th>
                <th>Status</th>
                <th>Price</th>
                <th>Due</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((server) => (
                <tr key={server.id}>
                  <td>
                    <div>{server.host}</div>
                    <div className="text-xs text-black/55">{server.ip}</div>
                  </td>
                  <td>
                    {server.provider || "-"} / {server.region || "-"}
                  </td>
                  <td>
                    {server.status} / {server.infra_status}
                  </td>
                  <td>
                    {server.price} {server.currency}
                  </td>
                  <td>{formatDate(server.next_due_at)}</td>
                </tr>
              ))}
              {visible.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-black/50">
                    No servers found.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Card>
    </AdminShell>
  );
}
