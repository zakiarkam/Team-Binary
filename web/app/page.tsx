import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  FlaskConical,
  Megaphone,
  PenSquare,
  RefreshCcw,
  Users,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Marketing OS  AI-Powered Digital Marketing Orchestration",
  description:
    "Audience intelligence, campaign automation, predictive analytics and AI content — one closed loop for launch-stage products.",
};

const MODULES = [
  {
    icon: Users,
    title: "Audience Targeting",
    body: "Hybrid rule + machine-learning segmentation groups your visitors by behaviour — built to stay stable even with launch-stage data.",
  },
  {
    icon: Megaphone,
    title: "Campaign Automation",
    body: "Fixed, trigger-based and hybrid automation policies compared head-to-head on the same audience, so strategy is measured, not assumed.",
  },
  {
    icon: BarChart3,
    title: "Analytics & Decisions",
    body: "Funnel analysis, multi-touch attribution and drop-off prediction turned into concrete next-best actions per customer.",
  },
  {
    icon: PenSquare,
    title: "AI Content Refinery",
    body: "A 15-stage pipeline turns your website into platform-ready copy, scored for meaning, platform fit and predicted engagement.",
  },
];

const LOOP = [
  {
    step: "01",
    title: "Understand",
    body: "Visitors are tracked and segmented into behavioural groups.",
  },
  {
    step: "02",
    title: "Act",
    body: "Campaigns run per segment under an automation policy.",
  },
  {
    step: "03",
    title: "Measure",
    body: "Every send, open, click and conversion feeds the funnel and attribution models.",
  },
  {
    step: "04",
    title: "Improve",
    body: "Analytics feedback re-prioritises the next campaign and the next piece of content.",
  },
];

const STATS = [
  { value: "4", label: "AI modules, one loop" },
  { value: "8,000", label: "users in the research audience" },
  { value: "11", label: "controlled experiments" },
  { value: "15", label: "content pipeline stages" },
];

export default function WelcomePage() {
  return (
    <div className="min-h-screen bg-white text-ink">
      {/* Top navigation */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand font-bold text-white shadow-md">
            M
          </span>
          <span className="text-sm font-extrabold tracking-widest">
            MARKETING OS
          </span>
        </div>
        <nav className="flex items-center gap-3">
          <Link
            href="/login"
            className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600
                       transition hover:bg-slate-100 hover:text-slate-900"
          >
            Sign in
          </Link>
          <Link
            href="/signup"
            className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold
                       text-white transition hover:bg-brand-strong"
          >
            Get started
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-linear-to-b from-brand-soft/70 via-white to-white"
        />
        <div className="relative mx-auto max-w-6xl px-6 pb-20 pt-16 text-center">
          <p
            className="mx-auto mb-5 inline-flex items-center gap-2 rounded-full
                        border border-line bg-white px-4 py-1.5 text-xs
                        font-semibold text-slate-600 shadow-sm"
          >
            <FlaskConical size={13} className="text-brand" />A research-first
            marketing platform · Team Binary · University of Moratuwa
          </p>
          <h1
            className="mx-auto max-w-3xl text-4xl font-extrabold tracking-tight
                         sm:text-5xl"
          >
            Launch-stage marketing,{" "}
            <span className="text-brand">orchestrated by AI</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-relaxed text-slate-600">
            Marketing OS joins audience intelligence, campaign automation,
            predictive analytics and AI content generation into one closed
            loop — built for new products that start with almost no data.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 rounded-xl bg-brand px-6
                         py-3 text-sm font-bold text-white shadow-lg shadow-brand/25
                         transition hover:bg-brand-strong"
            >
              Create your account
              <ArrowRight size={16} />
            </Link>
            <Link
              href="/login"
              className="inline-flex items-center gap-2 rounded-xl border
                         border-line bg-white px-6 py-3 text-sm font-bold
                         text-slate-700 transition hover:bg-slate-50"
            >
              Sign in
            </Link>
          </div>

          {/* Stat strip */}
          <dl className="mx-auto mt-14 grid max-w-3xl grid-cols-2 gap-6 sm:grid-cols-4">
            {STATS.map((s) => (
              <div key={s.label}>
                <dt className="sr-only">{s.label}</dt>
                <dd className="text-3xl font-extrabold text-brand">
                  {s.value}
                </dd>
                <p className="mt-1 text-xs font-medium text-slate-500">
                  {s.label}
                </p>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* Modules */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <p className="label text-center">WHAT IS INSIDE</p>
        <h2 className="mt-2 text-center text-2xl font-extrabold tracking-tight">
          Four modules, one closed loop
        </h2>
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {MODULES.map((m) => (
            <div
              key={m.title}
              className="card transition hover:-translate-y-0.5 hover:shadow-lg"
            >
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-soft">
                <m.icon size={19} className="text-brand" />
              </span>
              <h3 className="mt-4 font-bold">{m.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-500">
                {m.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* The loop */}
      <section className="border-y border-line bg-canvas">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="flex items-center justify-center gap-2">
            <RefreshCcw size={16} className="text-brand" />
            <p className="label">HOW IT WORKS</p>
          </div>
          <h2 className="mt-2 text-center text-2xl font-extrabold tracking-tight">
            Every campaign teaches the next one
          </h2>
          <ol className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {LOOP.map((item) => (
              <li key={item.step} className="card">
                <span className="text-xs font-extrabold tracking-widest text-brand">
                  {item.step}
                </span>
                <h3 className="mt-2 font-bold">{item.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-500">
                  {item.body}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Honesty band */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="card sm:flex sm:items-center sm:justify-between sm:gap-8">
          <div>
            <h2 className="text-xl font-extrabold tracking-tight">
              Numbers you can defend
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-500">
              Every figure on the dashboard carries its data basis — research
              dataset, live traffic, or both — and every model ships with its
              honestly measured accuracy, including the negative results. What
              you present is what was measured.
            </p>
            <ul className="mt-4 space-y-1.5 text-sm text-slate-600">
              {[
                "Segmentation, automation and attribution compared under controlled conditions",
                "Multi-touch attribution across every campaign touchpoint",
                "Statistical significance testing on optimisation gains",
              ].map((t) => (
                <li key={t} className="flex items-start gap-2">
                  <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-ok" />
                  {t}
                </li>
              ))}
            </ul>
          </div>
          <Link
            href="/signup"
            className="mt-6 inline-flex shrink-0 items-center gap-2 rounded-xl
                       bg-brand px-6 py-3 text-sm font-bold text-white
                       transition hover:bg-brand-strong sm:mt-0"
          >
            Start orchestrating
            <ArrowRight size={16} />
          </Link>
        </div>
      </section>

      <footer className="border-t border-line">
        <div
          className="mx-auto flex max-w-6xl flex-col items-center justify-between
                        gap-3 px-6 py-8 text-xs text-slate-400 sm:flex-row"
        >
          <p>AI-Powered Digital Marketing Orchestration</p>
          <p>Team Binary · Faculty of IT · University of Moratuwa · 2026</p>
        </div>
      </footer>
    </div>
  );
}
