"use client";

import { memo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface KpiBarDatum {
  dispatcher_name: string;
  value: number;
}

const COLORS: Record<string, string> = {
  NaiveDispatcher: "#ef4444",
  SmartDispatcher: "#22c55e",
};

function colorFor(name: string): string {
  return COLORS[name] ?? "#38bdf8";
}

function KpiBarChartImpl({
  title,
  dataKeyLabel,
  data,
}: {
  title: string;
  dataKeyLabel: string;
  data: KpiBarDatum[];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="dispatcher_name" stroke="#94a3b8" fontSize={11} />
            <YAxis stroke="#94a3b8" fontSize={11} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0b0f19",
                border: "1px solid #1f2937",
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="value" name={dataKeyLabel} radius={[3, 3, 0, 0]}>
              {data.map((d) => (
                <Cell key={d.dispatcher_name} fill={colorFor(d.dispatcher_name)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export const KpiBarChart = memo(KpiBarChartImpl);
export { COLORS as KPI_DISPATCHER_COLORS };
