"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";

interface AppErrorBoundaryProps {
  children: React.ReactNode;
}

interface AppErrorBoundaryState {
  error: Error | null;
}

export default class AppErrorBoundary extends React.Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  constructor(props: AppErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("Quant Engine Crash Detected", error, info);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-[#0A0C10] px-6 text-[#E6EDF3]">
        <div className="max-w-lg rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-8 text-center shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-xl">
          <AlertTriangle className="mx-auto mb-5 text-rose-400" size={44} />
          <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-rose-300">System Failure</p>
          <h1 className="mt-2 text-2xl font-black text-[#E6EDF3]">Quant Engine Crash Detected</h1>
          <p className="mt-3 text-sm leading-6 text-[#9BA7B4]">The client terminal isolated a runtime fault before it could corrupt the workspace state.</p>
          <button
            onClick={() => this.setState({ error: null })}
            className="mt-6 rounded-2xl border border-amber-400/20 bg-amber-400/10 px-5 py-3 text-sm font-black text-amber-200 transition hover:border-cyan-300 hover:bg-amber-400/10"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }
}
