import Link from "next/link";
import { SectionCard } from "../components/section-card";

const sections = [
  ["Dashboard", "/dashboard", "Live node health, revenue pulse, and migration progress"],
  ["Users", "/users", "Lifecycle control, limits, HWID policies, resets"],
  ["Squads", "/squads", "Policy-based endpoint groups: random, weighted, geo"],
  ["Nodes", "/nodes", "AWG2/Sing-box runtime revisions, apply and rollback"],
  ["Servers", "/servers", "Provider inventory, due dates, infra-cost reminders"],
  ["Protocols", "/protocols", "Versioned AWG2/TUIC/VLESS/Sing-box profiles"],
  ["Client Billing", "/client-billing", "Plans, orders, payments, renewals"],
  ["Infra Billing", "/infra-billing", "Cost aggregation by provider and currency"],
  ["Audit", "/audit", "Security-relevant timeline of all critical actions"],
  ["Settings", "/settings", "API keys, webhook routing, backup control"],
  ["Migration", "/migration", "Remnawave dry-run/apply/verify and token compatibility"],
] as const;

export default function Page() {
  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-12">
      <section className="rounded-3xl border border-black/15 bg-gradient-to-r from-mango/80 via-haze to-mint/60 px-6 py-8 shadow-lg">
        <p className="font-display text-xs uppercase tracking-[0.25em] text-black/70">Pepoapple Control Plane</p>
        <h1 className="mt-3 max-w-2xl font-display text-3xl leading-tight text-ink sm:text-5xl">
          Proxy Manager + Billing with zero-touch migration
        </h1>
        <p className="mt-3 max-w-3xl text-sm text-black/75 sm:text-base">
          Built for high-density squads, strict access control, and predictable operations across AWG2 and Sing-box.
        </p>
      </section>

      <section className="mt-7 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sections.map(([title, href, subtitle], index) => (
          <Link key={title} href={href}>
            <SectionCard title={title} subtitle={subtitle} index={index} />
          </Link>
        ))}
      </section>

      <section className="mt-8 rounded-3xl border border-black/10 bg-ink p-6 text-haze">
        <p className="font-display text-xs uppercase tracking-[0.2em] text-mint">API</p>
        <pre className="mt-2 overflow-x-auto rounded-xl bg-black/25 p-4 text-xs sm:text-sm">
{`curl -X POST http://localhost:8080/api/v1/auth/login \\
  -H 'Content-Type: application/json' \\
  -d '{"username":"root","password":"secret123"}'`}
        </pre>
      </section>
    </main>
  );
}
