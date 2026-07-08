"use client";

import dynamic from "next/dynamic";

const MineCanvasInner = dynamic(() => import("./MineCanvasInner"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-[#070a13] text-xs text-slate-500">
      Loading SCADA map...
    </div>
  ),
});

export function MineCanvas() {
  return <MineCanvasInner />;
}
