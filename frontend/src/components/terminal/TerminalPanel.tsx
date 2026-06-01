import type { ElementType, ReactNode } from "react";

interface TerminalPanelProps {
  as?: ElementType;
  eyebrow?: ReactNode;
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
  children?: ReactNode;
}

export default function TerminalPanel({
  as,
  eyebrow,
  title,
  description,
  actions,
  className = "",
  children,
}: TerminalPanelProps) {
  const Component = as ?? "section";
  return (
    <Component className={`terminal-panel p-4 ${className}`}>
      {(eyebrow || title || description || actions) && (
        <div className="mb-4 flex min-w-0 items-start justify-between gap-4">
          <div className="min-w-0">
            {eyebrow && <div className="terminal-micro-label">{eyebrow}</div>}
            {title && <h2 className="terminal-panel-title mt-1 text-[var(--theme-text)]">{title}</h2>}
            {description && <p className="mt-1 text-sm leading-relaxed text-[var(--theme-text-secondary)]">{description}</p>}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </div>
      )}
      {children}
    </Component>
  );
}

