"use client";

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
}

export function TypePieChart({ data }: TypeChartProps) {
  const chartData: ChartData[] = Object.entries(data).map(([name, value]) => ({
    name: name || "other",
    value,
  }));

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
                `${name} (${(percent * 100).toFixed(0)}%)`
              }
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function CountyBarChart({ data }: TypeChartProps) {
  const chartData: ChartData[] = Object.entries(data)
    .map(([name, value]) => ({ name: name || "Unknown", value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

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
            <Bar dataKey="value" fill="#0088FE" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
