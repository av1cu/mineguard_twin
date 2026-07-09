"use client";

import { useState } from "react";
import { FileText, FlaskConical, Loader2, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AgentChatPanel } from "@/components/AgentChatPanel";
import { useAgentShiftReport, useAgentWhatIf } from "@/hooks/queries";

export default function AgentPage() {
  const [whatIfQuestion, setWhatIfQuestion] = useState(
    "Что будет, если заблокировать ROUTE-02 на всю смену?"
  );
  const whatIf = useAgentWhatIf();
  const shiftReport = useAgentShiftReport();

  return (
    <div className="grid h-full grid-cols-1 gap-4 p-4 lg:grid-cols-[1fr_360px]">
      <div className="h-[calc(100vh-8rem)]">
        <AgentChatPanel />
      </div>

      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-lg font-bold text-sky-400">AI-диспетчер</h1>
          <p className="text-xs text-slate-400">
            Decision Support System поверх цифрового двойника: агент анализирует
            данные и предлагает действия. Опасные действия применяет только
            диспетчер, нажимая «Применить».
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5">
              <FlaskConical size={13} /> What-if сценарий
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <textarea
              className="w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100 outline-none focus:border-sky-600"
              rows={3}
              value={whatIfQuestion}
              onChange={(e) => setWhatIfQuestion(e.target.value)}
            />
            <Button
              size="sm"
              variant="primary"
              disabled={whatIf.isPending}
              onClick={() => whatIf.mutate({ question: whatIfQuestion, session_id: "whatif" })}
            >
              {whatIf.isPending ? (
                <>
                  <Loader2 size={12} className="animate-spin" /> Считаю...
                </>
              ) : (
                "Запустить анализ"
              )}
            </Button>
            {whatIf.data && (
              <div className="rounded border border-slate-700 bg-slate-800/60 p-2 text-[11px] leading-relaxed text-slate-200 whitespace-pre-wrap">
                {whatIf.data.answer}
              </div>
            )}
            {whatIf.isError && (
              <div className="text-[11px] text-red-400">
                Ошибка: {String(whatIf.error)}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5">
              <FileText size={13} /> Отчёт за смену
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button
              size="sm"
              variant="outline"
              disabled={shiftReport.isPending}
              onClick={() => shiftReport.mutate()}
            >
              {shiftReport.isPending ? (
                <>
                  <Loader2 size={12} className="animate-spin" /> Формирую...
                </>
              ) : (
                "Сформировать отчёт"
              )}
            </Button>
            {shiftReport.data && (
              <div className="max-h-64 overflow-y-auto rounded border border-slate-700 bg-slate-800/60 p-2 text-[11px] leading-relaxed text-slate-200 whitespace-pre-wrap">
                {shiftReport.data.report}
              </div>
            )}
            {shiftReport.isError && (
              <div className="text-[11px] text-red-400">
                Ошибка: {String(shiftReport.error)}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex items-start gap-1.5 rounded border border-slate-800 bg-slate-900/50 px-2.5 py-2 text-[10px] text-slate-500">
          <ShieldAlert size={12} className="mt-0.5 shrink-0" />
          <span>
            Рамки: агент не блокирует маршруты и не останавливает технику
            самостоятельно — только предлагает. Применение решения остаётся за
            диспетчером (ТЗ §16, Decision Support System).
          </span>
        </div>
      </div>
    </div>
  );
}
