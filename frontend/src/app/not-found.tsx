import Link from "next/link";
import { AlertCircle } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-[#0A0C10] px-6 text-[#E6EDF3]">
      <div className="max-w-lg rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-8 text-center shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-xl">
        <AlertCircle className="mx-auto mb-5 text-amber-200" size={46} />
        <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-amber-200">Bloomberg Terminal Route Guard</p>
        <h1 className="mt-2 text-3xl font-black text-[#E6EDF3]">404 - Asset Not Found</h1>
        <p className="mt-3 text-sm leading-6 text-[#9BA7B4]">The requested market asset, route, or terminal panel is not registered in this workspace.</p>
        <Link
          href="/"
          className="mt-6 inline-flex rounded-2xl border border-amber-400/20 bg-amber-400/10 px-5 py-3 text-sm font-black text-amber-200 transition hover:border-cyan-300 hover:bg-amber-400/10"
        >
          Return to Terminal
        </Link>
      </div>
    </div>
  );
}
