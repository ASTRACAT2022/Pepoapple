export function SectionCard({
  title,
  subtitle,
  index,
}: {
  title: string;
  subtitle: string;
  index: number;
}) {
  return (
    <article
      className="animate-rise rounded-2xl border border-black/10 bg-white/70 p-5 shadow-sm backdrop-blur transition hover:-translate-y-1 hover:shadow-lg"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <p className="font-display text-sm uppercase tracking-[0.2em] text-rust">{title}</p>
      <p className="mt-2 text-sm text-black/70">{subtitle}</p>
    </article>
  );
}
