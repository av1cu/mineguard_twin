"use client";

import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Tooltip({
  content,
  children,
  className,
}: {
  content: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <span
      className="relative inline-block"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && (
        <span
          className={cn(
            "absolute z-50 left-1/2 -translate-x-1/2 bottom-full mb-1 whitespace-nowrap rounded border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-100 shadow-lg",
            className
          )}
        >
          {content}
        </span>
      )}
    </span>
  );
}
