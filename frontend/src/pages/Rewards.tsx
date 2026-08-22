import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  CircleDollarSign,
  Gift,
  HandHeart,
  History,
  Landmark,
  Sparkles,
  Ticket,
  TrendingUp,
  WalletCards,
} from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { useNavigate } from "react-router-dom";
import { CountUp } from "../components/premium-motion";
import { fetchJson } from "../lib/api";

type RewardStatus = {
  mode: string;
  configured: boolean;
  network: string;
  asset: string;
  defaultAmount: number;
  reason: string | null;
};

const DEMO_REWARD_STATUS: RewardStatus = {
  mode: "demo",
  configured: false,
  network: "Solana devnet",
  asset: "USDC",
  defaultAmount: 50,
  reason: "Reward funding is in preview mode.",
};

const rewardMethods = [
  {
    title: "Partner vouchers",
    description: "Send useful local value at the moment a customer needs it.",
    detail: "GrabFood, Shopee, Starbucks",
    icon: Ticket,
    tone: "bg-amber-50 text-amber-700 ring-amber-100",
  },
  {
    title: "Subscription pause",
    description: "Create breathing room while the account gets back on track.",
    detail: "Pause billing for 1 to 2 months",
    icon: Landmark,
    tone: "bg-slate-100 text-slate-700 ring-slate-200",
  },
  {
    title: "Feature upgrade",
    description: "Unlock the right capability to remove a product blocker.",
    detail: "Premium access for 30 days",
    icon: Sparkles,
    tone: "bg-teal-50 text-teal-700 ring-teal-100",
  },
  {
    title: "Product credits",
    description: "Apply targeted value to the next invoice automatically.",
    detail: "Flexible invoice credit",
    icon: WalletCards,
    tone: "bg-emerald-50 text-emerald-700 ring-emerald-100",
  },
] as const;

const rewardActivity = [
  { customer: "Nexora Solutions", reward: "GrabFood voucher", value: "RM50", impact: "RM4.8K protected", time: "12 min ago", status: "Delivered" },
  { customer: "OrbitWorks", reward: "Invoice credit", value: "RM30", impact: "RM2.1K protected", time: "2 hr ago", status: "Claimed" },
  { customer: "Lumina Tech", reward: "Feature upgrade", value: "RM100", impact: "RM8.6K protected", time: "5 hr ago", status: "Delivered" },
  { customer: "ScaleForge", reward: "Subscription pause", value: "RM50", impact: "RM3.2K protected", time: "Yesterday", status: "Delivered" },
];

const motionEase = [0.22, 1, 0.36, 1] as const;

