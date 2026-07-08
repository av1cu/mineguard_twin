import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { EquipmentStatus, RouteStatus } from "@/types/api";

function statusClasses(status: string): string {
  const s = status.toLowerCase();
  if (s === "stopped") return "text-red-400 border-red-500 bg-red-500/10";
  if (s === "loading")
    return "text-amber-400 border-amber-500 bg-amber-500/10";
  if (s === "unload")
    return "text-stone-300 border-stone-400 bg-stone-500/10";
  if (s === "blocked") return "text-red-400 border-red-500 bg-red-500/10";
  if (s === "active" || s === "init")
    return "text-emerald-400 border-emerald-500 bg-emerald-500/10";
  // moving / running / anything else
  return "text-emerald-400 border-emerald-500 bg-emerald-500/10";
}

export function StatusBadge({
  status,
  className,
}: {
  status: EquipmentStatus | RouteStatus;
  className?: string;
}) {
  return (
    <Badge className={cn(statusClasses(String(status)), className)}>
      {status}
    </Badge>
  );
}
