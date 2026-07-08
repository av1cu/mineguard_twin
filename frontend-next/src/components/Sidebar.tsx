"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Gauge,
  Settings2,
  BarChart3,
  ListTree,
  Truck,
  Route as RouteIcon,
  Sliders,
  Eye,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/simulation", label: "Simulation", icon: Settings2 },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/events", label: "Events", icon: ListTree },
  { href: "/equipment", label: "Equipment", icon: Truck },
  { href: "/routes", label: "Routes", icon: RouteIcon },
  { href: "/driver-cv", label: "Driver CV", icon: Eye },
  { href: "/settings", label: "Settings", icon: Sliders },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex md:w-56 md:flex-col border-r border-slate-800 bg-[#070a13]">
      <div className="px-4 py-4 border-b border-slate-800">
        <div className="text-sm font-bold uppercase tracking-widest text-sky-400">
          MineGuard
        </div>
        <div className="text-[10px] text-slate-500">Digital Twin Console</div>
      </div>
      <nav className="flex-1 overflow-y-auto py-2">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname?.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-l-2",
                active
                  ? "border-sky-500 bg-sky-500/10 text-sky-300"
                  : "border-transparent text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
              )}
            >
              <Icon size={16} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="px-4 py-3 border-t border-slate-800 text-[10px] text-slate-600">
        MineGuard Twin v1.0
      </div>
    </aside>
  );
}
