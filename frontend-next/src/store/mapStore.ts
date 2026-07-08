import { create } from "zustand";

export const DEFAULT_POLL_INTERVAL_MS = 500;

interface MapDisplaySettings {
  showGrid: boolean;
  showPredictiveLines: boolean;
  showLabels: boolean;
}

interface MapState {
  selectedEquipmentId: string | null;
  setSelectedEquipmentId: (id: string | null) => void;
  toggleSelectedEquipmentId: (id: string) => void;

  zoom: number;
  setZoom: (zoom: number) => void;

  panX: number;
  panY: number;
  setPan: (x: number, y: number) => void;
  resetView: () => void;

  displaySettings: MapDisplaySettings;
  toggleDisplaySetting: (key: keyof MapDisplaySettings) => void;

  dispatcherSelection: string;
  setDispatcherSelection: (dispatcher: string) => void;

  speedSelection: number;
  setSpeedSelection: (speed: number) => void;

  truckSelection: string;
  setTruckSelection: (truck: string) => void;
}

export const useMapStore = create<MapState>((set) => ({
  selectedEquipmentId: null,
  setSelectedEquipmentId: (id) => set({ selectedEquipmentId: id }),
  toggleSelectedEquipmentId: (id) =>
    set((state) => ({
      selectedEquipmentId: state.selectedEquipmentId === id ? null : id,
    })),

  zoom: 1.0,
  setZoom: (zoom) => set({ zoom: Math.max(0.4, Math.min(zoom, 5.0)) }),

  panX: 0,
  panY: 0,
  setPan: (x, y) => set({ panX: x, panY: y }),
  resetView: () => set({ panX: 0, panY: 0, zoom: 1.0 }),

  displaySettings: {
    showGrid: true,
    showPredictiveLines: true,
    showLabels: true,
  },
  toggleDisplaySetting: (key) =>
    set((state) => ({
      displaySettings: {
        ...state.displaySettings,
        [key]: !state.displaySettings[key],
      },
    })),

  dispatcherSelection: "NaiveDispatcher",
  setDispatcherSelection: (dispatcher) =>
    set({ dispatcherSelection: dispatcher }),

  speedSelection: 1.0,
  setSpeedSelection: (speed) => set({ speedSelection: speed }),

  truckSelection: "TRUCK-04",
  setTruckSelection: (truck) => set({ truckSelection: truck }),
}));
