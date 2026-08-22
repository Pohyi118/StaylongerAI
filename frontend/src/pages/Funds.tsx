import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Check,
  Copy,
  ExternalLink,
  Info,
  LockKeyhole,
  RefreshCw,
  ShieldCheck,
  WalletCards,
  Zap,
} from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { useNavigate } from "react-router-dom";
import { fetchJson, postJson } from "../lib/api";

type FundingStatus = {
  mode: string;
  configured: boolean;
  network: string;
  asset: string;
  defaultAmount: number;
  reason: string | null;
  walletAddress: string | null;
  usdcMint: string | null;
  solBalance: number | null;
  usdcBalance: number | null;
  balanceAvailable: boolean;
  explorerUrl: string | null;
  demoFunding?: boolean;
};

const EMPTY_STATUS: FundingStatus = {
  mode: "demo",
  configured: false,
  network: "Solana devnet",
  asset: "USDC",
  defaultAmount: 50,
  reason: "Reward funding is in preview mode.",
  walletAddress: null,
  usdcMint: null,
  solBalance: null,
  usdcBalance: null,
  balanceAvailable: false,
  explorerUrl: null,
};

const motionEase = [0.22, 1, 0.36, 1] as const;

function formatBalance(value: number | null, maximumFractionDigits = 2): string {
  if (value === null) return "Unavailable";
  return value.toLocaleString("en-MY", { maximumFractionDigits });
}

