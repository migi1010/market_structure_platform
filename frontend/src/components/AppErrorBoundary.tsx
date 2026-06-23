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
      <div className="flex min-h-screen w-full items-center justify-center bg-[var(--theme-bg)] px-6 text-[var(--theme-text)]">
        <div className="terminal-panel max-w-lg p-8 text-center">
          <AlertTriangle className="mx-auto mb-5 text-rose-400" size={44} />
          <p className="text-[11px] font-semibold uppercase tracking-wide text-rose-300">System Failure</p>
          <h1 className="mt-2 text-2xl font-semibold text-[var(--theme-text)]">Quant Engine Crash Detected</h1>
          <p className="mt-3 text-sm leading-6 text-[var(--theme-muted)]">The client terminal isolated a runtime fault before it could corrupt the workspace state.</p>
          <button
            onClick={() => this.setState({ error: null })}
            className="mt-6 rounded-[6px] border border-[var(--theme-divider)] px-5 py-3 text-sm font-semibold text-[var(--theme-warning)] transition hover:border-[var(--theme-hover-edge)] hover:bg-[rgba(255,255,255,0.035)]"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }
}
