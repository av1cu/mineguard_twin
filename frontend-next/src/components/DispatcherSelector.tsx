"use client";

import { memo } from "react";
import { Select } from "@/components/ui/select";
import { useMapStore } from "@/store/mapStore";

export const DISPATCHER_OPTIONS = ["NaiveDispatcher", "SmartDispatcher"];

function DispatcherSelectorImpl() {
  const dispatcher = useMapStore((s) => s.dispatcherSelection);
  const setDispatcher = useMapStore((s) => s.setDispatcherSelection);

  return (
    <Select
      value={dispatcher}
      onChange={(e) => setDispatcher(e.target.value)}
      className="w-full"
    >
      {DISPATCHER_OPTIONS.map((d) => (
        <option key={d} value={d}>
          {d}
        </option>
      ))}
    </Select>
  );
}

export const DispatcherSelector = memo(DispatcherSelectorImpl);
