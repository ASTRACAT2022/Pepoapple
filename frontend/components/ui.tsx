"use client";

import { ReactNode } from "react";

export function Card({ title, children, right }: { title: string; children: ReactNode; right?: ReactNode }) {
  return (
    <section className="rounded-2xl border border-black/10 bg-white/75 p-4 shadow-sm backdrop-blur">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="font-display text-lg text-ink">{title}</h2>
        {right}
      </div>
      {children}
    </section>
  );
}

export function Notice({ type, message }: { type: "error" | "success"; message: string | null }) {
  if (!message) {
    return null;
  }
  return (
    <p
      className={`rounded-lg px-3 py-2 text-sm ${
        type === "error" ? "border border-rust/40 bg-rust/10 text-rust" : "border border-mint/50 bg-mint/20 text-ink"
      }`}
    >
      {message}
    </p>
  );
}

export function SmallButton({
  children,
  onClick,
  disabled,
  tone = "default",
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  tone?: "default" | "danger";
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`rounded-lg px-3 py-2 text-xs font-medium transition ${
        tone === "danger"
          ? "bg-rust text-white hover:brightness-95 disabled:opacity-50"
          : "bg-ink text-haze hover:brightness-110 disabled:opacity-50"
      }`}
    >
      {children}
    </button>
  );
}
