import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  ChevronRight,
  CreditCard,
  Crown,
  Gift,
  Heart,
  MessageCircle,
  Package,
  PauseCircle,
  Phone,
  ShieldAlert,
  Sparkles,
  Target,
  Trash2,
  TrendingUp,
} from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { fetchJson } from "../lib/api";
import { openWhatsApp } from "../whatsapp";

type DashboardRecord = {
  title: string;
  status: string;
  totalRevenueProtectedLabel: string;
  weekGrowth: string;
  roi: string;
  executiveBrief: string;
  metrics: Array<{ label: string; value: string; trend: string }>;
  chartData: Array<{ name: string; revenue: number }>;
  alert: {
    tag: string;
    title: string;
    message: string;
    activityDrop: string;
    affectedUsers: number;
  };
  vipAccounts: Array<{
    name: string;
    plan: string;
    revenueAtRisk: string;
    healthScore: string;
    status: string;
    phone?: string;
  }>;
  segments: Array<{
    title: string;
    description: string;
    value: number;
    action: string;
    theme: string;
  }>;
  rescues: Array<{
    name: string;
    time: string;
    reward: string;
    type: string;
    status: string;
    network: string;
  }>;
  inventory: InventoryRecord[];
};

type InventoryRecord = {
  id: string;
  source: string;
  sender: string;
  receivedAt: string;
  itemCount: number;
  items: Array<{ item: string; quantity: string | number }>;
  processor: string;
  paymentStatus: string;
};

const DEFAULT_DASHBOARD: DashboardRecord = {
  title: "Revenue Command Center",
  status: "AI Protection Active",
  totalRevenueProtectedLabel: "RM184,320",
  weekGrowth: "+12% this week",
  roi: "8.4×",
  executiveBrief:
    "Churn exposure decreased 12% this week. 9 persuadable accounts were automatically rescued. A coordinated activity drop across 127 SME customers may indicate a competitor campaign.",
  metrics: [
    { label: "Accounts Rescued", value: "47", trend: "+4" },
    { label: "MRR at Risk", value: "RM24,500", trend: "-12%" },
    { label: "Agent Payments", value: "RM450", trend: "Secure settlement" },
    { label: "Health Avg", value: "72/100", trend: "Stable" },
  ],
  chartData: [
    { name: "1", revenue: 120000 },
    { name: "5", revenue: 130000 },
    { name: "10", revenue: 128000 },
    { name: "15", revenue: 145000 },
    { name: "20", revenue: 160000 },
    { name: "25", revenue: 175000 },
    { name: "30", revenue: 184320 },
  ],
  alert: {
    tag: "Emergency",
    title: "Sudden drop in user activity detected.",
    message: "Possible competitor move targeting SME segment.",
    activityDrop: "-37%",
    affectedUsers: 2391,
  },
  vipAccounts: [
    {
      name: "Acme Corp",
      plan: "Enterprise",
      revenueAtRisk: "RM12,460",
      healthScore: "31 / 100 (87% risk)",
      status: "Human Alert",
    },
    {
      name: "Nexus Logistics",
      plan: "Mid-Market",
      revenueAtRisk: "RM8,200",
      healthScore: "42 / 100 (71% risk)",
      status: "Human Alert",
    },
  ],
  segments: [
    {
      title: "Persuadables",
      description: "High risk, can be saved",
      value: 45,
      action: "AI Action: Invest Rewards",
      theme: "pink",
    },
    {
      title: "Sure Things",
      description: "Loyal and engaged",
      value: 1204,
      action: "AI Action: No Discount",
      theme: "emerald",
    },
    {
      title: "Sleeping Dogs",
      description: "Dormant but still paying",
      value: 89,
      action: "AI Action: Monitor",
      theme: "amber",
    },
    {
      title: "Lost Causes",
      description: "Unlikely to stay",
      value: 12,
      action: "AI Action: Ignore",
      theme: "slate",
    },
  ],
  rescues: [
    {
      name: "Lumina Tech",
      time: "12m ago",
      reward: "GrabFood RM50",
      type: "Value Vault",
      status: "Claimed",
      network: "x402/Solana",
    },
    {
      name: "ScaleForge",
      time: "45m ago",
      reward: "Pause Subscription",
      type: "Billing",
      status: "Executed",
      network: "Internal",
    },
    {
      name: "OrbitWorks",
      time: "2h ago",
      reward: "Shopee RM30",
      type: "Value Vault",
      status: "Claimed",
      network: "x402/Solana",
    },
  ],
  inventory: [],
};

