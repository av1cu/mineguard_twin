"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import {
  acceptRecommendation,
  blockRoute,
  getAgentShiftReport,
  getEquipment,
  getEvent,
  getEvents,
  getKpis,
  getPredictiveRisks,
  getRecommendations,
  getRoutes,
  getSimulationState,
  postAgentChat,
  postAgentWhatIf,
  resetSimulation,
  resumeEquipment,
  runScenario,
  setSimulationSpeed,
  startSimulation,
  stopEquipment,
  stopSimulation,
  unblockRoute,
  updateEventStatus,
} from "@/lib/api";
import type {
  AgentChatRequest,
  EquipmentStateResponse,
  EventResponse,
  KPIResponse,
  PredictiveRiskResponse,
  RecommendationResponse,
  RouteResponse,
  ScenarioRunRequest,
  SimulationStateResponse,
  WhatIfAgentRequest,
} from "@/types/api";

const POLL_INTERVAL_MS = 500;

export function useSimulationState(): UseQueryResult<SimulationStateResponse> {
  return useQuery({
    queryKey: ["simulation-state"],
    queryFn: getSimulationState,
    refetchInterval: POLL_INTERVAL_MS,
  });
}

export function useEvents(
  limit = 100,
  sourceModule?: string
): UseQueryResult<EventResponse[]> {
  return useQuery({
    queryKey: ["events", limit, sourceModule ?? null],
    queryFn: () => getEvents(limit, sourceModule),
    refetchInterval: POLL_INTERVAL_MS * 2,
  });
}

export function useEvent(eventId: string | null): UseQueryResult<EventResponse> {
  return useQuery({
    queryKey: ["event", eventId],
    queryFn: () => getEvent(eventId as string),
    enabled: Boolean(eventId),
  });
}

export function useEquipment(): UseQueryResult<EquipmentStateResponse[]> {
  return useQuery({
    queryKey: ["equipment"],
    queryFn: getEquipment,
    refetchInterval: POLL_INTERVAL_MS,
  });
}

export function useRoutes(): UseQueryResult<RouteResponse[]> {
  return useQuery({
    queryKey: ["routes"],
    queryFn: getRoutes,
    refetchInterval: POLL_INTERVAL_MS,
  });
}

export function useRecommendations(): UseQueryResult<RecommendationResponse[]> {
  return useQuery({
    queryKey: ["recommendations"],
    queryFn: getRecommendations,
    refetchInterval: POLL_INTERVAL_MS * 2,
  });
}

export function useKpis(): UseQueryResult<KPIResponse[]> {
  return useQuery({
    queryKey: ["kpis"],
    queryFn: getKpis,
    refetchInterval: POLL_INTERVAL_MS * 4,
  });
}

export function usePredictiveRisks(): UseQueryResult<PredictiveRiskResponse[]> {
  return useQuery({
    queryKey: ["predictive-risks"],
    queryFn: getPredictiveRisks,
    refetchInterval: POLL_INTERVAL_MS * 2,
  });
}

// --- Mutations ---

export function useStartSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      dispatcher,
      speed,
    }: {
      dispatcher: string;
      speed: number;
    }) => startSimulation(dispatcher, speed),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["simulation-state"] }),
  });
}

export function useStopSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: stopSimulation,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["simulation-state"] }),
  });
}

export function useResetSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: resetSimulation,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["simulation-state"] }),
  });
}

export function useSetSimulationSpeed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (speed: number) => setSimulationSpeed(speed),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["simulation-state"] }),
  });
}

export function useBlockRoute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      routeId,
      reason,
    }: {
      routeId: string;
      reason: string;
    }) => blockRoute(routeId, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routes"] }),
  });
}

export function useUnblockRoute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (routeId: string) => unblockRoute(routeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routes"] }),
  });
}

export function useAcceptRecommendation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => acceptRecommendation(id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["recommendations"] }),
  });
}

export function useUpdateEventStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      eventId,
      status,
    }: {
      eventId: string;
      status: string;
    }) => updateEventStatus(eventId, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["events"] }),
  });
}

export function useRunScenario() {
  return useMutation({
    mutationFn: (payload: ScenarioRunRequest) => runScenario(payload),
  });
}

// --- AI Agent (Decision Support System) ---

export function useAgentChat() {
  return useMutation({
    mutationFn: (payload: AgentChatRequest) => postAgentChat(payload),
  });
}

export function useAgentWhatIf() {
  return useMutation({
    mutationFn: (payload: WhatIfAgentRequest) => postAgentWhatIf(payload),
  });
}

export function useAgentShiftReport() {
  return useMutation({
    mutationFn: () => getAgentShiftReport(),
  });
}

export function useStopEquipment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (equipmentId: string) => stopEquipment(equipmentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipment"] }),
  });
}

export function useResumeEquipment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (equipmentId: string) => resumeEquipment(equipmentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipment"] }),
  });
}
