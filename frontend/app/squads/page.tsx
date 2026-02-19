"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminShell } from "../../components/admin-shell";
import { Card, Notice, SmallButton } from "../../components/ui";
import { apiRequest, formatDate } from "../../lib/api";

type Squad = {
  id: string;
  name: string;
  description: string;
  selection_policy: string;
  fallback_policy: string;
  allowed_protocols: string[];
};

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

export default function SquadsPage() {
  const [squads, setSquads] = useState<Squad[]>([]);
  const [servers, setServers] = useState<Server[]>([]);
  const [selectedSquadId, setSelectedSquadId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [squadForm, setSquadForm] = useState({
    name: "",
    description: "",
    selection_policy: "round-robin",
    fallback_policy: "none",
    allowed_protocols: "AWG2,Sing-box",
  });

  const [serverForm, setServerForm] = useState({
    host: "",
    ip: "",
    provider: "",
    region: "",
    squad_id: "",
    price: "0",
    currency: "USD",
  });

  const filteredServers = useMemo(() => {
    if (!selectedSquadId) {
      return servers;
    }
    return servers.filter((server) => server.squad_id === selectedSquadId);
  }, [servers, selectedSquadId]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [squadData, serverData] = await Promise.all([
        apiRequest<Squad[]>("/api/v1/squads"),
        apiRequest<Server[]>("/api/v1/servers"),
      ]);
      setSquads(squadData);
      setServers(serverData);
      if (!selectedSquadId && squadData.length) {
        setSelectedSquadId(squadData[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load squads");
    }
  }, [selectedSquadId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function createSquad() {
    setError(null);
    setSuccess(null);
    try {
      await apiRequest<Squad>("/api/v1/squads", {
        method: "POST",
        body: JSON.stringify({
          name: squadForm.name,
          description: squadForm.description,
          selection_policy: squadForm.selection_policy,
          fallback_policy: squadForm.fallback_policy,
          allowed_protocols: squadForm.allowed_protocols
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      });
      setSquadForm({
        name: "",
        description: "",
        selection_policy: "round-robin",
        fallback_policy: "none",
        allowed_protocols: "AWG2,Sing-box",
      });
      setSuccess("Squad created");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create squad");
    }
  }

  async function createServer() {
    setError(null);
    setSuccess(null);
    try {
      await apiRequest<Server>("/api/v1/servers", {
        method: "POST",
        body: JSON.stringify({
          host: serverForm.host,
          ip: serverForm.ip,
          provider: serverForm.provider,
          region: serverForm.region,
          squad_id: serverForm.squad_id,
          price: Number(serverForm.price) || 0,
          currency: serverForm.currency,
        }),
      });
      setServerForm({
        host: "",
        ip: "",
        provider: "",
        region: "",
        squad_id: serverForm.squad_id,
        price: "0",
        currency: "USD",
      });
      setSuccess("Server created");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create server");
    }
  }

  return (
    <AdminShell
      title="Squads"
      subtitle="Build routing pools and attach servers"
      actions={<SmallButton onClick={() => void load()}>Refresh</SmallButton>}
    >
      <Notice type="error" message={error} />
      <Notice type="success" message={success} />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Create Squad">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className="label">Name</label>
              <input className="input" value={squadForm.name} onChange={(e) => setSquadForm({ ...squadForm, name: e.target.value })} />
            </div>
            <div>
              <label className="label">Selection Policy</label>
              <select
                className="select"
                value={squadForm.selection_policy}
                onChange={(e) => setSquadForm({ ...squadForm, selection_policy: e.target.value })}
              >
                <option value="round-robin">round-robin</option>
                <option value="random">random</option>
                <option value="weighted">weighted</option>
                <option value="geo">geo</option>
              </select>
            </div>
            <div>
              <label className="label">Fallback Policy</label>
              <input
                className="input"
                value={squadForm.fallback_policy}
                onChange={(e) => setSquadForm({ ...squadForm, fallback_policy: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Protocols (comma separated)</label>
              <input
                className="input"
                value={squadForm.allowed_protocols}
                onChange={(e) => setSquadForm({ ...squadForm, allowed_protocols: e.target.value })}
              />
            </div>
            <div className="md:col-span-2">
              <label className="label">Description</label>
              <input
                className="input"
                value={squadForm.description}
                onChange={(e) => setSquadForm({ ...squadForm, description: e.target.value })}
              />
            </div>
          </div>
          <button className="btn mt-3" type="button" onClick={() => void createSquad()} disabled={!squadForm.name.trim()}>
            Create Squad
          </button>
        </Card>

        <Card title="Create Server">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className="label">Host</label>
              <input className="input" value={serverForm.host} onChange={(e) => setServerForm({ ...serverForm, host: e.target.value })} />
            </div>
            <div>
              <label className="label">IP</label>
              <input className="input" value={serverForm.ip} onChange={(e) => setServerForm({ ...serverForm, ip: e.target.value })} />
            </div>
            <div>
              <label className="label">Provider</label>
              <input
                className="input"
                value={serverForm.provider}
                onChange={(e) => setServerForm({ ...serverForm, provider: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Region</label>
              <input className="input" value={serverForm.region} onChange={(e) => setServerForm({ ...serverForm, region: e.target.value })} />
            </div>
            <div>
              <label className="label">Squad</label>
              <select className="select" value={serverForm.squad_id} onChange={(e) => setServerForm({ ...serverForm, squad_id: e.target.value })}>
                <option value="">Select squad</option>
                {squads.map((squad) => (
                  <option key={squad.id} value={squad.id}>
                    {squad.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Price / Currency</label>
              <div className="grid grid-cols-[1fr_auto] gap-2">
                <input className="input" value={serverForm.price} onChange={(e) => setServerForm({ ...serverForm, price: e.target.value })} />
                <input
                  className="input w-24"
                  value={serverForm.currency}
                  onChange={(e) => setServerForm({ ...serverForm, currency: e.target.value.toUpperCase() })}
                />
              </div>
            </div>
          </div>
          <button className="btn mt-3" type="button" onClick={() => void createServer()} disabled={!serverForm.host || !serverForm.squad_id}>
            Create Server
          </button>
        </Card>
      </div>

      <Card title="Squad List">
        <div className="mb-3 flex gap-2 overflow-x-auto">
          <button
            className={`btn-secondary ${selectedSquadId === "" ? "ring-2 ring-mango" : ""}`}
            type="button"
            onClick={() => setSelectedSquadId("")}
          >
            All
          </button>
          {squads.map((squad) => (
            <button
              key={squad.id}
              className={`btn-secondary ${selectedSquadId === squad.id ? "ring-2 ring-mango" : ""}`}
              type="button"
              onClick={() => setSelectedSquadId(squad.id)}
            >
              {squad.name}
            </button>
          ))}
        </div>

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Host</th>
                <th>Squad</th>
                <th>Provider</th>
                <th>Price</th>
                <th>Status</th>
                <th>Next Due</th>
              </tr>
            </thead>
            <tbody>
              {filteredServers.map((server) => (
                <tr key={server.id}>
                  <td>
                    <div>{server.host}</div>
                    <div className="text-xs text-black/55">{server.ip}</div>
                  </td>
                  <td>{squads.find((item) => item.id === server.squad_id)?.name ?? server.squad_id.slice(0, 8)}</td>
                  <td>
                    {server.provider} / {server.region}
                  </td>
                  <td>
                    {server.price} {server.currency}
                  </td>
                  <td>{server.status}</td>
                  <td>{formatDate(server.next_due_at)}</td>
                </tr>
              ))}
              {filteredServers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-black/50">
                    No servers in this scope.
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