const PANEL =
  "rounded-[22px] border border-slate-200/90 bg-white shadow-[0_16px_42px_-32px_rgba(15,23,42,0.32)]";

function formatInventoryTime(value: string): string {
  const receivedAt = new Date(value);
  if (Number.isNaN(receivedAt.getTime())) return value;

  return receivedAt.toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatAnimatedValue(prefix: string, amount: number, suffix: string, decimals: number): string {
  const formatted = Math.abs(amount).toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return `${prefix}${amount < 0 ? "-" : ""}${formatted}${suffix}`;
}

function displayFriendlySettlement(value: string): string {
  return /(solana|x402)/i.test(value) ? "Secure settlement" : value;
}

function displaySegmentTitle(value: string): string {
  return value.trim().toLowerCase() === "inactive" ? "Sleeping Dogs" : value;
}

function getRiskPercent(healthScore: string): number {
  const risk = healthScore.match(/\((\d+)%\s*risk\)/i);
  if (!risk) return 70;
  return Math.min(Math.max(Number(risk[1]), 0), 100);
}

function AnimatedValue({
  value,
  className,
  duration = 850,
}: {
  value: string | number;
  className?: string;
  duration?: number;
}) {
  const reduceMotion = useReducedMotion();
  const label = String(value);
  const [displayValue, setDisplayValue] = useState(label);

  useEffect(() => {
    const match = label.match(/^([^\d-]*)(-?[\d,]+(?:\.\d+)?)(.*)$/);
    if (!match || reduceMotion) {
      setDisplayValue(label);
      return;
    }

    const [, prefix, rawNumber, suffix] = match;
    const target = Number(rawNumber.replace(/,/g, ""));
    if (!Number.isFinite(target)) {
      setDisplayValue(label);
      return;
    }

    const decimals = rawNumber.split(".")[1]?.length ?? 0;
    const startTime = performance.now();
    let frame = 0;

    setDisplayValue(formatAnimatedValue(prefix, 0, suffix, decimals));

    const tick = (now: number) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(formatAnimatedValue(prefix, target * eased, suffix, decimals));

      if (progress < 1) frame = window.requestAnimationFrame(tick);
    };

    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, [duration, label, reduceMotion]);

  return (
    <span className={className} aria-label={label}>
      {displayValue}
    </span>
  );
}

function SectionHeading({
  id,
  eyebrow,
  title,
  description,
  action,
  onAction,
}: {
  id?: string;
  eyebrow: string;
  title: string;
  description?: string;
  action?: string;
  onAction?: () => void;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3 md:mb-5">
      <div>
        <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-teal-700">{eyebrow}</div>
        <h2 id={id} className="mt-1 text-xl font-bold tracking-[-0.035em] text-slate-950 sm:text-2xl">{title}</h2>
        {description ? <p className="mt-1 text-sm text-slate-500">{description}</p> : null}
      </div>
      {action && onAction ? (
        <motion.button
          type="button"
          onClick={onAction}
          className="flex items-center gap-1 text-sm font-semibold text-teal-700"
          whileHover={reduceMotion ? undefined : { x: 2 }}
          whileTap={reduceMotion ? undefined : { scale: 0.98 }}
        >
          {action} <ChevronRight className="h-4 w-4" />
        </motion.button>
      ) : null}
    </div>
  );
}

export default function Dashboard() {
  const [dashboard, setDashboard] = useState<DashboardRecord>(DEFAULT_DASHBOARD);
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const recentInventory = [...dashboard.inventory]
    .sort((left, right) => Date.parse(right.receivedAt) - Date.parse(left.receivedAt))
    .slice(0, 3);
  const primaryVip = dashboard.vipAccounts[0];
  const persuadable = dashboard.segments.find((segment) => displaySegmentTitle(segment.title) === "Persuadables");
  const vaultActivity = dashboard.rescues.find((rescue) => rescue.type === "Value Vault");

  const handleAction = (route: string) => {
    navigate(route);
  };

  const handleNotifyExecTeam = () => {
    openWhatsApp({
      phone: import.meta.env.VITE_EXEC_WHATSAPP_NUMBER,
      message:
        "Executive Alert: churn risk is rising in the SME segment. Activity has dropped by 37% and 2,391 users are affected. Please review the retention plan immediately.",
    });
  };

  const handleAssignCsm = (account: DashboardRecord["vipAccounts"][number]) => {
    openWhatsApp({
      phone: import.meta.env.VITE_CSM_WHATSAPP_NUMBER,
      message: `CSM assignment request\n\nAccount: ${account.name}\nPlan: ${account.plan}\nRevenue at risk: ${account.revenueAtRisk}\nHealth: ${account.healthScore}\n\nPlease assign an owner and confirm the follow-up time.`,
    });
  };

  const handleCallNow = (account: DashboardRecord["vipAccounts"][number]) => {
    openWhatsApp({
      phone: account.phone || import.meta.env.VITE_CUSTOMER_WHATSAPP_NUMBER,
      message: `Hi ${account.name} team, this is Acme Admin. We noticed a recent drop in account activity and would like to help. Is now a good time for a quick retention check-in?`,
    });
  };

  useEffect(() => {
    let isMounted = true;
    let pollTimer: ReturnType<typeof setTimeout> | undefined;
    let requestController: AbortController | undefined;

    const loadDashboard = async () => {
      requestController = new AbortController();

      try {
        const data = await fetchJson<DashboardRecord>("/api/dashboard", {
          cache: "no-store",
          signal: requestController.signal,
        });

        if (isMounted) {
          setDashboard({
            ...DEFAULT_DASHBOARD,
            ...data,
            inventory: Array.isArray(data.inventory) ? data.inventory : [],
          });
        }
      } catch {
        // Keep the last successful payload (or the built-in demo data) available.
      } finally {
        if (isMounted) pollTimer = setTimeout(loadDashboard, 5000);
      }
    };

    void loadDashboard();

    return () => {
      isMounted = false;
      requestController?.abort();
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, []);

  return (
    <motion.div
      className="flex w-full flex-col gap-8 pb-6"
      initial={reduceMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduceMotion ? 0 : 0.38, ease: "easeOut" }}
    >
      <motion.header
        className="flex flex-col justify-between gap-4 border-b border-slate-200/80 pb-6 md:flex-row md:items-end"
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reduceMotion ? 0 : 0.36, ease: "easeOut" }}
      >
        <div>
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-teal-700">
            <span className="h-px w-6 bg-teal-600/45" /> Retention intelligence
          </div>
          <h1 className="mt-2 text-3xl font-bold tracking-[-0.05em] text-slate-950 sm:text-4xl">{dashboard.title}</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-500">
            See who is at risk, why it matters, and the next best AI-led action.
          </p>
        </div>

        <div
          className="flex w-fit items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700"
          aria-live="polite"
        >
          <motion.span
            className="relative flex h-2 w-2"
            animate={reduceMotion ? undefined : { scale: [1, 1.45, 1], opacity: [0.95, 0.42, 0.95] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
          >
            <span className="absolute inset-0 rounded-full bg-emerald-400/60" />
            <span className="relative m-auto h-2 w-2 rounded-full bg-emerald-600" />
          </motion.span>
          {dashboard.status}
        </div>
      </motion.header>

      <motion.section
        aria-labelledby="competitor-alert-title"
        className={`${PANEL} relative overflow-hidden border-rose-200/90 p-5 sm:p-6 lg:p-7`}
        initial={reduceMotion ? false : { opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reduceMotion ? 0 : 0.42, delay: reduceMotion ? 0 : 0.05, ease: "easeOut" }}
      >
        <div className="absolute inset-y-0 left-0 w-1 bg-rose-500" />
        <div className="absolute right-[-26px] top-[-26px] h-36 w-36 rounded-full bg-rose-100/70 blur-2xl" />
        <div className="relative grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.9fr)] lg:items-end">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-600 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.13em] text-white">
                <ShieldAlert className="h-3.5 w-3.5" /> Competitor alert
              </span>
              <span className="text-xs font-semibold text-rose-700">{dashboard.alert.tag}</span>
            </div>
            <h2 id="competitor-alert-title" className="mt-4 max-w-3xl text-2xl font-bold tracking-[-0.04em] text-slate-950 sm:text-3xl">
              {dashboard.alert.title}
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{dashboard.alert.message}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              <motion.button
                type="button"
                onClick={() => handleAction("/alerts")}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white shadow-[0_10px_24px_-16px_rgba(15,23,42,0.9)]"
                whileHover={reduceMotion ? undefined : { y: -2 }}
                whileTap={reduceMotion ? undefined : { scale: 0.98 }}
              >
                Investigate alert <ArrowRight className="h-4 w-4" />
              </motion.button>
              <motion.button
                type="button"
                onClick={() => handleAction("/customers")}
                className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700"
                whileHover={reduceMotion ? undefined : { y: -2, borderColor: "rgba(13, 148, 136, 0.45)" }}
                whileTap={reduceMotion ? undefined : { scale: 0.98 }}
              >
                View customers
              </motion.button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-2">
            <div className="rounded-2xl border border-rose-100 bg-rose-50/70 p-3.5">
              <div className="text-[10px] font-semibold uppercase tracking-[0.11em] text-slate-500">Activity drop</div>
              <AnimatedValue value={dashboard.alert.activityDrop} className="mt-1 block text-2xl font-bold tracking-[-0.04em] text-rose-700" />
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white/85 p-3.5">
              <div className="text-[10px] font-semibold uppercase tracking-[0.11em] text-slate-500">Affected users</div>
              <AnimatedValue value={dashboard.alert.affectedUsers} className="mt-1 block text-2xl font-bold tracking-[-0.04em] text-slate-950" />
            </div>
            <motion.button
              type="button"
              onClick={handleNotifyExecTeam}
              className="col-span-2 flex min-h-[70px] items-center justify-between rounded-2xl border border-teal-200 bg-teal-50/80 p-3.5 text-left text-teal-800 sm:col-span-1 lg:col-span-2"
              whileHover={reduceMotion ? undefined : { y: -2 }}
              whileTap={reduceMotion ? undefined : { scale: 0.985 }}
            >
              <span>
                <span className="block text-[10px] font-bold uppercase tracking-[0.12em] text-teal-700">Escalate now</span>
                <span className="mt-1 block text-sm font-semibold">Notify executive team</span>
              </span>
              <MessageCircle className="h-5 w-5" />
            </motion.button>
          </div>
        </div>
      </motion.section>

      <section aria-labelledby="attention-title">
        <SectionHeading
          id="attention-title"
          eyebrow="AI action center"
          title="What needs attention now"
          description="Prioritized actions chosen from live retention signals."
          action="View all alerts"
          onAction={() => handleAction("/alerts")}
        />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <motion.article
            className={`${PANEL} border-rose-100 p-4`}
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.36, delay: reduceMotion ? 0 : 0.1 }}
            whileHover={reduceMotion ? undefined : { y: -3 }}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="rounded-lg bg-rose-50 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-rose-700">High priority</span>
              <ShieldAlert className="h-4 w-4 text-rose-600" />
            </div>
            <h3 className="mt-4 font-bold tracking-[-0.02em] text-slate-950">Competitor signal detected</h3>
            <p className="mt-1 text-sm leading-5 text-slate-500">{dashboard.alert.affectedUsers.toLocaleString()} users require review.</p>
            <button type="button" onClick={() => handleAction("/alerts")} className="mt-4 text-sm font-semibold text-teal-700">
              Review signal
            </button>
          </motion.article>

          <motion.article
            className={`${PANEL} p-4`}
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.36, delay: reduceMotion ? 0 : 0.15 }}
            whileHover={reduceMotion ? undefined : { y: -3 }}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="rounded-lg bg-amber-50 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-amber-700">VIP risk</span>
              <Crown className="h-4 w-4 text-amber-600" />
            </div>
            <h3 className="mt-4 font-bold tracking-[-0.02em] text-slate-950">{primaryVip?.name ?? "VIP account"}</h3>
            <p className="mt-1 text-sm leading-5 text-slate-500">{primaryVip ? `${primaryVip.revenueAtRisk} at risk · ${primaryVip.plan}` : "Review the highest-value account."}</p>
            <button
              type="button"
              onClick={() => (primaryVip ? handleAssignCsm(primaryVip) : handleAction("/customers"))}
              className="mt-4 text-sm font-semibold text-teal-700"
            >
              {primaryVip ? "Assign CSM" : "Review account"}
            </button>
          </motion.article>

          <motion.article
            className={`${PANEL} p-4`}
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.36, delay: reduceMotion ? 0 : 0.2 }}
            whileHover={reduceMotion ? undefined : { y: -3 }}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="rounded-lg bg-teal-50 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-teal-700">Intervention ready</span>
              <Target className="h-4 w-4 text-teal-600" />
            </div>
            <h3 className="mt-4 font-bold tracking-[-0.02em] text-slate-950">Persuadables are ready</h3>
            <p className="mt-1 text-sm leading-5 text-slate-500">
              {persuadable ? `${persuadable.value.toLocaleString()} accounts are retainable now.` : "Review accounts ready for rescue."}
            </p>
            <button type="button" onClick={() => handleAction("/customers")} className="mt-4 text-sm font-semibold text-teal-700">
              Launch rescue
            </button>
          </motion.article>

          <motion.article
            className={`${PANEL} p-4`}
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.36, delay: reduceMotion ? 0 : 0.25 }}
            whileHover={reduceMotion ? undefined : { y: -3 }}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="rounded-lg bg-teal-50 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-teal-700">Value Vault</span>
              <Gift className="h-4 w-4 text-teal-600" />
            </div>
            <h3 className="mt-4 font-bold tracking-[-0.02em] text-slate-950">Reward intervention</h3>
            <p className="mt-1 text-sm leading-5 text-slate-500">
              {vaultActivity ? `${vaultActivity.reward} is ready for a recovery flow.` : "Review available customer value."}
            </p>
            <button type="button" onClick={() => handleAction("/rewards")} className="mt-4 text-sm font-semibold text-teal-700">
              Open Value Vault
            </button>
          </motion.article>
        </div>
      </section>

      <section aria-labelledby="business-impact-title">
        <SectionHeading
          id="business-impact-title"
          eyebrow="Business impact"
          title="Revenue protection at a glance"
          description="The financial outcome of autonomous retention work."
          action="Open analytics"
          onAction={() => handleAction("/reports")}
        />
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(300px,0.75fr)]">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {dashboard.metrics.map((metric, index) => {
              const isRiskImproving = /risk/i.test(metric.label) && metric.trend.startsWith("-");
              const trendClass = isRiskImproving || metric.label === "Accounts Rescued" ? "text-emerald-700" : "text-slate-500";
              return (
                <motion.article
                  key={metric.label}
                  className={`${PANEL} min-w-0 p-4`}
                  initial={reduceMotion ? false : { opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: reduceMotion ? 0 : 0.34, delay: reduceMotion ? 0 : 0.12 + index * 0.05 }}
                  whileHover={reduceMotion ? undefined : { y: -3 }}
                >
                  <div className="truncate text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">{metric.label}</div>
                  <AnimatedValue value={metric.value} className="mt-2 block truncate text-xl font-bold tracking-[-0.04em] text-slate-950 tabular-nums sm:text-2xl" />
                  <div className={`mt-2 flex items-center gap-1 text-xs font-semibold ${trendClass}`}>
                    {metric.label === "Accounts Rescued" || isRiskImproving ? <TrendingUp className="h-3.5 w-3.5" /> : null}
                    {displayFriendlySettlement(metric.trend)}
                  </div>
                </motion.article>
              );
            })}
          </div>

          <motion.article
            className={`${PANEL} min-h-[180px] p-4 sm:p-5`}
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.38, delay: reduceMotion ? 0 : 0.25 }}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">Revenue protected</div>
                <AnimatedValue value={dashboard.totalRevenueProtectedLabel} className="mt-1 block text-2xl font-bold tracking-[-0.05em] text-slate-950 tabular-nums" duration={1050} />
              </div>
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">{dashboard.weekGrowth}</span>
            </div>
            <div className="mt-4 h-20" aria-label="Thirty-day revenue protected trend">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={dashboard.chartData} margin={{ top: 8, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="dashboard-protected-revenue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0f9488" stopOpacity={0.22} />
                      <stop offset="100%" stopColor="#0f9488" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="#0f9488"
                    strokeWidth={2.5}
                    fill="url(#dashboard-protected-revenue)"
                    isAnimationActive={!reduceMotion}
                    animationDuration={700}
                    animationEasing="ease-out"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
              <span>30-day trend</span>
              <span>Intervention ROI: <strong className="font-semibold text-slate-800">{dashboard.roi}</strong></span>
            </div>
          </motion.article>
        </div>
      </section>

      <section aria-labelledby="customer-risk-title">
        <SectionHeading
          id="customer-risk-title"
          eyebrow="Customer risk"
          title="High-value accounts requiring a human decision"
          description="AI has surfaced the next accounts where timely outreach can protect revenue."
          action="View all customers"
          onAction={() => handleAction("/customers")}
        />
        <div className="grid gap-4 lg:grid-cols-2">
          {dashboard.vipAccounts.map((account, index) => {
            const riskPercent = getRiskPercent(account.healthScore);
            return (
              <motion.article
                key={account.name}
                className={`${PANEL} overflow-hidden p-5`}
                initial={reduceMotion ? false : { opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: reduceMotion ? 0 : 0.38, delay: reduceMotion ? 0 : 0.12 + index * 0.07 }}
                whileHover={reduceMotion ? undefined : { y: -3, boxShadow: "0 20px 42px -30px rgba(15, 23, 42, 0.34)" }}
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-950 text-sm font-bold text-white">
                      {account.name.slice(0, 1)}
                    </div>
                    <div className="min-w-0">
                      <h3 className="truncate text-lg font-bold tracking-[-0.025em] text-slate-950">{account.name}</h3>
                      <p className="mt-0.5 text-sm text-slate-500">{account.plan}</p>
                    </div>
                  </div>
                  <span className="rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-rose-700">
                    {account.status}
                  </span>
                </div>

                <div className="mt-5 grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-slate-50 p-3">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">Revenue at risk</div>
                    <div className="mt-1 text-lg font-bold tracking-[-0.025em] text-slate-950">{account.revenueAtRisk}</div>
                  </div>
                  <div className="rounded-xl bg-rose-50/70 p-3">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">Health score</div>
                    <div className="mt-1 text-lg font-bold tracking-[-0.025em] text-rose-700">{account.healthScore}</div>
                  </div>
                </div>

                <div className="mt-4">
                  <div className="mb-2 flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-500">Churn risk</span>
                    <span className="text-rose-700">{riskPercent}% elevated</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-rose-100">
                    <motion.div
                      className="h-full rounded-full bg-rose-500"
                      initial={{ scaleX: reduceMotion ? riskPercent / 100 : 0 }}
                      animate={{ scaleX: riskPercent / 100 }}
                      transition={{ duration: reduceMotion ? 0 : 0.7, delay: reduceMotion ? 0 : 0.28 + index * 0.08, ease: "easeOut" }}
                      style={{ transformOrigin: "left" }}
                    />
                  </div>
                </div>

                <div className="mt-5 flex flex-wrap gap-2">
                  <motion.button
                    type="button"
                    onClick={() => handleAssignCsm(account)}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-slate-950 px-3.5 py-2.5 text-sm font-semibold text-white"
                    whileHover={reduceMotion ? undefined : { y: -2 }}
                    whileTap={reduceMotion ? undefined : { scale: 0.98 }}
                  >
                    <MessageCircle className="h-3.5 w-3.5" /> Assign CSM
                  </motion.button>
                  <motion.button
                    type="button"
                    onClick={() => handleCallNow(account)}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-semibold text-slate-700"
                    whileHover={reduceMotion ? undefined : { y: -2, borderColor: "rgba(13, 148, 136, 0.48)" }}
                    whileTap={reduceMotion ? undefined : { scale: 0.98 }}
                  >
                    <Phone className="h-3.5 w-3.5 text-teal-700" /> Call now
                  </motion.button>
                </div>
              </motion.article>
            );
          })}
        </div>
      </section>

      <section aria-labelledby="triage-title">
        <SectionHeading
          id="triage-title"
          eyebrow="AI triage"
          title="Know which customers are worth saving"
          description="A clear, explainable classification system keeps interventions focused."
          action="Open customer intelligence"
          onAction={() => handleAction("/customers")}
        />
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {dashboard.segments.map((segment, index) => {
            const title = displaySegmentTitle(segment.title);
            const Icon = title === "Persuadables" ? Target : title === "Sure Things" ? Heart : title === "Sleeping Dogs" ? PauseCircle : Trash2;
            const tone =
              title === "Persuadables"
                ? { surface: "bg-amber-50", icon: "bg-amber-100 text-amber-700", value: "text-amber-800" }
                : title === "Sure Things"
                  ? { surface: "bg-emerald-50", icon: "bg-emerald-100 text-emerald-700", value: "text-emerald-800" }
                  : title === "Sleeping Dogs"
                    ? { surface: "bg-slate-100", icon: "bg-slate-200 text-slate-700", value: "text-slate-800" }
                    : { surface: "bg-rose-50", icon: "bg-rose-100 text-rose-700", value: "text-rose-800" };

            return (
              <motion.article
                key={`${segment.title}-${index}`}
                className={`${PANEL} p-4`}
                initial={reduceMotion ? false : { opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: reduceMotion ? 0 : 0.36, delay: reduceMotion ? 0 : 0.1 + index * 0.055 }}
                whileHover={reduceMotion ? undefined : { y: -3 }}
                whileTap={reduceMotion ? undefined : { scale: 0.995 }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${tone.icon}`}>
                    <Icon className="h-4.5 w-4.5" />
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.1em] ${tone.surface} ${tone.value}`}>
                    AI classified
                  </span>
                </div>
                <h3 className="mt-4 text-lg font-bold tracking-[-0.025em] text-slate-950">{title}</h3>
                <p className="mt-1 min-h-10 text-sm leading-5 text-slate-500">{segment.description}</p>
                <AnimatedValue value={segment.value} className={`mt-4 block text-3xl font-bold tracking-[-0.05em] tabular-nums ${tone.value}`} />
                <div className="mt-2 text-xs font-semibold text-slate-500">{segment.action}</div>
              </motion.article>
            );
          })}
        </div>
      </section>

      {dashboard.inventory.length > 0 ? (
        <motion.section
          aria-labelledby="inventory-title"
          className={`${PANEL} p-5 sm:p-6`}
          initial={reduceMotion ? false : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.38, delay: reduceMotion ? 0 : 0.14 }}
        >
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
                <Package className="h-5 w-5" />
              </div>
              <div>
                <h2 id="inventory-title" className="font-bold tracking-[-0.025em] text-slate-950">Recent WhatsApp inventory</h2>
                <p className="mt-0.5 text-sm text-slate-500">Structured items extracted from customer uploads.</p>
              </div>
            </div>
            <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700">{dashboard.inventory.length} processed</span>
          </div>
          <div className="grid gap-3 lg:grid-cols-3">
            {recentInventory.map((record, index) => (
              <motion.article
                key={record.id}
                className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4"
                initial={reduceMotion ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: reduceMotion ? 0 : 0.32, delay: reduceMotion ? 0 : 0.18 + index * 0.05 }}
                whileHover={reduceMotion ? undefined : { y: -2 }}
              >
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-bold text-slate-900">{record.sender}</div>
                    <div className="mt-0.5 text-xs text-slate-500">{formatInventoryTime(record.receivedAt)}</div>
                  </div>
                  <span className="rounded-lg bg-white px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-teal-700">{record.processor}</span>
                </div>
                <div className="space-y-1.5">
                  {record.items.slice(0, 3).map((item, itemIndex) => (
                    <div key={`${record.id}-${item.item}-${itemIndex}`} className="flex items-center justify-between gap-3 text-sm">
                      <span className="truncate text-slate-700">{item.item}</span>
                      <span className="shrink-0 font-semibold text-slate-500">× {item.quantity}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-200 pt-3 text-xs text-slate-500">
                  <span>{record.itemCount} items</span>
                  <span className="capitalize">Reward: {record.paymentStatus.replace(/_/g, " ")}</span>
                </div>
              </motion.article>
            ))}
          </div>
        </motion.section>
      ) : null}

      <motion.section
        aria-labelledby="recent-rescues-title"
        className={`${PANEL} overflow-hidden`}
        initial={reduceMotion ? false : { opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reduceMotion ? 0 : 0.38, delay: reduceMotion ? 0 : 0.16 }}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 sm:px-6">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-teal-700">Autonomous activity</div>
            <h2 id="recent-rescues-title" className="mt-1 text-lg font-bold tracking-[-0.025em] text-slate-950">Recent rescues</h2>
          </div>
          <motion.button
            type="button"
            onClick={() => handleAction("/alerts")}
            className="text-sm font-semibold text-teal-700"
            whileHover={reduceMotion ? undefined : { x: 2 }}
            whileTap={reduceMotion ? undefined : { scale: 0.98 }}
          >
            View log
          </motion.button>
        </div>
        <div className="divide-y divide-slate-100 px-5 sm:px-6">
          {dashboard.rescues.map((rescue, index) => (
            <motion.article
              key={`${rescue.name}-${rescue.time}`}
              className="flex items-center justify-between gap-4 py-4"
              initial={reduceMotion ? false : { opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: reduceMotion ? 0 : 0.32, delay: reduceMotion ? 0 : 0.2 + index * 0.055 }}
            >
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
                  {rescue.type === "Value Vault" ? <Gift className="h-4 w-4" /> : <CreditCard className="h-4 w-4" />}
                </div>
                <div className="min-w-0">
                  <div className="truncate text-sm font-bold text-slate-900">{rescue.name}</div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
                    <span>{rescue.time}</span>
                    <span className="font-medium text-teal-700">{rescue.reward}</span>
                  </div>
                </div>
              </div>
              <div className="hidden text-right sm:block">
                <div className="text-sm font-bold text-emerald-700">{rescue.status}</div>
                <div className="mt-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">{displayFriendlySettlement(rescue.network)}</div>
              </div>
            </motion.article>
          ))}
        </div>
      </motion.section>

      <motion.section
        className={`${PANEL} relative overflow-hidden bg-slate-950 p-5 text-white sm:p-6`}
        initial={reduceMotion ? false : { opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reduceMotion ? 0 : 0.38, delay: reduceMotion ? 0 : 0.2 }}
      >
        <div className="absolute right-[-34px] top-[-34px] h-36 w-36 rounded-full bg-teal-400/15 blur-2xl" />
        <div className="relative flex flex-col justify-between gap-5 md:flex-row md:items-end">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.15em] text-teal-300">
              <Sparkles className="h-3.5 w-3.5" /> AI executive brief
            </div>
            <p className="mt-3 text-base leading-7 text-slate-100 sm:text-lg">{dashboard.executiveBrief}</p>
          </div>
          <motion.button
            type="button"
            onClick={() => handleAction("/reports")}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-950"
            whileHover={reduceMotion ? undefined : { y: -2 }}
            whileTap={reduceMotion ? undefined : { scale: 0.98 }}
          >
            View analysis <ArrowRight className="h-4 w-4" />
          </motion.button>
        </div>
      </motion.section>
    </motion.div>
  );
}
