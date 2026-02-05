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

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884d8", "#82ca9d"];

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
      router.push(`/leads?type=${encodeURIComponent(entry.name)}`);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Leads by Type</CardTitle>
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
              fill="#8884d8"
              dataKey="value"
              onClick={(_, index) => handleClick(chartData[index])}
              style={{ cursor: "pointer" }}
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
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
        <CardTitle>Leads by County</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis />
            <Tooltip />
            <Bar
              dataKey="value"
              fill="#0088FE"
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
        <CardTitle>Leads by Stage</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData} layout="vertical">
            <XAxis type="number" />
            <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={80} />
            <Tooltip />
            <Bar
              dataKey="value"
              fill="#00C49F"
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
