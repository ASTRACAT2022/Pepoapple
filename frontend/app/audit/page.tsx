"use client";

import { useCallback, useEffect, useState } from "react";

import { AdminShell } from "../../components/admin-shell";
import { Card, Notice, SmallButton } from "../../components/ui";
import { apiRequest, formatDate } from "../../lib/api";

type AuditLog = {
  id: string;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [actionFilter, setActionFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("limit", "200");
      if (actionFilter) {
        params.set("action", actionFilter);
      }
      if (entityFilter) {
        params.set("entity_type", entityFilter);
      }

      const data = await apiRequest<{ items: AuditLog[] }>(`/api/v1/audit/logs?${params.toString()}`);
      setLogs(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit logs");
    }
  }, [actionFilter, entityFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AdminShell
      title="Audit"
      subtitle="Track security-relevant actions and operational changes"
      actions={<SmallButton onClick={() => void load()}>Refresh</SmallButton>}
    >
      <Notice type="error" message={error} />

      <Card title="Filters">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <input className="input" placeholder="action" value={actionFilter} onChange={(e) => setActionFilter(e.target.value)} />
          <input className="input" placeholder="entity_type" value={entityFilter} onChange={(e) => setEntityFilter(e.target.value)} />
          <button className="btn" type="button" onClick={() => void load()}>
            Apply Filters
          </button>
        </div>
      </Card>

      <Card title={`Audit Logs (${logs.length})`}>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Entity</th>
                <th>Payload</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td>{formatDate(log.created_at)}</td>
                  <td>{log.actor}</td>
                  <td>{log.action}</td>
                  <td>
                    {log.entity_type} / <span className="font-mono text-xs">{log.entity_id.slice(0, 10)}</span>
                  </td>
                  <td>
                    <pre className="max-w-[500px] overflow-x-auto rounded-md bg-black/5 p-2 text-xs">{JSON.stringify(log.payload, null, 2)}</pre>
                  </td>
                </tr>
              ))}
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-black/50">
                    No audit logs found for this filter.
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
