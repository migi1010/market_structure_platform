"use client";

import { useEffect, useMemo, useState } from "react";

export function useClientMounted(): boolean {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return mounted;
}

export function formatHydratedTime(date: Date, locale = "zh-TW"): string {
  return date.toLocaleTimeString(locale, { hour12: false });
}

export function useHydratedTime(options: { locale?: string; placeholder?: string; refreshMs?: number } = {}): string {
  const { locale = "zh-TW", placeholder = "--:--:--", refreshMs = 1000 } = options;
  const mounted = useClientMounted();
  const [date, setDate] = useState<Date | null>(null);

  useEffect(() => {
    if (!mounted) return;
    setDate(new Date());
    const timer = window.setInterval(() => setDate(new Date()), refreshMs);
    return () => window.clearInterval(timer);
  }, [mounted, refreshMs]);

  return useMemo(() => {
    if (!mounted || !date) return placeholder;
    return formatHydratedTime(date, locale);
  }, [date, locale, mounted, placeholder]);
}
