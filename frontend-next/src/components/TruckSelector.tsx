"use client";

import { memo } from "react";
import { Select } from "@/components/ui/select";
import { useMapStore } from "@/store/mapStore";

export const TRUCK_OPTIONS = [
  "TRUCK-01",
  "TRUCK-02",
  "TRUCK-03",
  "TRUCK-04",
  "TRUCK-05",
];

function TruckSelectorImpl() {
  const truck = useMapStore((s) => s.truckSelection);
  const setTruck = useMapStore((s) => s.setTruckSelection);

  return (
    <Select
      value={truck}
      onChange={(e) => setTruck(e.target.value)}
      className="w-full"
    >
      {TRUCK_OPTIONS.map((t) => (
        <option key={t} value={t}>
          {t}
        </option>
      ))}
    </Select>
  );
}

export const TruckSelector = memo(TruckSelectorImpl);
