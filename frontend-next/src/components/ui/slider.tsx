"use client";

import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type SliderProps = InputHTMLAttributes<HTMLInputElement>;

export const Slider = forwardRef<HTMLInputElement, SliderProps>(
  ({ className, ...props }, ref) => {
    return (
      <input
        ref={ref}
        type="range"
        className={cn(
          "h-1.5 w-full cursor-pointer appearance-none rounded-full bg-slate-700 accent-sky-500",
          className
        )}
        {...props}
      />
    );
  }
);
Slider.displayName = "Slider";
