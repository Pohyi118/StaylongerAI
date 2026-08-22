import { useState } from "react";
import { ArrowRight, CheckCircle2, Gift, LockKeyhole, MessageCircle, ShieldCheck, Sparkles } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useSearchParams } from "react-router-dom";
import BrandLogo from "../components/BrandLogo";
import { postJson } from "../lib/api";

type ClaimResponse = {
  status: string;
  amount: number;
  message: string;
  demo: boolean;
};

const motionEase = [0.22, 1, 0.36, 1] as const;

export default function RewardClaim() {
  const [searchParams] = useSearchParams();
  const shouldReduceMotion = useReducedMotion();
  const [claimResult, setClaimResult] = useState<ClaimResponse | null>(null);
  const [isClaiming, setIsClaiming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const token = searchParams.get("token");
  const rewardAmount = claimResult?.amount ?? 50;
  const transition = { duration: shouldReduceMotion ? 0 : 0.42, ease: motionEase };

  const handleClaim = async () => {
    if (isClaiming || claimResult) return;

    setError(null);

    if (!token) {
      setClaimResult({
        status: "demo",
        amount: 50,
        message: "Return to WhatsApp and send a photo of your inventory to continue onboarding.",
        demo: true,
      });
      return;
    }

    setIsClaiming(true);

    try {
      const result = await postJson<ClaimResponse>("/api/rewards/claim", { token });
      setClaimResult(result);
    } catch (claimError) {
      setError(claimError instanceof Error ? claimError.message : "We could not confirm this reward. Please try again.");
    } finally {
      setIsClaiming(false);
    }
  };

  return (
    <div className="relative flex min-h-[calc(100vh-7rem)] items-center justify-center overflow-hidden px-1 py-8 sm:px-6">
      <motion.div
        aria-hidden="true"
        className="pointer-events-none absolute -right-20 top-12 h-72 w-72 rounded-full bg-teal-100/70 blur-3xl"
        animate={shouldReduceMotion ? { opacity: 0.45 } : { opacity: [0.28, 0.56, 0.28], scale: [0.94, 1.05, 0.94] }}
        transition={shouldReduceMotion ? { duration: 0 } : { duration: 7, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        initial={shouldReduceMotion ? false : { opacity: 0, y: 18, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={transition}
        className="relative grid w-full max-w-4xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_24px_70px_-36px_rgba(15,23,42,0.28)] md:grid-cols-[0.9fr_1.1fr]"
      >
        <section className="border-b border-slate-200 bg-slate-950 p-7 text-white md:border-b-0 md:border-r md:p-9">
          <BrandLogo alt="" className="h-10 w-10 rounded-xl ring-1 ring-white/25 shadow-[0_12px_22px_-12px_rgba(45,212,191,0.8)]" />
          <p className="mt-8 text-xs font-semibold uppercase tracking-[0.16em] text-teal-300">StaylongerAI Value Vault</p>
          <h1 className="mt-3 text-3xl font-bold tracking-[-0.045em]">A small thank you, timed to help.</h1>
          <p className="mt-4 text-sm leading-6 text-slate-300">Your team prepared this reward as part of a personalized support plan.</p>

          <div className="mt-8 space-y-4 border-t border-white/10 pt-6 text-sm">
            <div className="flex gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/10 text-teal-300"><Gift className="h-4 w-4" /></span>
              <div><p className="font-semibold text-white">Personalized value</p><p className="mt-1 leading-5 text-slate-300">Reward options are chosen for your specific situation.</p></div>
            </div>
            <div className="flex gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/10 text-teal-300"><ShieldCheck className="h-4 w-4" /></span>
              <div><p className="font-semibold text-white">Simple and secure</p><p className="mt-1 leading-5 text-slate-300">No sensitive payment details are needed to claim this reward.</p></div>
            </div>
          </div>
        </section>

        <section className="flex min-h-[440px] items-center p-6 text-center sm:p-9">
          <AnimatePresence mode="wait">
            {!claimResult ? (
              isClaiming ? (
                <motion.div
                  key="processing"
                  initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={shouldReduceMotion ? undefined : { opacity: 0, y: -8 }}
                  transition={transition}
                  className="w-full"
                  aria-live="polite"
                >
                  <div className="relative mx-auto flex h-20 w-20 items-center justify-center">
                    <motion.span
                      className="absolute inset-0 rounded-full border border-teal-200"
                      animate={shouldReduceMotion ? { scale: 1, opacity: 0.6 } : { scale: [0.78, 1.14, 0.78], opacity: [0.25, 0.85, 0.25] }}
                      transition={shouldReduceMotion ? { duration: 0 } : { duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
                    />
                    <motion.span
                      className="absolute inset-2 rounded-full border-2 border-slate-100 border-t-teal-600"
                      animate={shouldReduceMotion ? { rotate: 0 } : { rotate: 360 }}
                      transition={shouldReduceMotion ? { duration: 0 } : { duration: 1.05, repeat: Infinity, ease: "linear" }}
                    />
                    <Gift className="relative h-7 w-7 text-teal-700" />
                  </div>
                  <p className="mt-8 text-xs font-semibold uppercase tracking-[0.16em] text-teal-700">Confirming reward</p>
                  <h2 className="mt-3 text-2xl font-bold tracking-[-0.035em] text-slate-950">Preparing your reward</h2>
                  <p className="mx-auto mt-3 max-w-sm text-sm leading-6 text-slate-600">We are confirming this reward session securely. This will only take a moment.</p>
                </motion.div>
              ) : (
                <motion.div
                  key="offer"
                  initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={shouldReduceMotion ? undefined : { opacity: 0, y: -8 }}
                  transition={transition}
                  className="w-full"
                >
                  <motion.div
                    className="relative mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-teal-50 text-teal-700"
                    animate={shouldReduceMotion ? { y: 0 } : { y: [0, -3, 0] }}
                    transition={shouldReduceMotion ? { duration: 0 } : { duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
                  >
                    <Gift className="h-8 w-8" />
                    <Sparkles className="absolute -right-2 -top-2 h-4 w-4 text-amber-500" />
                  </motion.div>
                  <p className="mt-7 text-xs font-semibold uppercase tracking-[0.16em] text-teal-700">Value Vault reward</p>
                  <h2 className="mt-3 text-4xl font-bold tracking-[-0.055em] text-slate-950">RM{rewardAmount}</h2>
                  <p className="mx-auto mt-3 max-w-sm text-[15px] leading-6 text-slate-600">A personalized retention reward is ready for you to claim.</p>

                  <motion.button
                    type="button"
                    onClick={() => void handleClaim()}
                    whileHover={shouldReduceMotion ? undefined : { y: -1 }}
                    whileTap={shouldReduceMotion ? undefined : { scale: 0.985 }}
                    className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-teal-700 px-5 py-3.5 font-semibold text-white shadow-sm transition-colors hover:bg-teal-800"
                  >
                    Claim reward <ArrowRight className="h-4 w-4" />
                  </motion.button>

                  {error ? <p role="alert" className="mt-4 text-sm text-rose-700">{error}</p> : null}

                  <div className="mt-5 flex items-center justify-center gap-2 text-xs text-slate-500">
                    <LockKeyhole className="h-3.5 w-3.5" />
                    {token ? "Secure reward session" : "Demo preview"}
                  </div>
                </motion.div>
              )
            ) : (
              <motion.div
                key="success"
                initial={shouldReduceMotion ? false : { opacity: 0, y: 12, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={transition}
                className="w-full"
                aria-live="polite"
              >
                <motion.div
                  className="relative mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-emerald-50 text-emerald-700"
                  initial={shouldReduceMotion ? false : { scale: 0.7 }}
                  animate={{ scale: 1 }}
                  transition={shouldReduceMotion ? { duration: 0 } : { type: "spring", stiffness: 260, damping: 18 }}
                >
                  <CheckCircle2 className="h-10 w-10" />
                </motion.div>
                <p className="mt-7 text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">Reward confirmed</p>
                <h2 className="mt-3 text-3xl font-bold tracking-[-0.045em] text-slate-950">RM{rewardAmount} is ready</h2>
                <p className="mx-auto mt-3 max-w-sm text-[15px] leading-6 text-slate-600">{claimResult.message || "Return to WhatsApp and send a photo of your inventory to continue onboarding."}</p>
                <div className="mt-7 rounded-xl border border-slate-200 bg-slate-50 p-4 text-left">
                  <div className="flex gap-3">
                    <MessageCircle className="mt-0.5 h-5 w-5 shrink-0 text-teal-700" />
                    <div><p className="text-sm font-semibold text-slate-900">What happens next</p><p className="mt-1 text-sm leading-5 text-slate-600">Continue the conversation in WhatsApp. Your support plan will guide the next step.</p></div>
                  </div>
                </div>
                {claimResult.demo ? <p className="mt-5 text-xs leading-5 text-amber-800">This is a demo preview. No live reward payment was required.</p> : null}
              </motion.div>
            )}
          </AnimatePresence>
        </section>
      </motion.div>
    </div>
  );
}
