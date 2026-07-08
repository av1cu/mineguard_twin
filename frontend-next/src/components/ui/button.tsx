"use client";

import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "primary" | "danger" | "ghost" | "outline";
type Size = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const variantClasses: Record<Variant, string> = {
  default:
    "bg-slate-800 border border-slate-700 text-slate-100 hover:bg-slate-700",
  primary:
    "bg-sky-600 border border-sky-700 text-white hover:bg-sky-500",
  danger: "bg-red-600 border border-red-700 text-white hover:bg-red-500",
  ghost:
    "bg-transparent border border-transparent text-slate-300 hover:bg-slate-800",
  outline:
    "bg-transparent border border-slate-600 text-slate-200 hover:bg-slate-800",
};

const sizeClasses: Record<Size, string> = {
  sm: "text-xs px-2 py-1",
  md: "text-sm px-3 py-1.5",
  lg: "text-base px-4 py-2",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "md", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-1.5 rounded-md font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50",
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
