"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminShell } from "../../components/admin-shell";
import { Card, Notice, SmallButton } from "../../components/ui";
import { apiRequest, formatBytes, formatDate } from "../../lib/api";

type UserStatus = "active" | "blocked" | "expired" | "deleted";

type UserItem = {
  id: string;
  uuid: string;
  vless_id: string;
  short_id: string;
  status: UserStatus;
  traffic_limit_bytes: number;
  traffic_used_bytes: number;
  expires_at: string | null;
  max_devices: number;
  hwid_policy: string;
  strict_bind: boolean;
  device_eviction_policy: string;
  squad_id: string | null;
  reseller_id: string | null;
  subscription_token: string;
};

type UserList = {
  items: UserItem[];
  total: number;
};

type SquadItem = { id: string; name: string };
type DeviceItem = { id: string; device_hash: string; is_active: boolean; first_seen_at: string; last_seen_at: string };

function randomUuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = Math.random() * 16;
    const v = c === "x" ? r : (r % 4) + 8;
    return Math.floor(v).toString(16);
  });
}

export default function UsersPage() {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [total, setTotal] = useState(0);
  const [squads, setSquads] = useState<SquadItem[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [devices, setDevices] = useState<DeviceItem[]>([]);
  const [subscriptionLinks, setSubscriptionLinks] = useState<Record<string, string>>({});

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [createForm, setCreateForm] = useState({
    uuid: randomUuid(),
    vless_id: randomUuid(),
    short_id: Math.random().toString(16).slice(2, 10),
    subscription_token: `sub-${Math.random().toString(36).slice(2, 10)}`,
    traffic_limit_bytes: "0",
    max_devices: "3",
    strict_bind: false,
    device_eviction_policy: "reject",
    squad_id: "",
  });

  const [limitsForm, setLimitsForm] = useState({ traffic_limit_bytes: "0", max_devices: "1" });
  const [assignSquadId, setAssignSquadId] = useState("");

  const selectedUser = useMemo(() => users.find((item) => item.id === selectedUserId) ?? null, [users, selectedUserId]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [usersData, squadsData] = await Promise.all([
        apiRequest<UserList>("/api/v1/users?limit=200&offset=0&sort_by=created_at&sort_order=desc"),
        apiRequest<SquadItem[]>("/api/v1/squads"),
      ]);
      setUsers(usersData.items);
      setTotal(usersData.total);
      setSquads(squadsData);
      if (!selectedUserId && usersData.items.length > 0) {
        setSelectedUserId(usersData.items[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, [selectedUserId]);

  const loadDevices = useCallback(async (userId: string) => {
    try {
      const data = await apiRequest<DeviceItem[]>(`/api/v1/users/${userId}/devices`);
      setDevices(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load devices");
    }
  }, []);

  const loadSubscriptionLinks = useCallback(async (identifier: string) => {
    try {
      setSubscriptionLinks(await apiRequest<Record<string, string>>(`/api/v1/subscriptions/${identifier}/links`));
    } catch {
      setSubscriptionLinks({});
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (selectedUserId) {
      setDevices([]);
      void loadDevices(selectedUserId);
      const user = users.find((item) => item.id === selectedUserId);
      if (user) {
        setLimitsForm({
          traffic_limit_bytes: String(user.traffic_limit_bytes),
          max_devices: String(user.max_devices),
        });
        setAssignSquadId(user.squad_id ?? "");
        void loadSubscriptionLinks(user.subscription_token);
      }
    }
  }, [selectedUserId, users, loadDevices, loadSubscriptionLinks]);

  async function runAction(action: () => Promise<void>, successMessage: string) {
    setError(null);
    setSuccess(null);
    try {
      await action();
      setSuccess(successMessage);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    }
  }

  async function createUser() {
    await runAction(async () => {
      await apiRequest<UserItem>("/api/v1/users", {
        method: "POST",
        body: JSON.stringify({
          uuid: createForm.uuid,
          vless_id: createForm.vless_id,
          short_id: createForm.short_id,
          squad_id: createForm.squad_id || null,
          traffic_limit_bytes: Number(createForm.traffic_limit_bytes) || 0,
          max_devices: Number(createForm.max_devices) || 1,
          hwid_policy: "hash",
          strict_bind: createForm.strict_bind,
          device_eviction_policy: createForm.device_eviction_policy,
          subscription_token: createForm.subscription_token,
          external_identities: {},
        }),
      });
      setCreateForm({
        uuid: randomUuid(),
        vless_id: randomUuid(),
        short_id: Math.random().toString(16).slice(2, 10),
        subscription_token: `sub-${Math.random().toString(36).slice(2, 10)}`,
        traffic_limit_bytes: "0",
        max_devices: "3",
        strict_bind: false,
        device_eviction_policy: "reject",
        squad_id: "",
      });
    }, "User created");
  }

  return (
    <AdminShell
      title="Users"
      subtitle="Create and operate subscriptions, limits, keys and devices"
      actions={<SmallButton onClick={() => void load()}>{loading ? "Loading..." : "Refresh"}</SmallButton>}
    >
      <Notice type="error" message={error} />
      <Notice type="success" message={success} />

      <Card title="Create User">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div>
            <label className="label">UUID</label>
            <input className="input" value={createForm.uuid} onChange={(e) => setCreateForm({ ...createForm, uuid: e.target.value })} />
          </div>
          <div>
            <label className="label">VLESS ID</label>
            <input className="input" value={createForm.vless_id} onChange={(e) => setCreateForm({ ...createForm, vless_id: e.target.value })} />
          </div>
          <div>
            <label className="label">Short ID</label>
            <input className="input" value={createForm.short_id} onChange={(e) => setCreateForm({ ...createForm, short_id: e.target.value })} />
          </div>
          <div>
            <label className="label">Subscription Token</label>
            <input
              className="input"
              value={createForm.subscription_token}
              onChange={(e) => setCreateForm({ ...createForm, subscription_token: e.target.value })}
            />
          </div>
          <div>
            <label className="label">Traffic Limit (bytes)</label>
            <input
              className="input"
              value={createForm.traffic_limit_bytes}
              onChange={(e) => setCreateForm({ ...createForm, traffic_limit_bytes: e.target.value })}
            />
          </div>
          <div>
            <label className="label">Max Devices</label>
            <input className="input" value={createForm.max_devices} onChange={(e) => setCreateForm({ ...createForm, max_devices: e.target.value })} />
          </div>
          <div>
            <label className="label">Device Eviction</label>
            <select
              className="select"
              value={createForm.device_eviction_policy}
              onChange={(e) => setCreateForm({ ...createForm, device_eviction_policy: e.target.value })}
            >
              <option value="reject">reject</option>
              <option value="evict_oldest">evict_oldest</option>
            </select>
          </div>
          <div>
            <label className="label">Squad</label>
            <select className="select" value={createForm.squad_id} onChange={(e) => setCreateForm({ ...createForm, squad_id: e.target.value })}>
              <option value="">-</option>
              {squads.map((squad) => (
                <option value={squad.id} key={squad.id}>
                  {squad.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <label className="mt-3 flex items-center gap-2 text-sm text-black/70">
          <input
            type="checkbox"
            checked={createForm.strict_bind}
            onChange={(e) => setCreateForm({ ...createForm, strict_bind: e.target.checked })}
          />
          strict_bind
        </label>
        <div className="mt-3 flex gap-2">
          <button className="btn" type="button" onClick={() => void createUser()}>
            Create User
          </button>
          <button
            className="btn-secondary"
            type="button"
            onClick={() =>
              setCreateForm({
                ...createForm,
                uuid: randomUuid(),
                vless_id: randomUuid(),
                short_id: Math.random().toString(16).slice(2, 10),
                subscription_token: `sub-${Math.random().toString(36).slice(2, 10)}`,
              })
            }
          >
            Regenerate IDs
          </button>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.2fr_1fr]">
        <Card title={`Users (${total})`}>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Status</th>
                  <th>Traffic</th>
                  <th>Expires</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr
                    key={user.id}
                    className={`cursor-pointer ${user.id === selectedUserId ? "bg-mango/20" : "hover:bg-black/5"}`}
                    onClick={() => setSelectedUserId(user.id)}
                  >
                    <td>
                      <div className="font-mono text-xs">{user.id.slice(0, 10)}</div>
                      <div className="text-xs text-black/55">{user.short_id}</div>
                    </td>
                    <td>{user.status}</td>
                    <td>
                      {formatBytes(user.traffic_used_bytes)} / {formatBytes(user.traffic_limit_bytes)}
                    </td>
                    <td>{formatDate(user.expires_at)}</td>
                  </tr>
                ))}
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-black/50">
                      No users created yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Selected User Actions">
          {!selectedUser ? (
            <p className="text-sm text-black/55">Pick a user from table.</p>
          ) : (
            <div className="space-y-3 text-sm">
              <div className="rounded-lg border border-black/10 bg-black/5 p-3">
                <p className="font-mono text-xs">{selectedUser.id}</p>
                <p className="mt-1">Status: {selectedUser.status}</p>
                <p>UUID: {selectedUser.uuid}</p>
                <p>Squad: {selectedUser.squad_id ?? "-"}</p>
              </div>

              <div>
                <label className="label">Update Limits</label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    className="input"
                    value={limitsForm.traffic_limit_bytes}
                    onChange={(e) => setLimitsForm({ ...limitsForm, traffic_limit_bytes: e.target.value })}
                    placeholder="traffic bytes"
                  />
                  <input
                    className="input"
                    value={limitsForm.max_devices}
                    onChange={(e) => setLimitsForm({ ...limitsForm, max_devices: e.target.value })}
                    placeholder="max devices"
                  />
                </div>
                <button
                  className="btn mt-2"
                  type="button"
                  onClick={() =>
                    void runAction(
                      async () => {
                        await apiRequest(`/api/v1/users/${selectedUser.id}/limits`, {
                          method: "PATCH",
                          body: JSON.stringify({
                            traffic_limit_bytes: Number(limitsForm.traffic_limit_bytes) || 0,
                            max_devices: Number(limitsForm.max_devices) || 1,
                          }),
                        });
                      },
                      "Limits updated",
                    )
                  }
                >
                  Save Limits
                </button>
              </div>

              <div>
                <label className="label">Assign Squad</label>
                <div className="flex gap-2">
                  <select className="select" value={assignSquadId} onChange={(e) => setAssignSquadId(e.target.value)}>
                    <option value="">-</option>
                    {squads.map((squad) => (
                      <option key={squad.id} value={squad.id}>
                        {squad.name}
                      </option>
                    ))}
                  </select>
                  <button
                    className="btn"
                    type="button"
                    onClick={() =>
                      void runAction(
                        async () => {
                          await apiRequest(`/api/v1/users/${selectedUser.id}/assign-squad?squad_id=${encodeURIComponent(assignSquadId)}`, {
                            method: "POST",
                          });
                        },
                        "Squad assigned",
                      )
                    }
                    disabled={!assignSquadId}
                  >
                    Assign
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <SmallButton
                  onClick={() =>
                    void runAction(async () => {
                      await apiRequest(`/api/v1/users/${selectedUser.id}/block`, { method: "PATCH" });
                    }, "User blocked")
                  }
                >
                  Block
                </SmallButton>
                <SmallButton
                  onClick={() =>
                    void runAction(async () => {
                      await apiRequest(`/api/v1/users/${selectedUser.id}/reset-subscription`, { method: "POST" });
                    }, "Subscription reset")
                  }
                >
                  Reset Sub
                </SmallButton>
                <SmallButton
                  onClick={() =>
                    void runAction(async () => {
                      await apiRequest(`/api/v1/users/${selectedUser.id}/rotate-keys`, { method: "POST" });
                    }, "Keys rotated")
                  }
                >
                  Rotate Keys
                </SmallButton>
                <SmallButton
                  onClick={() =>
                    void runAction(async () => {
                      await apiRequest(`/api/v1/users/${selectedUser.id}/devices/reset`, { method: "POST" });
                    }, "Devices reset")
                  }
                >
                  Reset Devices
                </SmallButton>
                <SmallButton
                  tone="danger"
                  onClick={() =>
                    void runAction(async () => {
                      await apiRequest(`/api/v1/users/${selectedUser.id}`, { method: "DELETE" });
                      setSelectedUserId("");
                    }, "User soft deleted")
                  }
                >
                  Soft Delete
                </SmallButton>
              </div>

              <div>
                <p className="label">Devices</p>
                <div className="space-y-1">
                  {devices.map((device) => (
                    <div key={device.id} className="rounded-lg border border-black/10 px-3 py-2 text-xs">
                      <div className="font-mono">{device.device_hash}</div>
                      <div className="text-black/55">
                        {device.is_active ? "active" : "inactive"} | seen {formatDate(device.last_seen_at)}
                      </div>
                    </div>
                  ))}
                  {devices.length === 0 ? <p className="text-xs text-black/55">No registered devices.</p> : null}
                </div>
              </div>

              <div>
                <p className="label">Subscription Links</p>
                <div className="space-y-1">
                  {Object.entries(subscriptionLinks).map(([name, url]) => (
                    <div key={name} className="rounded-lg border border-black/10 px-3 py-2 text-xs">
                      <p className="font-medium">{name}</p>
                      <p className="font-mono break-all text-black/60">{url}</p>
                    </div>
                  ))}
                  {Object.keys(subscriptionLinks).length === 0 ? (
                    <p className="text-xs text-black/55">No links generated.</p>
                  ) : null}
                  {selectedUser ? (
                    <p className="text-xs text-black/55">
                      Public page (separate service): <span className="font-mono">http://localhost:3010/{selectedUser.short_id}</span>
                    </p>
                  ) : null}
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </AdminShell>
  );
}
