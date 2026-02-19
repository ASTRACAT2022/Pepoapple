"use client";

import { useCallback, useEffect, useState } from "react";

import { AdminShell } from "../../components/admin-shell";
import { Card, Notice, SmallButton } from "../../components/ui";
import { AuthState, apiRequest, formatDate, loadAuthState, resetAuthState, saveAuthState } from "../../lib/api";

type MeResponse = {
  principal_id: string;
  role: string;
  scopes: string[];
  reseller_id: string | null;
  auth_type: string;
};

type ApiKeyItem = {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  status: string;
  reseller_id: string | null;
  created_at: string;
};

type WebhookEndpoint = {
  id: string;
  name: string;
  target_url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
};

type WebhookDelivery = {
  id: string;
  endpoint_id: string;
  event: string;
  status: string;
  attempts: number;
  response_status: number | null;
  last_error: string;
  created_at: string;
  sent_at: string | null;
};

type BackupSnapshot = {
  id: string;
  storage_type: string;
  file_path: string;
  status: string;
  size_bytes: number;
  created_at: string;
};

export default function SettingsPage() {
  const [authState, setAuthState] = useState<AuthState>(loadAuthState());
  const [me, setMe] = useState<MeResponse | null>(null);
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([]);
  const [newApiKey, setNewApiKey] = useState<{ id: string; name: string; key: string; key_prefix: string; scopes: string[] } | null>(null);
  const [webhookEndpoints, setWebhookEndpoints] = useState<WebhookEndpoint[]>([]);
  const [webhookDeliveries, setWebhookDeliveries] = useState<WebhookDelivery[]>([]);
  const [backups, setBackups] = useState<BackupSnapshot[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [bootstrapForm, setBootstrapForm] = useState({ username: "root", password: "" });
  const [loginForm, setLoginForm] = useState({ username: "root", password: "" });
  const [apiKeyForm, setApiKeyForm] = useState({ name: "panel-key", scopes: "users.read,users.write,billing.read,billing.write,nodes.control,squads.write,api.manage,migration.run,infra.billing.read" });
  const [webhookForm, setWebhookForm] = useState({ name: "", target_url: "", secret: "", events: "user.created,order.paid,node.offline" });

  const refreshAll = useCallback(async () => {
    setError(null);
    try {
      const [meData, keyData, endpointData, deliveryData, backupData] = await Promise.all([
        apiRequest<MeResponse>("/api/v1/auth/me"),
        apiRequest<ApiKeyItem[]>("/api/v1/auth/api-keys"),
        apiRequest<WebhookEndpoint[]>("/api/v1/webhooks/endpoints"),
        apiRequest<WebhookDelivery[]>("/api/v1/webhooks/deliveries"),
        apiRequest<BackupSnapshot[]>("/api/v1/backups"),
      ]);
      setMe(meData);
      setApiKeys(keyData);
      setWebhookEndpoints(endpointData);
      setWebhookDeliveries(deliveryData);
      setBackups(backupData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings data");
    }
  }, []);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  function persistAuth(next: AuthState) {
    setAuthState(next);
    saveAuthState(next);
  }

  async function run(action: () => Promise<void>, okMessage: string) {
    setError(null);
    setSuccess(null);
    try {
      await action();
      setSuccess(okMessage);
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    }
  }

  return (
    <AdminShell title="Settings" subtitle="Auth, API keys, webhooks and backup operations" actions={<SmallButton onClick={() => void refreshAll()}>Refresh</SmallButton>}>
      <Notice type="error" message={error} />
      <Notice type="success" message={success} />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Panel Auth Mode">
          <div className="space-y-2">
            <label className="label">Mode</label>
            <select className="select" value={authState.mode} onChange={(e) => persistAuth({ ...authState, mode: e.target.value as AuthState["mode"] })}>
              <option value="scopes">X-Scopes (dev)</option>
              <option value="bearer">Bearer token</option>
              <option value="api_key">API key</option>
            </select>

            {authState.mode === "scopes" ? (
              <div>
                <label className="label">Scopes Header</label>
                <input className="input" value={authState.scopes} onChange={(e) => persistAuth({ ...authState, scopes: e.target.value })} />
              </div>
            ) : null}

            {authState.mode === "bearer" ? (
              <div>
                <label className="label">Access Token</label>
                <textarea className="textarea" value={authState.accessToken} onChange={(e) => persistAuth({ ...authState, accessToken: e.target.value })} />
              </div>
            ) : null}

            {authState.mode === "api_key" ? (
              <div>
                <label className="label">X-API-Key</label>
                <input className="input" value={authState.apiKey} onChange={(e) => persistAuth({ ...authState, apiKey: e.target.value })} />
              </div>
            ) : null}

            <div className="flex gap-2">
              <button className="btn-secondary" type="button" onClick={() => void refreshAll()}>
                Test /auth/me
              </button>
              <button
                className="btn-secondary"
                type="button"
                onClick={() => {
                  resetAuthState();
                  const next = loadAuthState();
                  setAuthState(next);
                }}
              >
                Reset Local Auth
              </button>
            </div>

            <pre className="overflow-x-auto rounded-lg bg-black/5 p-2 text-xs">{JSON.stringify(me, null, 2)}</pre>
          </div>
        </Card>

        <Card title="Bootstrap / Login">
          <div className="space-y-3">
            <div>
              <p className="label">Bootstrap Admin</p>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                <input
                  className="input"
                  placeholder="username"
                  value={bootstrapForm.username}
                  onChange={(e) => setBootstrapForm({ ...bootstrapForm, username: e.target.value })}
                />
                <input
                  className="input"
                  type="password"
                  placeholder="password"
                  value={bootstrapForm.password}
                  onChange={(e) => setBootstrapForm({ ...bootstrapForm, password: e.target.value })}
                />
              </div>
              <button
                className="btn mt-2"
                type="button"
                onClick={() =>
                  void run(
                    async () => {
                      const token = await apiRequest<{ access_token: string; refresh_token: string }>("/api/v1/auth/bootstrap", {
                        method: "POST",
                        body: JSON.stringify(bootstrapForm),
                      });
                      persistAuth({ ...authState, mode: "bearer", accessToken: token.access_token });
                    },
                    "Bootstrap complete, bearer token saved",
                  )
                }
              >
                Bootstrap
              </button>
            </div>

            <div>
              <p className="label">Login</p>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                <input className="input" value={loginForm.username} onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })} placeholder="username" />
                <input
                  className="input"
                  type="password"
                  value={loginForm.password}
                  onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                  placeholder="password"
                />
              </div>
              <button
                className="btn mt-2"
                type="button"
                onClick={() =>
                  void run(
                    async () => {
                      const token = await apiRequest<{ access_token: string }>("/api/v1/auth/login", {
                        method: "POST",
                        body: JSON.stringify(loginForm),
                      });
                      persistAuth({ ...authState, mode: "bearer", accessToken: token.access_token });
                    },
                    "Login success, bearer token saved",
                  )
                }
              >
                Login
              </button>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="API Keys">
          <div className="space-y-2">
            <input className="input" placeholder="key name" value={apiKeyForm.name} onChange={(e) => setApiKeyForm({ ...apiKeyForm, name: e.target.value })} />
            <input
              className="input"
              placeholder="scopes comma separated"
              value={apiKeyForm.scopes}
              onChange={(e) => setApiKeyForm({ ...apiKeyForm, scopes: e.target.value })}
            />
            <button
              className="btn"
              type="button"
              onClick={() =>
                void run(
                  async () => {
                    const created = await apiRequest<{ id: string; name: string; key: string; key_prefix: string; scopes: string[] }>(
                      "/api/v1/auth/api-keys",
                      {
                        method: "POST",
                        body: JSON.stringify({
                          name: apiKeyForm.name,
                          scopes: apiKeyForm.scopes
                            .split(",")
                            .map((item) => item.trim())
                            .filter(Boolean),
                        }),
                      },
                    );
                    setNewApiKey(created);
                  },
                  "API key created",
                )
              }
            >
              Create API Key
            </button>
            {newApiKey ? (
              <div className="rounded-lg border border-mint/60 bg-mint/20 p-3 text-sm">
                <p className="font-medium">Copy now (shown once)</p>
                <p className="font-mono text-xs break-all">{newApiKey.key}</p>
              </div>
            ) : null}

            <div className="space-y-1 pt-2">
              {apiKeys.map((key) => (
                <div key={key.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-black/10 px-3 py-2 text-xs">
                  <div>
                    <p className="font-medium">{key.name}</p>
                    <p className="text-black/55">{key.key_prefix} | {key.status} | {formatDate(key.created_at)}</p>
                  </div>
                  <SmallButton
                    tone="danger"
                    onClick={() =>
                      void run(async () => {
                        await apiRequest(`/api/v1/auth/api-keys/${key.id}/revoke`, { method: "POST" });
                      }, "API key revoked")
                    }
                  >
                    Revoke
                  </SmallButton>
                </div>
              ))}
            </div>
          </div>
        </Card>

        <Card title="Webhooks">
          <div className="space-y-2">
            <input className="input" placeholder="name" value={webhookForm.name} onChange={(e) => setWebhookForm({ ...webhookForm, name: e.target.value })} />
            <input
              className="input"
              placeholder="target_url"
              value={webhookForm.target_url}
              onChange={(e) => setWebhookForm({ ...webhookForm, target_url: e.target.value })}
            />
            <input className="input" placeholder="secret" value={webhookForm.secret} onChange={(e) => setWebhookForm({ ...webhookForm, secret: e.target.value })} />
            <input
              className="input"
              placeholder="events comma separated"
              value={webhookForm.events}
              onChange={(e) => setWebhookForm({ ...webhookForm, events: e.target.value })}
            />
            <div className="flex gap-2">
              <button
                className="btn"
                type="button"
                onClick={() =>
                  void run(
                    async () => {
                      await apiRequest("/api/v1/webhooks/endpoints", {
                        method: "POST",
                        body: JSON.stringify({
                          name: webhookForm.name,
                          target_url: webhookForm.target_url,
                          secret: webhookForm.secret,
                          events: webhookForm.events
                            .split(",")
                            .map((item) => item.trim())
                            .filter(Boolean),
                        }),
                      });
                      setWebhookForm({ name: "", target_url: "", secret: "", events: "user.created,order.paid,node.offline" });
                    },
                    "Webhook endpoint created",
                  )
                }
              >
                Add Endpoint
              </button>
              <button
                className="btn-secondary"
                type="button"
                onClick={() =>
                  void run(async () => {
                    await apiRequest("/api/v1/webhooks/process?limit=100", { method: "POST" });
                  }, "Webhook queue processed")
                }
              >
                Process Queue
              </button>
            </div>

            <div className="space-y-1 pt-2">
              {webhookEndpoints.map((ep) => (
                <div key={ep.id} className="rounded-lg border border-black/10 px-3 py-2 text-xs">
                  <p className="font-medium">{ep.name}</p>
                  <p className="text-black/55 break-all">{ep.target_url}</p>
                  <p className="text-black/55">events: {ep.events.join(", ") || "*"}</p>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Recent Webhook Deliveries">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Status</th>
                  <th>Attempts</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {webhookDeliveries.slice(0, 20).map((delivery) => (
                  <tr key={delivery.id}>
                    <td>{delivery.event}</td>
                    <td>{delivery.status}</td>
                    <td>{delivery.attempts}</td>
                    <td>{formatDate(delivery.created_at)}</td>
                  </tr>
                ))}
                {webhookDeliveries.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-black/50">
                      No webhook deliveries yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Backups">
          <div className="space-y-2">
            <button
              className="btn"
              type="button"
              onClick={() =>
                void run(
                  async () => {
                    await apiRequest("/api/v1/backups/run", {
                      method: "POST",
                      body: JSON.stringify({ storage_type: "local" }),
                    });
                  },
                  "Backup created",
                )
              }
            >
              Run Backup
            </button>

            <div className="space-y-1">
              {backups.map((backup) => (
                <div key={backup.id} className="rounded-lg border border-black/10 px-3 py-2 text-xs">
                  <p className="font-medium">{backup.status}</p>
                  <p className="text-black/55 break-all">{backup.file_path}</p>
                  <p className="text-black/55">{backup.size_bytes} bytes | {formatDate(backup.created_at)}</p>
                </div>
              ))}
              {backups.length === 0 ? <p className="text-xs text-black/55">No backups yet.</p> : null}
            </div>
          </div>
        </Card>
      </div>
    </AdminShell>
  );
}
