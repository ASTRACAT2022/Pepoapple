"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useMemo } from "react";

import { getApiBaseUrl, loadAuthState } from "../lib/api";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/users", label: "Users" },
  { href: "/squads", label: "Squads" },
  { href: "/servers", label: "Servers" },
  { href: "/nodes", label: "Nodes" },
  { href: "/protocols", label: "Protocols" },
  { href: "/client-billing", label: "Client Billing" },
  { href: "/infra-billing", label: "Infra Billing" },
  { href: "/migration", label: "Migration" },
  { href: "/audit", label: "Audit" },
  { href: "/settings", label: "Settings" },
] as const;

export function AdminShell({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const pathname = usePathname();

  const authLabel = useMemo(() => {
    const auth = loadAuthState();
    if (auth.mode === "bearer") {
      return auth.accessToken ? "Bearer" : "Bearer (empty)";
    }
    if (auth.mode === "api_key") {
      return auth.apiKey ? "API key" : "API key (empty)";
    }
    return `Scopes: ${auth.scopes || "*"}`;
  }, [pathname]);

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-[1400px] gap-4 px-3 py-4 sm:px-5">
      <aside className="hidden w-64 shrink-0 rounded-3xl border border-black/10 bg-white/70 p-4 shadow-sm backdrop-blur lg:block">
        <Link href="/dashboard" className="block rounded-xl bg-ink px-4 py-3 font-display text-haze">
          Pepoapple Admin
        </Link>
        <nav className="mt-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`block rounded-lg px-3 py-2 text-sm transition ${
                  active ? "bg-mango text-ink" : "text-black/70 hover:bg-black/5"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <header className="rounded-3xl border border-black/10 bg-white/75 p-4 shadow-sm backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="font-display text-xs uppercase tracking-[0.18em] text-rust">Control Panel</p>
              <h1 className="mt-1 font-display text-2xl text-ink sm:text-3xl">{title}</h1>
              {subtitle ? <p className="mt-1 text-sm text-black/65">{subtitle}</p> : null}
            </div>
            <div className="flex flex-col items-end gap-2">
              <span className="rounded-lg border border-black/10 bg-black/5 px-3 py-1 text-xs text-black/70">{authLabel}</span>
              <span className="text-xs text-black/45">API: {getApiBaseUrl()}</span>
              {actions ? <div>{actions}</div> : null}
            </div>
          </div>
          <nav className="mt-3 flex gap-2 overflow-x-auto lg:hidden">
            {NAV_ITEMS.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs ${
                    active ? "bg-mango text-ink" : "bg-black/5 text-black/70"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>

        <main className="grid gap-4">{children}</main>
      </div>
    </div>
  );
}
