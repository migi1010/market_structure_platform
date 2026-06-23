import Link from "next/link";
import { AlertCircle } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-[var(--theme-bg)] px-6 text-[var(--theme-text)]">
      <div className="terminal-panel max-w-lg p-8 text-center">
        <AlertCircle className="mx-auto mb-5 text-amber-200" size={46} />
        <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-warning)]">Terminal Route Guard</p>
        <h1 className="mt-2 text-3xl font-semibold text-[var(--theme-text)]">404 - Asset Not Found</h1>
        <p className="mt-3 text-sm leading-6 text-[var(--theme-muted)]">The requested market asset, route, or terminal panel is not registered in this workspace.</p>
        <Link
          href="/"
          className="mt-6 inline-flex rounded-[6px] border border-[var(--theme-divider)] px-5 py-3 text-sm font-semibold text-[var(--theme-warning)] transition hover:border-[var(--theme-hover-edge)] hover:bg-[rgba(255,255,255,0.035)]"
        >
          Return to Terminal
        </Link>
      </div>
    </div>
  );
}