export default function Funds() {
  const navigate = useNavigate();
  const shouldReduceMotion = useReducedMotion();
  const [status, setStatus] = useState<FundingStatus>(EMPTY_STATUS);
  const [amount, setAmount] = useState("100");
  const [isLoading, setIsLoading] = useState(true);
  const [isFunding, setIsFunding] = useState(false);
  const [copied, setCopied] = useState(false);
  const [notice, setNotice] = useState("");

  const loadStatus = useCallback(async (showConfirmation = false) => {
    setIsLoading(true);
    try {
      const nextStatus = await fetchJson<FundingStatus>("/api/rewards/funding", { cache: "no-store" });
      setStatus({ ...EMPTY_STATUS, ...nextStatus });
      setNotice(showConfirmation ? "Reward reserve balance refreshed." : "");
    } catch (error) {
      setStatus(EMPTY_STATUS);
      setNotice(error instanceof Error ? error.message : "Could not load the reward reserve.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (!copied) return;
    const timeout = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(timeout);
  }, [copied]);

  const parsedAmount = Number(amount);
  const validAmount = Number.isFinite(parsedAmount) && parsedAmount > 0 && parsedAmount <= 1_000_000;
  const isLive = status.mode.toLowerCase() === "live";
  const paymentUri = useMemo(() => {
    if (!isLive || !status.walletAddress || !status.usdcMint || !validAmount) return "";

    const parameters = new URLSearchParams({
      amount: String(parsedAmount),
      label: "StayLongerAI Value Vault",
      message: "Fund the retention reward reserve",
    });
    parameters.set("spl-token", status.usdcMint);
    return `solana:${status.walletAddress}?${parameters.toString()}`;
  }, [isLive, parsedAmount, status.usdcMint, status.walletAddress, validAmount]);

  const handleDemoFunding = async () => {
    if (isLive || !validAmount || isFunding) return;

    setIsFunding(true);
    try {
      const nextStatus = await postJson<FundingStatus & { message?: string }>("/api/rewards/funding/demo", { amount: parsedAmount });
      setStatus({ ...EMPTY_STATUS, ...nextStatus });
      setNotice(nextStatus.message ?? `${parsedAmount} ${status.asset} added to the demo reserve. No wallet transaction was created.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not add demo funds to the reward reserve.");
    } finally {
      setIsFunding(false);
    }
  };

  const handleCopy = async () => {
    if (!status.walletAddress) return;
    try {
      await navigator.clipboard.writeText(status.walletAddress);
      setCopied(true);
      setNotice("Funding address copied.");
    } catch {
      setNotice("Copy was blocked. Select the funding address and copy it manually.");
    }
  };

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
          <motion.button
            type="button"
            onClick={() => navigate("/rewards")}
            whileHover={shouldReduceMotion ? undefined : { x: -2 }}
            whileTap={shouldReduceMotion ? undefined : { scale: 0.985 }}
            className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-slate-600 transition-colors hover:text-slate-950"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Value Vault
          </motion.button>
          <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-teal-700">
            <span className="h-2 w-2 rounded-full bg-teal-600" />
            Reserve management
          </div>
          <h1 className="text-3xl font-bold tracking-[-0.04em] text-slate-950 md:text-[2.15rem]">Add reward funds</h1>
          <p className="mt-2 max-w-xl text-[15px] leading-6 text-slate-600">
            Keep the Value Vault ready for high-confidence customer interventions.
          </p>
        </div>

        <motion.button
          type="button"
          onClick={() => void loadStatus(true)}
          disabled={isLoading}
          whileHover={!shouldReduceMotion && !isLoading ? { y: -1 } : undefined}
          whileTap={!shouldReduceMotion && !isLoading ? { scale: 0.985 } : undefined}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 shadow-sm transition-colors hover:bg-slate-50 disabled:cursor-wait disabled:opacity-60"
        >
          <motion.span
            animate={isLoading && !shouldReduceMotion ? { rotate: 360 } : { rotate: 0 }}
            transition={isLoading && !shouldReduceMotion ? { duration: 0.9, repeat: Infinity, ease: "linear" } : { duration: 0 }}
          >
            <RefreshCw className="h-4 w-4" />
          </motion.span>
          Refresh balance
        </motion.button>
      </header>

      <motion.section
        initial={shouldReduceMotion ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.06 }}
        className={isLive ? "flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3.5 text-sm text-emerald-900" : "flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3.5 text-sm text-amber-900"}
      >
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="font-semibold">{isLive ? "Funding connection is ready." : "Preview mode is active."}</p>
          <p className="mt-0.5 leading-5">{isLive ? "Use the controlled funding flow below to replenish your reward reserve." : "No live reward funding will be sent until a reserve is connected."}</p>
        </div>
      </motion.section>

      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <motion.section
          initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.12 }}
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_8px_24px_rgba(15,23,42,0.05)] sm:p-6"
          aria-labelledby="funding-title"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Controlled contribution</p>
              <h2 id="funding-title" className="mt-1 text-xl font-bold tracking-[-0.025em] text-slate-950">Fund the reward reserve</h2>
              <p className="mt-2 max-w-xl text-sm leading-6 text-slate-600">Choose the value you want ready for upcoming retention actions. Customers never need to take part in this funding step.</p>
            </div>
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
              <WalletCards className="h-5 w-5" />
            </span>
          </div>

          <div className="mt-7">
            <label htmlFor="fund-amount" className="text-sm font-semibold text-slate-900">Contribution amount</label>
            <div className="mt-2 flex flex-col gap-3 sm:flex-row">
              <div className="relative min-w-0 flex-1">
                <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-sm font-semibold text-slate-500">{status.asset}</span>
                <input
                  id="fund-amount"
                  type="number"
                  min="0.01"
                  max="1000000"
                  step="0.01"
                  inputMode="decimal"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white py-3 pl-16 pr-4 text-lg font-bold tabular-nums text-slate-950 outline-none transition focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
                />
              </div>
              {paymentUri ? (
                <motion.a
                  href={paymentUri}
                  whileHover={!shouldReduceMotion ? { y: -1 } : undefined}
                  whileTap={!shouldReduceMotion ? { scale: 0.985 } : undefined}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-teal-700 px-5 py-3 font-semibold text-white shadow-sm transition-colors hover:bg-teal-800"
                >
                  <Zap className="h-4 w-4" /> Open funding app
                </motion.a>
              ) : (
                <motion.button
                  type="button"
                  onClick={() => void handleDemoFunding()}
                  disabled={isLive || !validAmount || isFunding}
                  whileHover={!shouldReduceMotion && !isLive && validAmount && !isFunding ? { y: -1 } : undefined}
                  whileTap={!shouldReduceMotion && !isLive && validAmount && !isFunding ? { scale: 0.985 } : undefined}
                  className={!isLive && validAmount ? "inline-flex items-center justify-center gap-2 rounded-lg bg-teal-700 px-5 py-3 font-semibold text-white shadow-sm transition-colors hover:bg-teal-800 disabled:cursor-wait disabled:bg-teal-700/70" : "inline-flex cursor-not-allowed items-center justify-center gap-2 rounded-lg bg-slate-200 px-5 py-3 font-semibold text-slate-500"}
                >
                  <Zap className="h-4 w-4" /> {isFunding ? "Adding demo funds…" : isLive ? "Funding setup required" : "Add demo funds"}
                </motion.button>
              )}
            </div>
            {!validAmount ? <p role="alert" className="mt-2 text-sm text-rose-700">Enter an amount between 0.01 and 1,000,000 {status.asset}.</p> : null}
            {status.walletAddress && !status.usdcMint ? <p role="alert" className="mt-2 text-sm text-amber-800">A settlement asset still needs to be configured. For safety, this flow will not select a default asset.</p> : null}
            {!isLive ? <p className="mt-2 text-sm text-slate-600">Demo funding updates this local reserve only. No wallet approval or blockchain transaction is created.</p> : null}
            {isLive && !paymentUri ? <p role="alert" className="mt-2 text-sm text-amber-800">A public funding address and USDC mint are required before the approved wallet flow can open.</p> : null}
          </div>

          <div className="mt-7 grid gap-3 border-t border-slate-100 pt-6 sm:grid-cols-3">
            {[
              ["1", "Set value", `Choose the ${status.asset} that should be available for retention.`],
              ["2", "Confirm", "Review the amount in your approved funding app."],
              ["3", "Refresh", "Return here to verify the updated reserve balance."],
            ].map(([step, title, detail], index) => (
              <motion.div
                key={step}
                initial={shouldReduceMotion ? false : { opacity: 0, y: 7 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.22 + index * 0.05 }}
                className="rounded-xl bg-slate-50 p-3.5"
              >
                <p className="text-xs font-bold text-teal-700">{step.padStart(2, "0")}</p>
                <p className="mt-2 text-sm font-semibold text-slate-900">{title}</p>
                <p className="mt-1 text-xs leading-5 text-slate-600">{detail}</p>
              </motion.div>
            ))}
          </div>

          <div className="mt-5 flex items-start gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-3 text-xs leading-5 text-slate-600">
            <LockKeyhole className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" />
            Approval happens only in your funding app. Private credentials are never exposed in StaylongerAI.
          </div>
        </motion.section>

        <motion.aside
          initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...transition, delay: shouldReduceMotion ? 0 : 0.17 }}
          className="rounded-2xl border border-slate-200 bg-white shadow-[0_8px_24px_rgba(15,23,42,0.05)]"
          aria-labelledby="reserve-title"
        >
          <div className="border-b border-slate-100 p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Value Vault reserve</p>
                <h2 id="reserve-title" className="mt-1 text-lg font-bold text-slate-950">Available reward balance</h2>
              </div>
              <span className={status.balanceAvailable ? "mt-1 h-2.5 w-2.5 rounded-full bg-emerald-500" : "mt-1 h-2.5 w-2.5 rounded-full bg-slate-300"} aria-label={status.balanceAvailable ? "Balance available" : "Balance unavailable"} />
            </div>
            <p className="mt-5 text-4xl font-bold tracking-[-0.05em] tabular-nums text-slate-950">{status.usdcBalance === null ? "Unavailable" : `${formatBalance(status.usdcBalance)} ${status.asset}`}</p>
            <p className="mt-2 text-sm text-slate-600">Ready to support customer interventions.</p>
          </div>

          <div className="p-5">
            <details className="group">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-slate-800">
                Technical settlement details
                <Info className="h-4 w-4 text-slate-500 transition-transform group-open:rotate-180" />
              </summary>
              <div className="mt-4 space-y-4 border-t border-slate-100 pt-4 text-sm">
                <div>
                  <p className="text-xs font-medium uppercase tracking-[0.1em] text-slate-500">Settlement network</p>
                  <p className="mt-1 font-semibold text-slate-800">{status.network}</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-[0.1em] text-slate-500">Reserve asset</p>
                    <p className="mt-1 font-semibold text-slate-800">{status.asset}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium uppercase tracking-[0.1em] text-slate-500">Fee balance</p>
                    <p className="mt-1 font-semibold tabular-nums text-slate-800">{formatBalance(status.solBalance, 6)} SOL</p>
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs font-medium uppercase tracking-[0.1em] text-slate-500">Public funding address</p>
                    {status.walletAddress ? (
                      <motion.button
                        type="button"
                        onClick={() => void handleCopy()}
                        aria-label="Copy public funding address"
                        whileTap={shouldReduceMotion ? undefined : { scale: 0.94 }}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                      >
                        {copied ? <Check className="h-4 w-4 text-emerald-700" /> : <Copy className="h-4 w-4" />}
                      </motion.button>
                    ) : null}
                  </div>
                  {status.walletAddress ? <code className="mt-2 block break-all rounded-lg bg-slate-50 px-3 py-2.5 text-xs leading-5 text-slate-700 select-all">{status.walletAddress}</code> : <p className="mt-1 text-sm leading-5 text-slate-600">No public funding address is configured.</p>}
                </div>
                {status.explorerUrl ? (
                  <a href={status.explorerUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-sm font-semibold text-teal-700 hover:text-teal-800">
                    View settlement details <ExternalLink className="h-4 w-4" />
                  </a>
                ) : null}
              </div>
            </details>
          </div>
        </motion.aside>
      </div>

      <p role="status" aria-live="polite" className="min-h-5 text-center text-sm text-slate-600">{notice}</p>
    </motion.div>
  );
}
