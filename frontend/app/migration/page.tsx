"use client";

import { useCallback, useEffect, useState } from "react";

import { AdminShell } from "../../components/admin-shell";
import { Card, Notice, SmallButton } from "../../components/ui";
import { apiRequest, formatDate, safeJsonParse } from "../../lib/api";

type MigrationRun = {
  id: string;
  mode: string;
  status: string;
  details: Record<string, unknown>;
};

export default function MigrationPage() {
  const [runs, setRuns] = useState<MigrationRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [mode, setMode] = useState("dry-run");
  const [payloadText, setPayloadText] = useState('{"users":[],"servers":[],"squads":[],"legacy_tokens":[]}');

  const [legacyForm, setLegacyForm] = useState({ user_id: "", legacy_token: "", subscription_token: "" });

  const load = useCallback(async () => {
    setError(null);
    try {
      setRuns(await apiRequest<MigrationRun[]>("/api/v1/migration/runs"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load migration runs");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AdminShell
      title="Migration"
      subtitle="Run dry-run/apply/verify and maintain legacy token mapping"
      actions={<SmallButton onClick={() => void load()}>Refresh</SmallButton>}
    >
      <Notice type="error" message={error} />
      <Notice type="success" message={success} />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Run Migration">
          <div className="space-y-3">
            <div>
              <label className="label">Mode</label>
              <select className="select" value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="dry-run">dry-run</option>
                <option value="apply">apply</option>
                <option value="verify">verify</option>
              </select>
            </div>
            <div>
              <label className="label">Payload JSON</label>
              <textarea className="textarea" value={payloadText} onChange={(e) => setPayloadText(e.target.value)} />
            </div>
            <button
              className="btn"
              type="button"
              onClick={async () => {
                setError(null);
                setSuccess(null);
                try {
                  await apiRequest("/api/v1/migration/run", {
                    method: "POST",
                    body: JSON.stringify({
                      mode,
                      payload: safeJsonParse(payloadText, {}),
                    }),
                  });
                  setSuccess(`Migration ${mode} executed`);
                  await load();
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Migration request failed");
                }
              }}
            >
              Run
            </button>
          </div>
        </Card>

        <Card title="Legacy Token Map">
          <div className="space-y-2">
            <input className="input" placeholder="user_id" value={legacyForm.user_id} onChange={(e) => setLegacyForm({ ...legacyForm, user_id: e.target.value })} />
            <input
              className="input"
              placeholder="legacy_token"
              value={legacyForm.legacy_token}
              onChange={(e) => setLegacyForm({ ...legacyForm, legacy_token: e.target.value })}
            />
            <input
              className="input"
              placeholder="subscription_token"
              value={legacyForm.subscription_token}
              onChange={(e) => setLegacyForm({ ...legacyForm, subscription_token: e.target.value })}
            />
            <button
              className="btn"
              type="button"
              disabled={!legacyForm.user_id || !legacyForm.legacy_token || !legacyForm.subscription_token}
              onClick={async () => {
                setError(null);
                setSuccess(null);
                try {
                  await apiRequest("/api/v1/migration/legacy-token-map", {
                    method: "POST",
                    body: JSON.stringify(legacyForm),
                  });
                  setSuccess("Legacy mapping created");
                  setLegacyForm({ user_id: "", legacy_token: "", subscription_token: "" });
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Failed to create mapping");
                }
              }}
            >
              Create Mapping
            </button>
          </div>
        </Card>
      </div>

      <Card title="Migration Runs">
        <div className="space-y-3">
          {runs.map((run) => (
            <div key={run.id} className="rounded-lg border border-black/10 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">
                  {run.mode} / {run.status}
                </p>
                <p className="font-mono text-xs text-black/55">{run.id}</p>
              </div>
              <pre className="mt-2 overflow-x-auto rounded-md bg-black/5 p-2 text-xs">{JSON.stringify(run.details, null, 2)}</pre>
            </div>
          ))}
          {runs.length === 0 ? <p className="text-sm text-black/55">No migration runs yet.</p> : null}
        </div>
      </Card>
    </AdminShell>
  );
}
