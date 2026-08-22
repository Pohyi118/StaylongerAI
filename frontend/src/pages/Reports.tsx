import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  Calendar,
  Check,
  ChevronDown,
  Download,
  FileDown,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CountUp } from "../components/premium-motion";
import { apiUrl } from "../lib/api";

const revenueData = [
  { name: "W1", protected: 12000, lost: 4000 },
  { name: "W2", protected: 18000, lost: 3000 },
  { name: "W3", protected: 24000, lost: 5000 },
  { name: "W4", protected: 45000, lost: 2000 },
  { name: "W5", protected: 85320, lost: 1000 },
];

const segmentData = [
  { name: "Persuadables", rate: 74, color: "#0f766e" },
  { name: "Sure Things", rate: 98, color: "#16a34a" },
  { name: "Sleeping Dogs", rate: 22, color: "#d97706" },
  { name: "Lost Causes", rate: 4, color: "#94a3b8" },
];

const interventionRows = [
  { customer: "Nexora Solutions", action: "WhatsApp rescue", segment: "Persuadable", value: "RM4,800", result: "Recovered", time: "Today, 09:42" },
  { customer: "Lumina Tech", action: "Reverse onboarding", segment: "Persuadable", value: "RM8,600", result: "In progress", time: "Today, 08:18" },
  { customer: "OrbitWorks", action: "Value Vault credit", segment: "Sleeping Dogs", value: "RM2,100", result: "Recovered", time: "Yesterday" },
  { customer: "ScaleForge", action: "Human CSM follow-up", segment: "Persuadable", value: "RM3,200", result: "Awaiting reply", time: "Yesterday" },
];

const REPORT_PERIODS = ["Last 7 Days", "Last 30 Days", "Last 90 Days"] as const;
const motionEase = [0.22, 1, 0.36, 1] as const;

function filenameFromContentDisposition(value: string | null): string | null {
  const filename = value?.match(/filename="?([^";]+)"?/i)?.[1];
  return filename?.endsWith(".pdf") ? filename : null;
}

