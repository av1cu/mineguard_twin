"use client";

import { useState } from "react";
import { Bot, Send, ShieldAlert, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  useAgentChat,
  useBlockRoute,
  useResumeEquipment,
  useStopEquipment,
  useUnblockRoute,
} from "@/hooks/queries";
import type { ProposedAction } from "@/types/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  proposedActions?: ProposedAction[];
  appliedIndices?: number[];
}

function ProposedActionCard({
  action,
  applied,
  onApply,
  applying,
}: {
  action: ProposedAction;
  applied: boolean;
  onApply: () => void;
  applying: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-2 rounded border border-amber-700/50 bg-amber-950/30 px-2 py-1.5 text-[11px]">
      <div className="flex items-center gap-1.5 text-amber-300">
        <ShieldAlert size={12} />
        <span className="font-semibold">{action.label ?? action.type}</span>
        {action.reason && (
          <span className="text-slate-400"> — {action.reason}</span>
        )}
      </div>
      <Button
        size="sm"
        variant={applied ? "default" : "danger"}
        disabled={applied || applying}
        onClick={onApply}
      >
        {applied ? "Применено" : applying ? "..." : "Применить"}
      </Button>
    </div>
  );
}

export function AgentChatPanel() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Я AI-диспетчер цифрового двойника. Спросите меня, например: «Почему TRUCK-04 стоит?» или «Что будет, если заблокировать ROUTE-02 на смену?». Опасные действия я только предлагаю — применяете их вы.",
    },
  ]);

  const chat = useAgentChat();
  const blockRoute = useBlockRoute();
  const unblockRoute = useUnblockRoute();
  const stopEquipment = useStopEquipment();
  const resumeEquipment = useResumeEquipment();
  const [applyingKey, setApplyingKey] = useState<string | null>(null);

  const sessionId = "dispatcher-console";

  function send(message: string) {
    if (!message.trim() || chat.isPending) return;
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    chat.mutate(
      { message, session_id: sessionId },
      {
        onSuccess: (res) => {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: res.answer,
              proposedActions: res.proposed_actions,
              appliedIndices: [],
            },
          ]);
        },
        onError: (err) => {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `Ошибка агента: ${err instanceof Error ? err.message : String(err)}`,
            },
          ]);
        },
      }
    );
  }

  function applyAction(msgIndex: number, actionIndex: number, action: ProposedAction) {
    const key = `${msgIndex}-${actionIndex}`;
    setApplyingKey(key);
    const markApplied = () => {
      setMessages((prev) =>
        prev.map((m, i) =>
          i === msgIndex
            ? { ...m, appliedIndices: [...(m.appliedIndices ?? []), actionIndex] }
            : m
        )
      );
      setApplyingKey(null);
    };
    const onErr = () => setApplyingKey(null);

    switch (action.type) {
      case "block_route":
        if (action.route_id) {
          blockRoute.mutate(
            { routeId: action.route_id, reason: action.reason ?? "Заблокировано по рекомендации AI-агента" },
            { onSuccess: markApplied, onError: onErr }
          );
        }
        break;
      case "unblock_route":
        if (action.route_id) {
          unblockRoute.mutate(action.route_id, { onSuccess: markApplied, onError: onErr });
        }
        break;
      case "stop_equipment":
        if (action.equipment_id) {
          stopEquipment.mutate(action.equipment_id, { onSuccess: markApplied, onError: onErr });
        }
        break;
      case "resume_equipment":
      case "replace_driver":
        if (action.equipment_id) {
          resumeEquipment.mutate(action.equipment_id, { onSuccess: markApplied, onError: onErr });
        }
        break;
      default:
        setApplyingKey(null);
    }
  }

  return (
    <Card className="flex h-full flex-col">
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <Bot size={13} /> AI-диспетчер
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3 overflow-hidden p-3">
        <div className="flex-1 space-y-3 overflow-y-auto pr-1">
          {messages.map((m, i) => (
            <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
              <div
                className={
                  "inline-block max-w-[90%] rounded-lg px-3 py-2 text-[12px] leading-relaxed whitespace-pre-wrap " +
                  (m.role === "user"
                    ? "bg-sky-600/20 border border-sky-700/40 text-sky-100"
                    : "bg-slate-800/70 border border-slate-700 text-slate-200")
                }
              >
                {m.content}
              </div>
              {m.proposedActions && m.proposedActions.length > 0 && (
                <div className="mt-1.5 space-y-1">
                  {m.proposedActions.map((a, ai) => (
                    <ProposedActionCard
                      key={ai}
                      action={a}
                      applied={m.appliedIndices?.includes(ai) ?? false}
                      applying={applyingKey === `${i}-${ai}`}
                      onApply={() => applyAction(i, ai, a)}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
          {chat.isPending && (
            <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
              <Loader2 size={12} className="animate-spin" /> Агент анализирует данные...
            </div>
          )}
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <input
            className="flex-1 rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-100 outline-none focus:border-sky-600"
            placeholder="Спросите AI-диспетчера..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <Button type="submit" size="sm" variant="primary" disabled={chat.isPending}>
            <Send size={13} />
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
