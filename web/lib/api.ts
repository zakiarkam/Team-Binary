/**
 * Thin client for the FastAPI backend.
 *
 * Every dashboard page goes through here so the base URL, error handling and
 * response shapes live in exactly one place.
 */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * The session token lives in an HttpOnly cookie on the dashboard's own
 * domain — browser JavaScript can never read it. Server components and route
 * handlers CAN, so every server-side API call carries it as a Bearer token.
 * In a client component the dynamic import throws and we send none, which is
 * exactly right: clients talk to our own /api/* route handlers instead.
 */
async function authHeader(): Promise<Record<string, string>> {
  try {
    const { cookies } = await import("next/headers");
    const token = (await cookies()).get("mos_token")?.value;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(await authHeader()),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      /* response had no JSON body — keep the status text */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
};

/**
 * Fetch that resolves to `null` instead of throwing.
 *
 * Most dashboard panels are independent: analytics being unavailable should
 * grey out one card, not blank the whole page.
 */
export async function safeGet<T>(path: string): Promise<T | null> {
  try {
    return await api.get<T>(path);
  } catch {
    return null;
  }
}

// ── Types mirroring the FastAPI response models ──────────────────────────────

/** Which audience a figure rests on: the imported research dataset, a live
 * browser session, or both. */
export type DataBasis = "live" | "dataset" | "mixed" | "no data yet" | null;

export interface Health {
  status: "ok" | "degraded";
  database: "up" | "down";
  email_delivery: "live" | "dry_run";
  version: string;
}

export interface Site {
  id: number;
  site_key: string;
  name: string;
  url: string;
  product_name?: string | null;
  description?: string | null;
  target_audience?: string | null;
}

export interface User {
  id: number;
  email: string;
  company_name: string;
}

export interface DailyPoint {
  day: string;
  visitors: number;
  events: number;
}

export interface AudienceSummary {
  totals: {
    visitors: number;
    known: number;
    reachable: number;
    new_7d: number;
    active_24h: number;
    events: number;
  };
  events_by_type: { event_type: string; count: number }[];
  top_pages: { path: string; views: number; visitors: number }[];
  sources: { source: string; visitors: number }[];
  daily: DailyPoint[];
  segments: {
    segment_name: string;
    visitors: number;
    avg_confidence: number;
    cold_start: number;
  }[];
}

export interface ReachableAudience {
  visitors: number;
  anonymous: number;
  known_no_consent: number;
  unsubscribed: number;
  reachable: number;
  reachable_by_segment: { segment_name: string; reachable: number }[];
  explanation: string;
}

export interface Visitor {
  visitor_id: number;
  visitor_uid: string;
  email: string | null;
  email_consent: boolean;
  utm_source: string | null;
  device: string | null;
  last_seen: string;
  page_views: number;
  clicks: number;
  sessions: number;
  unique_pages: number;
  max_scroll_depth: number;
  time_on_site_seconds: number;
  purchases: number;
  segment_name: string | null;
  segment_confidence: number | null;
  is_cold_start: boolean | null;
  predicted_conversion: number | null;
  drop_off_risk: number | null;
  recommendation: string | null;
}

export interface SegmentRun {
  site_id: number;
  n_visitors: number;
  mode: string;
  segments: Record<string, number>;
  cold_start_users: number;
  mean_confidence: number | null;
  silhouette: number | null;
  classifier_accuracy: number | null;
  reason: string | null;
  model_version: string;
}

export interface CampaignMetrics {
  id: number;
  name: string;
  strategy: string;
  status: string;
  recipients: number;
  pending: number;
  sent: number;
  opens: number;
  clicks: number;
  conversions: number;
  unsubscribes: number;
  open_rate: number;
  click_through_rate: number;
  conversion_rate: number;
  unsubscribe_rate: number;
  conversions_per_1000_sends: number;
  operational_complexity: number;
  data_basis: DataBasis;
  caveat: string;
}

export interface FunnelResult {
  funnel: { sent: number; open: number; click: number; convert: number };
  dropoffs: Record<string, number>;
  by_strategy: Record<string, number | string>[];
  by_segment: Record<string, number | string>[];
  data_basis: DataBasis;
  caveat?: string;
  note?: string;
}

export interface AttributionResult {
  models: Record<string, { platform: string; credit: number }[]>;
  level?: string;
  converters: number;
  data_basis: DataBasis;
  diagnostics: {
    n_converting_journeys?: number;
    mean_distinct_touchpoints?: number;
    single_touch_journeys?: number;
    single_touch_share?: number | null;
    note?: string | null;
  };
  note?: string;
}

export interface Recommendation {
  visitor_id: number;
  email: string | null;
  visitor_uid: string;
  segment_name: string | null;
  predicted_conversion: number;
  drop_off_risk: number;
  recommendation: string;
  recommended_platform: string;
  confidence: number;
  source: "live" | "dataset";
}

export interface ContentAsset {
  id: number;
  platform: string;
  subject: string | null;
  caption: string;
  hashtags: string[];
  cta: string | null;
  image_prompt: string | null;
  /** Which medium the brief is for — adaptive platforms vary per asset. */
  visual_kind: "image" | "video" | null;
  campaign_goal: string | null;
  tone: string | null;
  engagement_score: number | null;
  semantic_score: number | null;
  platform_suitability_score: number | null;
  final_score: number | null;
  engine: string;
  created_at: string;
}

export interface ContentPriorities {
  platform_ranking: Record<string, number>;
  actionable_ranking: Record<string, number>;
  unactionable_channels: Record<string, number>;
  actionable_share: number;
  basis: string;
  converters: number;
  data_basis: DataBasis;
  note?: string | null;
}
