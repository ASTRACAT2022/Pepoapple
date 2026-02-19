"use client";

import { useCallback, useEffect, useState } from "react";

import { AdminShell } from "../../components/admin-shell";
import { Card, Notice, SmallButton } from "../../components/ui";
import { apiRequest, formatDate, safeJsonParse } from "../../lib/api";

type Protocol = {
  id: string;
  name: string;
  protocol_type: string;
  schema_json: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
};

export default function ProtocolsPage() {
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    protocol_type: "AWG2",
    schema_json: '{"type":"object","required":[]}',
  });

  const load = useCallback(async () => {
    setError(null);
    try {
      setProtocols(await apiRequest<Protocol[]>("/api/v1/protocols"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load protocols");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AdminShell
      title="Protocols"
      subtitle="Manage profile schemas for AWG2/TUIC/VLESS/Sing-box"
      actions={<SmallButton onClick={() => void load()}>Refresh</SmallButton>}
    >
      <Notice type="error" message={error} />
      <Notice type="success" message={success} />

      <Card title="Create Protocol Profile">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div>
            <label className="label">Name</label>
            <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label">Protocol</label>
            <select className="select" value={form.protocol_type} onChange={(e) => setForm({ ...form, protocol_type: e.target.value })}>
              <option value="AWG2">AWG2</option>
              <option value="TUIC">TUIC</option>
              <option value="VLESS">VLESS</option>
              <option value="Sing-box">Sing-box</option>
            </select>
          </div>
        </div>
        <div className="mt-3">
          <label className="label">Schema JSON</label>
          <textarea className="textarea" value={form.schema_json} onChange={(e) => setForm({ ...form, schema_json: e.target.value })} />
        </div>
        <button
          className="btn mt-3"
          type="button"
          disabled={!form.name.trim()}
          onClick={async () => {
            setError(null);
            setSuccess(null);
            try {
              await apiRequest("/api/v1/protocols", {
                method: "POST",
                body: JSON.stringify({
                  name: form.name,
                  protocol_type: form.protocol_type,
                  schema_json: safeJsonParse(form.schema_json, {}),
                }),
              });
              setSuccess("Protocol profile created");
              setForm({ name: "", protocol_type: "AWG2", schema_json: '{"type":"object","required":[]}' });
              await load();
            } catch (err) {
              setError(err instanceof Error ? err.message : "Failed to create protocol");
            }
          }}
        >
          Create Profile
        </button>
      </Card>

      <Card title="Protocol Profiles">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Active</th>
                <th>Created</th>
                <th>Schema</th>
              </tr>
            </thead>
            <tbody>
              {protocols.map((item) => (
                <tr key={item.id}>
                  <td>{item.name}</td>
                  <td>{item.protocol_type}</td>
                  <td>{item.is_active ? "yes" : "no"}</td>
                  <td>{formatDate(item.created_at)}</td>
                  <td>
                    <pre className="max-w-[420px] overflow-x-auto rounded-md bg-black/5 p-2 text-xs">{JSON.stringify(item.schema_json, null, 2)}</pre>
                  </td>
                </tr>
              ))}
              {protocols.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-black/50">
                    No protocol profiles yet.
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