async function downloadPdfReport(period: string): Promise<void> {
  const response = await fetch(apiUrl(`/api/reports/export.pdf?period=${encodeURIComponent(period)}`), {
    headers: { Accept: "application/pdf" },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "PDF export is unavailable.");
  }

  const report = await response.blob();
  if (report.size < 1024 || !report.type.startsWith("application/pdf")) {
    throw new Error("The exported report was not a valid PDF.");
  }

  const url = URL.createObjectURL(report);
  const anchor = document.createElement("a");
  const date = new Date().toISOString().slice(0, 10);
  const fallbackFilename = `staylongerai-retention-report-${period.toLowerCase().replace(/\s+/g, "-")}-${date}.pdf`;

  anchor.href = url;
  anchor.download = filenameFromContentDisposition(response.headers.get("Content-Disposition")) ?? fallbackFilename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

function ResultBadge({ result }: { result: string }) {
  const tone = result === "Recovered" ? "bg-emerald-50 text-emerald-700" : result === "In progress" ? "bg-teal-50 text-teal-700" : "bg-amber-50 text-amber-800";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${tone}`}>{result}</span>;
}

export default function Reports() {
  const [period, setPeriod] = useState<(typeof REPORT_PERIODS)[number]>("Last 30 Days");
  const [isPeriodOpen, setIsPeriodOpen] = useState(false);
  const [exportStatus, setExportStatus] = useState<"idle" | "exporting" | "success" | "error">("idle");
  const [isCompactViewport, setIsCompactViewport] = useState(false);
  const shouldReduceMotion = useReducedMotion();
  const transition = { duration: shouldReduceMotion ? 0 : 0.42, ease: motionEase };
  const isExporting = exportStatus === "exporting";

  const handleExport = async () => {
    if (isExporting) return;
    setExportStatus("exporting");
    try {
      await downloadPdfReport(period);
      setExportStatus("success");
    } catch {
      setExportStatus("error");
    }
  };

  useEffect(() => {
    if (exportStatus !== "success" && exportStatus !== "error") return;
    const timeout = window.setTimeout(() => setExportStatus("idle"), 3200);
    return () => window.clearTimeout(timeout);
  }, [exportStatus]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 479px)");
    const updateViewport = () => setIsCompactViewport(mediaQuery.matches);

    updateViewport();
    mediaQuery.addEventListener("change", updateViewport);
    return () => mediaQuery.removeEventListener("change", updateViewport);
  }, []);

  return (
    <motion.div
      initial={shouldReduceMotion ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={transition}
      className="flex w-full flex-col gap-6 pb-6"
    >
      <header className="flex flex-col gap-5 border-b border-slate-200 pb-6 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-teal-700">
            <span className="h-2 w-2 rounded-full bg-teal-600" />
            Retention intelligence
          </div>
          <h1 className="text-3xl font-bold tracking-[-0.04em] text-slate-950 md:text-[2.15rem]">Analytics &amp; Reports</h1>
          <p className="mt-2 text-[15px] leading-6 text-slate-600">Measure the retention work that protected revenue, not only the risk that was detected.</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <motion.button
              type="button"
              onClick={() => setIsPeriodOpen((current) => !current)}
              whileTap={shouldReduceMotion ? undefined : { scale: 0.985 }}
              aria-haspopup="listbox"
              aria-expanded={isPeriodOpen}
              aria-controls="report-period-menu"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-semibold text-slate-800 shadow-sm hover:bg-slate-50"
            >
              <Calendar className="h-4 w-4 text-slate-500" />
              {period}
              <ChevronDown className={isPeriodOpen ? "h-4 w-4 rotate-180 text-slate-500 transition-transform" : "h-4 w-4 text-slate-500 transition-transform"} />
            </motion.button>
            <AnimatePresence>
              {isPeriodOpen ? (
                <motion.div
                  id="report-period-menu"
                  role="listbox"
                  aria-label="Report period"
                  initial={shouldReduceMotion ? false : { opacity: 0, y: -6, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={shouldReduceMotion ? undefined : { opacity: 0, y: -4, scale: 0.98 }}
                  transition={{ duration: shouldReduceMotion ? 0 : 0.16, ease: motionEase }}
                  className="absolute right-0 z-30 mt-2 w-48 rounded-xl border border-slate-200 bg-white p-1.5 shadow-[0_16px_38px_rgba(15,23,42,0.14)]"
                >
                  {REPORT_PERIODS.map((option) => {
                    const selected = option === period;
                    return (
                      <button
                        key={option}
                        type="button"
                        role="option"
                        aria-selected={selected}
                        onClick={() => {
                          setPeriod(option);
                          setIsPeriodOpen(false);
                        }}
                        className={selected ? "flex w-full items-center justify-between rounded-lg bg-teal-50 px-3 py-2 text-left text-sm font-semibold text-teal-800" : "flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"}
                      >
                        {option}
                        {selected ? <Check className="h-4 w-4" /> : null}
                      </button>
                    );
                  })}
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>

          <motion.button
            type="button"
            onClick={() => void handleExport()}
            disabled={isExporting}
            whileHover={shouldReduceMotion ? undefined : { y: -1 }}
            whileTap={shouldReduceMotion ? undefined : { scale: 0.985 }}
            className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-teal-800 disabled:cursor-wait disabled:bg-teal-700/70"
          >
            {exportStatus === "success" ? <Check className="h-4 w-4" /> : <Download className="h-4 w-4" />}
            {isExporting ? "Preparing PDF…" : exportStatus === "success" ? "PDF downloaded" : exportStatus === "error" ? "Try export again" : "Export PDF"}
          </motion.button>
          <span className="sr-only" aria-live="polite">
            {exportStatus === "success" ? `PDF report for ${period} downloaded.` : exportStatus === "error" ? "PDF export failed. Please try again." : ""}
          </span>
        </div>
      </header>

      {exportStatus === "error" ? (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-800">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          PDF export is temporarily unavailable. Please try again.
        </div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-3" aria-label="Reporting highlights">
        {[
          { label: "Revenue protected", value: 184320, decimals: 0, suffix: "", note: "+24% vs last period", icon: ShieldCheck, tone: "text-teal-700", trend: "positive" },
          { label: "Intervention ROI", value: 8.4, decimals: 1, suffix: "x", note: "For every RM1 invested", icon: TrendingUp, tone: "text-emerald-700", trend: "positive" },
          { label: "At-risk revenue", value: 91200, decimals: 0, suffix: "", note: "-12.6% vs last period", icon: AlertTriangle, tone: "text-rose-700", trend: "declining" },
        ].map((metric, index) => {
          const Icon = metric.icon;
          const TrendIcon = metric.trend === "declining" ? TrendingDown : ArrowUpRight;
          return (
            <motion.article
              key={metric.label}
              initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.08 + index * 0.05 }}
              whileHover={shouldReduceMotion ? undefined : { y: -2 }}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_8px_24px_rgba(15,23,42,0.05)]"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium text-slate-600">{metric.label}</p>
                <span className={`flex h-9 w-9 items-center justify-center rounded-lg bg-slate-50 ${metric.tone}`}><Icon className="h-4.5 w-4.5" /></span>
              </div>
              <CountUp value={metric.value} decimals={metric.decimals} prefix={metric.label === "Intervention ROI" ? "" : "RM"} suffix={metric.suffix} className="mt-5 block text-3xl font-bold tracking-[-0.045em] tabular-nums text-slate-950" />
              <div className={metric.trend === "declining" ? "mt-2 flex items-center gap-1.5 text-xs font-semibold text-emerald-700" : "mt-2 flex items-center gap-1.5 text-xs font-semibold text-emerald-700"}>
                <TrendIcon className="h-3.5 w-3.5" /> {metric.note}
              </div>
            </motion.article>
          );
        })}
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.45fr_0.85fr]">
        <motion.section
          initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.22 }}
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_8px_24px_rgba(15,23,42,0.05)] sm:p-6"
          aria-labelledby="revenue-chart-title"
        >
          <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Business impact</p>
              <h2 id="revenue-chart-title" className="mt-1 text-lg font-bold text-slate-950">Revenue protected vs lost</h2>
              <p className="mt-1 text-sm text-slate-600">Weekly retention outcome for the selected reporting period.</p>
            </div>
            <div className="flex items-center gap-4 text-xs font-medium text-slate-600">
              <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-teal-700" />Protected</span>
              <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-rose-300" />Lost</span>
            </div>
          </div>
          <div className="h-[224px] w-full sm:h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={revenueData} margin={{ top: 8, right: isCompactViewport ? 0 : 8, left: isCompactViewport ? -16 : -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="protected-area" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0f766e" stopOpacity={0.22} />
                    <stop offset="95%" stopColor="#0f766e" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="lost-area" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#fb7185" stopOpacity={0.16} />
                    <stop offset="95%" stopColor="#fb7185" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 4" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: isCompactViewport ? 11 : 12 }} dy={8} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: isCompactViewport ? 10 : 12 }} tickFormatter={(value) => `RM${value / 1000}k`} width={isCompactViewport ? 46 : 54} />
                <Tooltip contentStyle={{ borderRadius: "12px", border: "1px solid #e2e8f0", boxShadow: "0 12px 28px rgba(15,23,42,0.12)", background: "#ffffff" }} itemStyle={{ fontWeight: 600 }} />
                <Area type="monotone" dataKey="lost" name="Lost" stroke="#fb7185" strokeWidth={2} fill="url(#lost-area)" isAnimationActive={!shouldReduceMotion} animationDuration={640} />
                <Area type="monotone" dataKey="protected" name="Protected" stroke="#0f766e" strokeWidth={3} fill="url(#protected-area)" isAnimationActive={!shouldReduceMotion} animationDuration={760} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.section>

        <motion.section
          initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.27 }}
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_8px_24px_rgba(15,23,42,0.05)] sm:p-6"
          aria-labelledby="segment-chart-title"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Segment performance</p>
          <h2 id="segment-chart-title" className="mt-1 text-lg font-bold text-slate-950">Retention by segment</h2>
          <p className="mt-1 text-sm text-slate-600">Which accounts respond to intervention.</p>
          <div className="mt-5 h-[224px] w-full sm:h-[210px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={segmentData} margin={{ top: 0, right: isCompactViewport ? 2 : 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 4" horizontal={false} stroke="#e2e8f0" />
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: "#475569", fontSize: isCompactViewport ? 11 : 12, fontWeight: 500 }} width={isCompactViewport ? 88 : 92} />
                <Tooltip cursor={{ fill: "rgba(15, 118, 110, 0.04)" }} contentStyle={{ borderRadius: "12px", border: "1px solid #e2e8f0", boxShadow: "0 12px 28px rgba(15,23,42,0.12)", background: "#ffffff" }} />
                <Bar dataKey="rate" name="Retention rate" radius={[0, 7, 7, 0]} barSize={20} isAnimationActive={!shouldReduceMotion} animationDuration={720}>
                  {segmentData.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 flex gap-3 rounded-xl border border-teal-100 bg-teal-50/70 p-3.5">
            <Activity className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" />
            <p className="text-sm leading-5 text-slate-700"><strong className="font-semibold text-slate-950">Persuadables</strong> continue to deliver the strongest return from AI-led retention work.</p>
          </div>
        </motion.section>
      </div>

      <motion.section
        initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.32 }}
        className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_8px_24px_rgba(15,23,42,0.05)]"
        aria-labelledby="intervention-table-title"
      >
        <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Value attribution</p>
            <h2 id="intervention-table-title" className="mt-1 text-lg font-bold text-slate-950">Intervention outcomes</h2>
          </div>
          <div className="inline-flex w-fit items-center gap-2 text-sm text-slate-600"><FileDown className="h-4 w-4 text-teal-700" /> Included in your executive PDF</div>
        </div>
        <div className="divide-y divide-slate-100 md:hidden">
          {interventionRows.map((row, index) => (
            <motion.article
              key={`${row.customer}-${row.action}-mobile`}
              initial={shouldReduceMotion ? false : { opacity: 0, y: 7 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.36 + index * 0.045 }}
              className="p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-slate-900">{row.customer}</p>
                  <p className="mt-1 text-xs text-slate-500">{row.time}</p>
                </div>
                <ResultBadge result={row.result} />
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                <div className="min-w-0">
                  <dt className="text-xs font-medium text-slate-500">AI action</dt>
                  <dd className="mt-1 truncate font-medium text-slate-700">{row.action}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">Segment</dt>
                  <dd className="mt-1"><span className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">{row.segment}</span></dd>
                </div>
              </dl>
              <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
                <span className="text-xs font-medium text-slate-500">Value impact</span>
                <span className="text-sm font-semibold tabular-nums text-emerald-700">{row.value}</span>
              </div>
            </motion.article>
          ))}
        </div>
        <div className="hidden overflow-x-auto md:block">
          <table className="w-full min-w-[780px] text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
              <tr>
                <th className="px-5 py-3">Customer</th>
                <th className="px-5 py-3">AI action</th>
                <th className="px-5 py-3">Segment</th>
                <th className="px-5 py-3">Value impact</th>
                <th className="px-5 py-3">Outcome</th>
                <th className="px-5 py-3 text-right">Recorded</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {interventionRows.map((row, index) => (
                <motion.tr
                  key={`${row.customer}-${row.action}`}
                  initial={shouldReduceMotion ? false : { opacity: 0, y: 7 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.36 + index * 0.045 }}
                  className="transition-colors hover:bg-slate-50/80"
                >
                  <td className="px-5 py-4 font-semibold text-slate-900">{row.customer}</td>
                  <td className="px-5 py-4 text-slate-600">{row.action}</td>
                  <td className="px-5 py-4"><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">{row.segment}</span></td>
                  <td className="px-5 py-4 font-semibold tabular-nums text-emerald-700">{row.value}</td>
                  <td className="px-5 py-4"><ResultBadge result={row.result} /></td>
                  <td className="px-5 py-4 text-right text-slate-500">{row.time}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.section>
    </motion.div>
  );
}
