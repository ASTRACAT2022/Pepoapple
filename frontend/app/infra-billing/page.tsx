"use client";

import { useCallback, useEffect, useState } from "react";

import { AdminShell } from "../../components/admin-shell";
import { Card, Notice, SmallButton } from "../../components/ui";
import { apiRequest, formatDate } from "../../lib/api";

type InfraReport = {
  items: Array<{ provider: string; currency: string; servers: number; monthly_total: number }>;
  due: Array<{ server_id: string; host: string; next_due_at: string | null; infra_status: string; reminder_days_before: number }>;
};

export default function InfraBillingPage() {
  const [report, setReport] = useState<InfraReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await apiRequest<InfraReport>("/api/v1/infra-billing/report");
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load infra billing");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AdminShell
      title="Infra Billing"
      subtitle="Provider cost tracking and due reminders"
      actions={<SmallButton onClick={() => void load()}>Refresh</SmallButton>}
    >
      <Notice type="error" message={error} />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Monthly Cost by Provider">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Servers</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {(report?.items ?? []).map((item) => (
                  <tr key={`${item.provider}-${item.currency}`}>
                    <td>{item.provider || "unknown"}</td>
                    <td>{item.servers}</td>
                    <td>
                      {item.monthly_total} {item.currency}
                    </td>
                  </tr>
                ))}
                {(report?.items.length ?? 0) === 0 ? (
                  <tr>
                    <td colSpan={3} className="text-black/50">
                      No cost records.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Upcoming Due Dates">
          <div className="space-y-2">
            {(report?.due ?? []).map((due) => (
              <div key={due.server_id} className="rounded-lg border border-black/10 px-3 py-2 text-sm">
                <p className="font-medium">{due.host}</p>
                <p className="text-black/60">
                  Next due: {formatDate(due.next_due_at)} | status: {due.infra_status} | remind {due.reminder_days_before}d before
                </p>
              </div>
            ))}
            {(report?.due.length ?? 0) === 0 ? <p className="text-sm text-black/55">No due items.</p> : null}
          </div>
        </Card>
      </div>
    </AdminShell>
  );
}
