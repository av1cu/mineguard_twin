import { cn } from "@/lib/utils";

interface DriverAlertBannerProps {
  message: string;
  tone: "red" | "amber";
}

export function DriverAlertBanner({ message, tone }: DriverAlertBannerProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md border px-4 py-3 text-center text-sm font-bold uppercase tracking-wide",
        tone === "red"
          ? "border-red-500 bg-red-500/20 text-red-300"
          : "border-amber-500 bg-amber-500/20 text-amber-300"
      )}
    >
      {message}
    </div>
  );
}
