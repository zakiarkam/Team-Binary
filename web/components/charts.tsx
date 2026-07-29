"use client";

import {
  Area,
  AreaChart,
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

import { PLATFORM_COLOR, SEGMENT_COLOR } from "@/components/ui";

/** Recharts is the charting library named in Chapter 3.5 of the report. */

const AXIS = { fill: "#94a3b8", fontSize: 11 };
const TOOLTIP = {
  borderRadius: 12,
  border: "1px solid #e2e8f0",
  fontSize: 13,
  boxShadow: "0 8px 24px rgb(15 23 42 / 0.08)",
};

/**
 * Recharts types a tooltip value as `ValueType | undefined`, so a formatter
 * typed `(v: number)` does not satisfy it. Narrowing here keeps every chart's
 * formatter assignable without casting.
 */
const asPercent = (value: unknown) =>
  typeof value === "number" ? `${(value * 100).toFixed(1)}%` : String(value ?? "");

function Empty({ message }: { message: string }) {
  return (
    <div className="flex h-full items-center justify-center text-sm text-slate-400">
      {message}
    </div>
  );
}

export interface DailyPoint {
  day: string;
  visitors: number;
  events: number;
}

export function AudienceChart({ data }: { data: DailyPoint[] }) {
  const empty = !data?.length || data.every((d) => d.events === 0);
  return (
    <div className="h-64 w-full">
      {empty ? (
        <Empty message="No visitor activity yet — browse the demo site to populate this." />
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
            <defs>
              <linearGradient id="visitorsFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b5bdb" stopOpacity={0.32} />
                <stop offset="100%" stopColor="#3b5bdb" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="eventsFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.22} />
                <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
            <XAxis
              dataKey="day"
              tickFormatter={(d: string) => d.slice(5)}
              tick={AXIS}
              axisLine={{ stroke: "#e2e8f0" }}
              tickLine={false}
            />
            <YAxis allowDecimals={false} tick={AXIS} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP} />
            <Area type="monotone" dataKey="events" stroke="#0ea5e9" strokeWidth={2}
                  fill="url(#eventsFill)" name="Events" />
            <Area type="monotone" dataKey="visitors" stroke="#3b5bdb" strokeWidth={2.5}
                  fill="url(#visitorsFill)" name="Visitors" />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export function SegmentChart({
  data,
}: {
  data: { segment_name: string; visitors: number; cold_start?: number }[];
}) {
  return (
    <div className="h-64 w-full">
      {!data?.length ? (
        <Empty message="Not segmented yet — run segmentation to populate this." />
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical"
                    margin={{ top: 4, right: 16, bottom: 4, left: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" horizontal={false} />
            <XAxis type="number" allowDecimals={false} tick={AXIS} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="segment_name" width={110}
                   tick={AXIS} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP} />
            <Bar dataKey="visitors" name="Visitors" radius={[0, 6, 6, 0]} barSize={22}>
              {data.map((d) => (
                <Cell key={d.segment_name}
                      fill={SEGMENT_COLOR[d.segment_name] ?? "#3b5bdb"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export function FunnelChart({
  funnel,
}: {
  funnel: { sent: number; open: number; click: number; convert: number };
}) {
  const data = [
    { stage: "Sent", users: funnel.sent, fill: "#3b5bdb" },
    { stage: "Opened", users: funnel.open, fill: "#0ea5e9" },
    { stage: "Clicked", users: funnel.click, fill: "#f59e0b" },
    { stage: "Converted", users: funnel.convert, fill: "#16a34a" },
  ];
  return (
    <div className="h-64 w-full">
      {funnel.sent === 0 ? (
        <Empty message="No campaign sent yet." />
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
            <XAxis dataKey="stage" tick={AXIS} axisLine={{ stroke: "#e2e8f0" }} tickLine={false} />
            <YAxis allowDecimals={false} tick={AXIS} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP} />
            <Bar dataKey="users" name="Unique visitors" radius={[6, 6, 0, 0]} barSize={54}>
              {data.map((d) => <Cell key={d.stage} fill={d.fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

/**
 * The four attribution models side by side.
 *
 * Grouped rather than stacked on purpose: the point of the comparison is where
 * the models *disagree*, and a stacked chart hides exactly that.
 */
export function AttributionChart({
  models,
}: {
  models: Record<string, { platform: string; credit: number }[]>;
}) {
  const names = Object.keys(models ?? {});
  if (!names.length) return <Empty message="Not enough converting journeys yet." />;

  const platforms = Array.from(
    new Set(names.flatMap((m) => (models[m] ?? []).map((r) => r.platform))),
  );

  const data = platforms.map((platform) => {
    const row: Record<string, string | number> = { platform };
    for (const model of names) {
      row[model] = (models[model] ?? []).find((r) => r.platform === platform)?.credit ?? 0;
    }
    return row;
  });

  const colors: Record<string, string> = {
    first_touch: "#3b5bdb",
    last_touch: "#f59e0b",
    linear: "#16a34a",
    markov: "#8b5cf6",
  };

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
          <XAxis dataKey="platform" tick={AXIS} axisLine={{ stroke: "#e2e8f0" }} tickLine={false} />
          <YAxis tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                 tick={AXIS} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={TOOLTIP}
                   formatter={asPercent} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {names.map((model) => (
            <Bar key={model} dataKey={model} name={model.replace("_", " ")}
                 fill={colors[model] ?? "#64748b"} radius={[4, 4, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * One numeric metric per automation strategy.
 *
 * Typed against the metric key rather than an index signature, so passing a
 * field that does not exist on the campaign is a compile error rather than a
 * silently empty bar.
 */
export function StrategyChart<
  T extends { strategy: string },
  K extends keyof T,
>({
  campaigns,
  metric,
  label,
}: {
  campaigns: T[];
  metric: T[K] extends number ? K : never;
  label: string;
}) {
  if (!campaigns?.length) return <Empty message="No campaigns yet." />;
  const data = campaigns.map((c) => ({
    strategy: c.strategy,
    value: Number(c[metric] ?? 0),
  }));
  const colors: Record<string, string> = {
    fixed: "#3b5bdb",
    trigger: "#f59e0b",
    hybrid: "#16a34a",
  };
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
          <XAxis dataKey="strategy" tick={AXIS} axisLine={{ stroke: "#e2e8f0" }} tickLine={false} />
          <YAxis tick={AXIS} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={TOOLTIP} />
          <Bar dataKey="value" name={label} radius={[6, 6, 0, 0]} barSize={48}>
            {data.map((d) => <Cell key={d.strategy} fill={colors[d.strategy] ?? "#64748b"} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function PlatformCreditChart({
  ranking,
}: {
  ranking: Record<string, number>;
}) {
  const data = Object.entries(ranking ?? {}).map(([platform, credit]) => ({
    platform,
    credit,
  }));
  if (!data.length) return <Empty message="No attribution evidence yet." />;
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical"
                  margin={{ top: 4, right: 16, bottom: 4, left: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" horizontal={false} />
          <XAxis type="number" tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                 tick={AXIS} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="platform" width={88}
                 tick={AXIS} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={TOOLTIP}
                   formatter={asPercent} />
          <Bar dataKey="credit" name="Conversion credit" radius={[0, 6, 6, 0]} barSize={20}>
            {data.map((d) => (
              <Cell key={d.platform} fill={PLATFORM_COLOR[d.platform] ?? "#3b5bdb"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
