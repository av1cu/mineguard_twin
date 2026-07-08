"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Activity } from "lucide-react";
import { useSimulationState } from "@/hooks/queries";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/simulation", label: "Simulation" },
  { href: "/analytics", label: "Analytics" },
  { href: "/events", label: "Events" },
  { href: "/equipment", label: "Equipment" },
  { href: "/routes", label: "Routes" },
  { href: "/settings", label: "Settings" },
];

export function TopBar() {
  const { data } = useSimulationState();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const statusText = useMemo(() => {
    if (!data) return "OFFLINE";
    return data.is_running ? "RUNNING" : "IDLE";
  }, [data]);

  return (
    <header className="border-b border-slate-800 bg-[#070a13]">
      <div className="flex items-center justify-between px-4 py-2.5">
        <div className="flex items-center gap-3">
          <button
            className="md:hidden text-slate-300"
            onClick={() => setMobileOpen((v) => !v)}
            aria-label="Toggle navigation"
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <Activity
            size={16}
            className={cn(
              data?.is_running ? "text-emerald-400 animate-pulse" : "text-slate-600"
            )}
          />
          <span className="text-xs font-mono text-slate-400">
            RUN ID: <span className="text-slate-200">{data?.run_id || "---"}</span>
          </span>
          <span className="text-xs font-mono text-slate-400">
            TICK: <span className="text-slate-200">{data?.current_tick ?? 0} / {data?.max_ticks ?? 0}</span>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "text-[10px] font-bold uppercase tracking-widest rounded px-2 py-1 border",
              data?.is_running
                ? "text-emerald-400 border-emerald-500 bg-emerald-500/10"
                : "text-slate-400 border-slate-600 bg-slate-500/10"
            )}
          >
            {statusText}
          </span>
        </div>
      </div>
      {mobileOpen && (
        <nav className="md:hidden border-t border-slate-800 bg-[#070a13] px-2 py-2">
          {NAV_ITEMS.map((item) => {
            const active =
              pathname === item.href || pathname?.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "block rounded px-3 py-2 text-sm font-medium",
                  active
                    ? "bg-sky-500/10 text-sky-300"
                    : "text-slate-400 hover:bg-slate-800/50"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
