"use client";

import { useRouter } from "next/navigation";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS = [
  "hsl(226, 70%, 60%)",
  "hsl(173, 58%, 45%)",
  "hsl(262, 60%, 58%)",
  "hsl(43, 74%, 56%)",
  "hsl(340, 75%, 55%)",
  "hsl(200, 70%, 55%)",
];

const tooltipStyle = {
  backgroundColor: "hsl(224, 47%, 12%)",
  border: "1px solid hsl(223, 30%, 20%)",
  borderRadius: "8px",
  fontSize: "12px",
  color: "hsl(213, 31%, 91%)",
  boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
};

interface ChartData {
  name: string;
  value: number;
}

interface TypeChartProps {
  data: Record<string, number>;
  onSegmentClick?: (filterKey: string, filterValue: string) => void;
}

export function TypePieChart({ data, onSegmentClick }: TypeChartProps) {
  const router = useRouter();
  const chartData: ChartData[] = Object.entries(data).map(([name, value]) => ({
    name: name || "other",
    value,
  }));

  const handleClick = (entry: ChartData) => {
    if (onSegmentClick) {
      onSegmentClick("type", entry.name);
    } else {
      router.push(`/leads?q=${encodeURIComponent(entry.name)}`);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Leads by Type
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) =>
                `${name} (${((percent ?? 0) * 100).toFixed(0)}%)`
              }
              outerRadius={80}
              innerRadius={40}
              fill="#8884d8"
              dataKey="value"
              onClick={(_, index) => handleClick(chartData[index])}
              style={{ cursor: "pointer" }}
              strokeWidth={0}
            >
              {chartData.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[index % COLORS.length]}
                  className="transition-opacity hover:opacity-80"
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={tooltipStyle}
              itemStyle={{ color: "hsl(213, 31%, 91%)" }}
            />
          </PieChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Click a segment to filter leads
        </p>
      </CardContent>
    </Card>
  );
}

export function CountyBarChart({ data, onSegmentClick }: TypeChartProps) {
  const router = useRouter();
  const chartData: ChartData[] = Object.entries(data)
    .map(([name, value]) => ({ name: name || "Unknown", value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  const handleClick = (entry: ChartData) => {
    if (onSegmentClick) {
      onSegmentClick("county", entry.name);
    } else {
      router.push(`/leads?county=${encodeURIComponent(entry.name)}`);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Leads by County
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData}>
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: "hsl(218, 11%, 55%)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "hsl(218, 11%, 55%)" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              itemStyle={{ color: "hsl(213, 31%, 91%)" }}
              cursor={{ fill: "hsl(226, 70%, 55%, 0.08)" }}
            />
            <Bar
              dataKey="value"
              fill="hsl(226, 70%, 60%)"
              radius={[6, 6, 0, 0]}
              onClick={(entry) => {
                if (entry.name) {
                  const value = Array.isArray(entry.value) ? entry.value[0] : entry.value;
                  handleClick({ name: entry.name, value });
                }
              }}
              style={{ cursor: "pointer" }}
            />
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Click a bar to filter leads
        </p>
      </CardContent>
    </Card>
  );
}

export function StageBarChart({ data, onSegmentClick }: TypeChartProps) {
  const router = useRouter();
  const chartData: ChartData[] = Object.entries(data).map(([name, value]) => ({
    name,
    value,
  }));

  const handleClick = (entry: ChartData) => {
    if (onSegmentClick) {
      onSegmentClick("stage", entry.name);
    } else {
      router.push(`/leads?stage=${encodeURIComponent(entry.name)}`);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Leads by Stage
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData} layout="vertical">
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: "hsl(218, 11%, 55%)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              dataKey="name"
              type="category"
              tick={{ fontSize: 11, fill: "hsl(218, 11%, 55%)" }}
              width={80}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              itemStyle={{ color: "hsl(213, 31%, 91%)" }}
              cursor={{ fill: "hsl(173, 58%, 45%, 0.08)" }}
            />
            <Bar
              dataKey="value"
              fill="hsl(173, 58%, 45%)"
              radius={[0, 6, 6, 0]}
              onClick={(entry) => {
                if (entry.name) {
                  const value = Array.isArray(entry.value) ? entry.value[0] : entry.value;
                  handleClick({ name: entry.name, value });
                }
              }}
              style={{ cursor: "pointer" }}
            />
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Click a bar to filter leads
        </p>
      </CardContent>
    </Card>
  );
}