export default function Rewards() {
  const navigate = useNavigate();
  const shouldReduceMotion = useReducedMotion();
  const [rewardStatus, setRewardStatus] = useState<RewardStatus>(DEMO_REWARD_STATUS);

  useEffect(() => {
    let active = true;

    fetchJson<RewardStatus>("/api/rewards/status", { cache: "no-store" })
      .then((status) => {
        if (active) setRewardStatus({ ...DEMO_REWARD_STATUS, ...status });
      })
      .catch(() => {
        if (active) setRewardStatus(DEMO_REWARD_STATUS);
      });

    return () => {
      active = false;
    };
  }, []);

  const isLive = rewardStatus.configured && rewardStatus.mode.toLowerCase() === "live";
  const transition = { duration: shouldReduceMotion ? 0 : 0.42, ease: motionEase };

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
            Retention value engine
          </div>
          <h1 className="text-3xl font-bold tracking-[-0.04em] text-slate-950 md:text-[2.15rem]">Value Vault</h1>
          <p className="mt-2 max-w-xl text-[15px] leading-6 text-slate-600">
            Turn unused subscription value into timely, personalized retention rewards.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm">
            <span className={isLive ? "h-2 w-2 rounded-full bg-emerald-500" : "h-2 w-2 rounded-full bg-amber-400"} />
            <span className="font-medium text-slate-700">{isLive ? "Reserve connected" : "Preview reserve"}</span>
          </div>
          <motion.button
            type="button"
            onClick={() => navigate("/rewards/funds")}
            whileHover={shouldReduceMotion ? undefined : { y: -1 }}
            whileTap={shouldReduceMotion ? undefined : { scale: 0.985 }}
            className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-teal-800"
          >
            Add funds <ArrowRight className="h-4 w-4" />
          </motion.button>
        </div>
      </header>

      <motion.section
        initial={shouldReduceMotion ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.06 }}
        className="grid gap-4 rounded-2xl border border-teal-100 bg-teal-50/70 p-4 sm:grid-cols-[auto_1fr_auto] sm:items-center"
        aria-label="Value Vault insight"
      >
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-teal-700 shadow-sm">
          <HandHeart className="h-5 w-5" />
        </span>
        <div>
          <p className="text-sm font-semibold text-slate-900">AI is prioritizing value where it can change the outcome.</p>
          <p className="mt-1 text-sm leading-5 text-slate-600">
            Persuadable accounts receive the highest-fit rewards before value is released.
          </p>
        </div>
        <span className="inline-flex w-fit items-center gap-1.5 rounded-full border border-teal-200 bg-white px-2.5 py-1 text-xs font-semibold text-teal-800">
          <Activity className="h-3.5 w-3.5" /> Active
        </span>
      </motion.section>

      <section className="grid gap-4 md:grid-cols-3" aria-label="Value Vault impact">
        {[
          { label: "Recoverable value", value: 12450, note: "Across 128 eligible accounts", icon: CircleDollarSign, accent: "text-slate-950" },
          { label: "Value redeemed", value: 4820, note: "38.7% of available value", icon: Gift, accent: "text-teal-700" },
          { label: "Retention impact", value: 92000, note: "Protected revenue attributed", icon: TrendingUp, accent: "text-emerald-700" },
        ].map((metric, index) => {
          const Icon = metric.icon;
          return (
            <motion.article
              key={metric.label}
              initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.1 + index * 0.05 }}
              whileHover={shouldReduceMotion ? undefined : { y: -2 }}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_8px_24px_rgba(15,23,42,0.05)]"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium text-slate-600">{metric.label}</p>
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-50 text-slate-500">
                  <Icon className="h-4.5 w-4.5" />
                </span>
              </div>
              <CountUp value={metric.value} prefix="RM" className={`mt-5 block text-3xl font-bold tracking-[-0.045em] tabular-nums ${metric.accent}`} />
              <p className="mt-2 text-xs font-medium text-slate-500">{metric.note}</p>
            </motion.article>
          );
        })}
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_0.9fr]">
        <section aria-labelledby="library-title">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Intervention library</p>
              <h2 id="library-title" className="mt-1 text-xl font-bold tracking-[-0.025em] text-slate-950">Choose value with intent</h2>
            </div>
            <motion.button
              type="button"
              onClick={() => navigate("/alerts")}
              whileHover={shouldReduceMotion ? undefined : { x: 2 }}
              className="inline-flex items-center gap-1 text-sm font-semibold text-teal-700 hover:text-teal-800"
            >
              Manage sources <ArrowRight className="h-4 w-4" />
            </motion.button>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {rewardMethods.map((method, index) => {
              const Icon = method.icon;
              return (
                <motion.article
                  key={method.title}
                  initial={shouldReduceMotion ? false : { opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.2 + index * 0.05 }}
                  whileHover={shouldReduceMotion ? undefined : { y: -2, borderColor: "rgba(13, 148, 136, 0.35)" }}
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_5px_18px_rgba(15,23,42,0.035)]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className={`flex h-10 w-10 items-center justify-center rounded-lg ring-1 ${method.tone}`}>
                      <Icon className="h-5 w-5" />
                    </span>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.09em] text-slate-600">Ready</span>
                  </div>
                  <h3 className="mt-5 text-base font-bold text-slate-950">{method.title}</h3>
                  <p className="mt-1 text-sm leading-5 text-slate-600">{method.description}</p>
                  <p className="mt-4 border-t border-slate-100 pt-3 text-xs font-medium text-slate-500">{method.detail}</p>
                </motion.article>
              );
            })}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white shadow-[0_8px_24px_rgba(15,23,42,0.05)]" aria-labelledby="vault-plan-title">
          <div className="border-b border-slate-100 px-5 py-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">AI allocation plan</p>
                <h2 id="vault-plan-title" className="mt-1 text-lg font-bold text-slate-950">Where value goes next</h2>
              </div>
              <Sparkles className="h-5 w-5 text-teal-700" />
            </div>
          </div>
          <ol className="divide-y divide-slate-100">
            {[
              ["01", "Identify", "Find unused value and qualified customer need."],
              ["02", "Match", "Select the smallest reward with the strongest expected lift."],
              ["03", "Measure", "Attribute protected revenue back to the intervention."],
            ].map(([step, title, detail], index) => (
              <motion.li
                key={step}
                initial={shouldReduceMotion ? false : { opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.26 + index * 0.06 }}
                className="flex gap-3 px-5 py-4"
              >
                <span className="mt-0.5 text-xs font-bold tabular-nums text-teal-700">{step}</span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{title}</p>
                  <p className="mt-1 text-sm leading-5 text-slate-600">{detail}</p>
                </div>
              </motion.li>
            ))}
          </ol>
        </section>
      </div>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_8px_24px_rgba(15,23,42,0.05)]" aria-labelledby="reward-activity-title">
        <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-slate-500" />
              <h2 id="reward-activity-title" className="text-lg font-bold text-slate-950">Reward activity</h2>
            </div>
            <p className="mt-1 text-sm text-slate-600">Value sent and the business impact it is expected to protect.</p>
          </div>
          <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
            <CheckCircle2 className="h-3.5 w-3.5" /> {isLive ? "Live tracking" : "Preview tracking"}
          </span>
        </div>
        <div className="divide-y divide-slate-100 md:hidden">
          {rewardActivity.map((item, index) => (
            <motion.article
              key={`${item.customer}-${item.reward}-mobile`}
              initial={shouldReduceMotion ? false : { opacity: 0, y: 7 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.32 + index * 0.045 }}
              className="p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-slate-900">{item.customer}</p>
                  <p className="mt-1 truncate text-sm text-slate-600">{item.reward}</p>
                </div>
                <span className="shrink-0 rounded-full bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-700">{item.status}</span>
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                <div>
                  <dt className="text-xs font-medium text-slate-500">Reward value</dt>
                  <dd className="mt-1 font-semibold tabular-nums text-slate-900">{item.value}</dd>
                </div>
                <div className="min-w-0">
                  <dt className="text-xs font-medium text-slate-500">Expected impact</dt>
                  <dd className="mt-1 truncate font-semibold text-emerald-700">{item.impact}</dd>
                </div>
              </dl>
              <p className="mt-4 border-t border-slate-100 pt-3 text-xs font-medium text-slate-500">Sent {item.time}</p>
            </motion.article>
          ))}
        </div>
        <div className="hidden overflow-x-auto md:block">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
              <tr>
                <th className="px-5 py-3">Customer</th>
                <th className="px-5 py-3">Reward</th>
                <th className="px-5 py-3">Value</th>
                <th className="px-5 py-3">Expected impact</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3 text-right">Sent</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rewardActivity.map((item, index) => (
                <motion.tr
                  key={item.customer}
                  initial={shouldReduceMotion ? false : { opacity: 0, y: 7 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.32 + index * 0.045 }}
                  className="transition-colors hover:bg-slate-50/80"
                >
                  <td className="px-5 py-4 font-semibold text-slate-900">{item.customer}</td>
                  <td className="px-5 py-4 text-slate-600">{item.reward}</td>
                  <td className="px-5 py-4 font-semibold tabular-nums text-slate-900">{item.value}</td>
                  <td className="px-5 py-4 font-medium text-emerald-700">{item.impact}</td>
                  <td className="px-5 py-4"><span className="rounded-full bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-700">{item.status}</span></td>
                  <td className="px-5 py-4 text-right text-slate-500">{item.time}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </motion.div>
  );
}
