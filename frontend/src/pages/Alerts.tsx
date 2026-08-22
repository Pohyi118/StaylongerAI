import { useState } from "react"
import { motion, useReducedMotion, type Variants } from "motion/react"
import {
  Activity,
  ArrowRight,
  Bell,
  Bot,
  CheckCheck,
  ChevronRight,
  Clock3,
  Crown,
  MessageCircle,
  PhoneCall,
  Send,
  ShieldAlert,
  Sparkles,
  UserRoundPlus,
  Zap,
} from "lucide-react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { cn } from "../App"
import BrandLogo from "../components/BrandLogo"
import { openWhatsApp } from "../whatsapp"

type VipEscalation = {
  name: string
  mrr: string
  risk: string
  issue: string
  reply: string
  lastSignal: string
}

type RescueState = Record<
  string,
  {
    assigned?: boolean
    messageOpened?: boolean
  }
>

const vipEscalations: VipEscalation[] = [
  {
    name: "Acme Corp",
    mrr: "RM12,460",
    risk: "87%",
    issue: "Executive sponsor stopped logging in for 14 days.",
    reply: "Thanks for reaching out. We have been busy with our migration and could use a quick walkthrough.",
    lastSignal: "Executive activity fell 82%",
  },
  {
    name: "Nexus Logistics",
    mrr: "RM8,200",
    risk: "71%",
    issue: "Multiple severe support tickets opened regarding API latency.",
    reply: "The API delay is blocking our dispatch workflow. Please keep us updated on the fix.",
    lastSignal: "3 severe support tickets",
  },
]

const entranceVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 27, mass: 0.85 },
  },
}

const stackVariants: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.09, delayChildren: 0.08 } },
}

function customerMessage(vip: VipEscalation) {
  return `Hi ${vip.name} team, this is Acme Admin. We noticed ${vip.issue.toLowerCase()} We'd like to help - would now be a good time for a quick check-in?`
}

function pageTitle(focus: string | null) {
  if (focus === "competitor") return "Competitor Alert"
  if (focus === "interventions") return "AI Action Center"
  if (focus === "whatsapp") return "WhatsApp Rescue"
  if (focus === "activity") return "Retention Activity"
  return "Alerts & Anomalies"
}

export default function Alerts() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const shouldReduceMotion = useReducedMotion()
  const [activeVipName, setActiveVipName] = useState(vipEscalations[0].name)
  const [rescueState, setRescueState] = useState<RescueState>({})
  const [execNotified, setExecNotified] = useState(false)
  const focus = searchParams.get("focus")
  const activeVip =
    vipEscalations.find((vip) => vip.name === activeVipName) ?? vipEscalations[0]
  const activeRescueState = rescueState[activeVip.name] ?? {}
  const focusedSection =
    focus === "whatsapp"
      ? "WhatsApp rescue"
      : focus === "interventions"
        ? "AI intervention queue"
        : focus === "activity"
          ? "Live activity"
          : focus === "competitor"
            ? "Competitor signal"
            : null

  const handleAction = (route: string) => {
    navigate(route)
  }

  const handleNotifyExecTeam = () => {
    openWhatsApp({
      phone: import.meta.env.VITE_EXEC_WHATSAPP_NUMBER,
      message:
        "Executive Alert: competitor activity is impacting SME retention. Activity has dropped by 37% and 2,391 users are affected. Please review the escalation response immediately.",
    })
    setExecNotified(true)
  }

  const handleAssignCsm = (vip: VipEscalation) => {
    setActiveVipName(vip.name)
    openWhatsApp({
      phone: import.meta.env.VITE_CSM_WHATSAPP_NUMBER,
      message: `CSM assignment request\n\nAccount: ${vip.name}\nRevenue at risk: ${vip.mrr}\nChurn risk: ${vip.risk}\nDiagnosis: ${vip.issue}\n\nPlease assign an owner and confirm the follow-up time.`,
    })
    setRescueState((current) => ({
      ...current,
      [vip.name]: { ...current[vip.name], assigned: true },
    }))
  }

  const handleCallNow = (vip: VipEscalation) => {
    setActiveVipName(vip.name)
    openWhatsApp({
      phone: import.meta.env.VITE_CUSTOMER_WHATSAPP_NUMBER,
      message: customerMessage(vip),
    })
    setRescueState((current) => ({
      ...current,
      [vip.name]: { ...current[vip.name], messageOpened: true },
    }))
  }

  return (
    <motion.div
      initial={shouldReduceMotion ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.42, ease: "easeOut" }}
      className="flex w-full flex-col gap-6"
    >
      <header className="flex flex-col justify-between gap-4 pt-1 xl:flex-row xl:items-end">
        <div>
          <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-teal-700">
            <span className="h-px w-6 bg-teal-500/70" />
            AI retention watch
          </div>
          <h1 className="flex items-center gap-3 text-3xl font-bold tracking-[-0.045em] text-foreground md:text-[2.1rem]">
            <span className="flex size-11 items-center justify-center rounded-2xl border border-teal-200 bg-teal-50 text-teal-700 shadow-[0_8px_24px_rgba(13,148,136,0.12)]">
              <Bell className="size-5" />
            </span>
            {pageTitle(focus)}
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground md:text-base">
            The AI has prioritized the actions most likely to protect revenue right now.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {focusedSection ? (
            <span className="inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-800">
              <Sparkles className="size-3.5" />
              Viewing {focusedSection}
            </span>
          ) : null}
          <span className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800">
            <span className="relative flex size-2">
              <motion.span
                aria-hidden="true"
                className="absolute inline-flex size-full rounded-full bg-amber-400"
                animate={
                  shouldReduceMotion
                    ? { opacity: 0.8 }
                    : { opacity: [0.45, 1, 0.45], scale: [0.92, 1.15, 0.92] }
                }
                transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
              />
              <span className="relative inline-flex size-2 rounded-full bg-amber-500" />
            </span>
            3 items need attention
          </span>
        </div>
      </header>

      <motion.section
        aria-labelledby="competitor-alert-title"
        initial={shouldReduceMotion ? false : { opacity: 0, y: 18, scale: 0.99 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ delay: shouldReduceMotion ? 0 : 0.06, type: "spring", stiffness: 260, damping: 25 }}
        whileHover={shouldReduceMotion ? undefined : { y: -2, boxShadow: "0 20px 50px rgba(185, 28, 28, 0.11)" }}
        className={cn(
          "relative overflow-hidden rounded-[28px] border bg-white p-5 shadow-[0_14px_38px_rgba(15,23,42,0.07)] md:p-7",
          focus === "competitor" ? "border-red-300 ring-4 ring-red-100/70" : "border-red-200/85",
        )}
      >
        <div className="pointer-events-none absolute right-0 top-0 size-44 -translate-y-1/3 translate-x-1/3 rounded-full bg-red-100/65 blur-2xl" />
        <div className="relative z-10 flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between">
          <div className="max-w-3xl">
            <div className="mb-3 flex flex-wrap items-center gap-2.5">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-red-600 px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.12em] text-white shadow-[0_6px_14px_rgba(220,38,38,0.18)]">
                <ShieldAlert className="size-3.5" />
                Priority signal
              </span>
              <span className="text-sm font-semibold text-red-700">Competitor alert</span>
              <span className="hidden h-1 w-1 rounded-full bg-red-300 sm:block" />
              <span className="text-xs text-muted-foreground">First detected 2h ago</span>
            </div>
            <h2 id="competitor-alert-title" className="text-2xl font-semibold tracking-[-0.035em] text-foreground md:text-[1.75rem]">
              A coordinated activity drop is affecting your SME accounts.
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground md:text-base">
              The signal pattern suggests a possible competitor campaign targeting your logistics software segment. The AI has opened a recovery path for the highest-value accounts.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 rounded-[22px] border border-slate-200 bg-slate-50/80 p-3 sm:flex sm:items-center sm:gap-5 sm:p-4">
            <AlertStat label="Affected accounts" value="23" />
            <div className="hidden h-10 w-px bg-slate-200 sm:block" />
            <AlertStat label="Revenue exposed" value="RM84.2K" accent="red" />
            <div className="hidden h-10 w-px bg-slate-200 sm:block" />
            <AlertStat label="AI confidence" value="87%" accent="teal" />
            <motion.button
              type="button"
              onClick={handleNotifyExecTeam}
              whileHover={shouldReduceMotion ? undefined : { y: -2, boxShadow: "0 12px 24px rgba(15,118,110,0.22)" }}
              whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
              className={cn(
                "col-span-2 inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold text-white shadow-[0_7px_16px_rgba(15,118,110,0.17)] transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500/40 focus:ring-offset-2 sm:col-auto",
                execNotified ? "bg-teal-800 hover:bg-teal-900" : "bg-teal-700 hover:bg-teal-800",
              )}
            >
              {execNotified ? <CheckCheck className="size-4" /> : <Bell className="size-4" />}
              {execNotified ? "Executive message opened" : "Notify Exec Team"}
            </motion.button>
          </div>
        </div>
      </motion.section>

      <motion.div
        variants={stackVariants}
        initial={shouldReduceMotion ? false : "hidden"}
        animate="visible"
        className="grid grid-cols-1 gap-6 xl:grid-cols-[1.1fr_0.9fr]"
      >
        <motion.section
          variants={entranceVariants}
          aria-labelledby="action-center-title"
          className={cn(
            "rounded-[26px] border bg-white p-5 shadow-[0_12px_34px_rgba(15,23,42,0.05)] md:p-6",
            focus === "interventions" ? "border-teal-300 ring-4 ring-teal-100/70" : "border-slate-200/85",
          )}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.13em] text-teal-700">
                <Bot className="size-3.5" />
                AI action center
              </div>
              <h2 id="action-center-title" className="mt-2 text-xl font-semibold tracking-[-0.025em] text-foreground">
                What needs attention now
              </h2>
            </div>
            <span className="rounded-full border border-teal-200 bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-800">
              AI prioritized
            </span>
          </div>

          <div className="mt-5 divide-y divide-slate-100 border-y border-slate-100">
            <ActionCenterItem
              icon={<ShieldAlert className="size-4" />}
              title="Competitor alert detected"
              detail="23 accounts affected · RM84.2K revenue exposed"
              tone="red"
              action="Review signal"
              onClick={() => undefined}
            />
            <ActionCenterItem
              icon={<Crown className="size-4" />}
              title="VIP customer needs a human owner"
              detail={`${vipEscalations[0].name} · ${vipEscalations[0].mrr} at risk`}
              tone="teal"
              action="Open rescue"
              onClick={() => setActiveVipName(vipEscalations[0].name)}
            />
            <ActionCenterItem
              icon={<Zap className="size-4" />}
              title="Intervention ready"
              detail="17 Persuadables are ready for an AI recovery flow"
              tone="amber"
              action="View Value Vault"
              onClick={() => handleAction("/rewards")}
            />
            <ActionCenterItem
              icon={<MessageCircle className="size-4" />}
              title="WhatsApp rescue awaiting follow-up"
              detail={`${activeVip.name} · ${activeVip.risk} churn probability`}
              tone="teal"
              action="Preview thread"
              onClick={() => setActiveVipName(activeVip.name)}
            />
          </div>
        </motion.section>

        <motion.section
          variants={entranceVariants}
          aria-labelledby="whatsapp-preview-title"
          className={cn(
            "overflow-hidden rounded-[26px] border bg-white shadow-[0_12px_34px_rgba(15,23,42,0.05)]",
            focus === "whatsapp" ? "border-teal-300 ring-4 ring-teal-100/70" : "border-slate-200/85",
          )}
        >
          <div className="flex items-center justify-between border-b border-slate-200 bg-teal-50/75 px-5 py-4">
            <div className="flex items-center gap-3">
              <span className="flex size-9 items-center justify-center rounded-xl bg-teal-700 text-white shadow-sm">
                <MessageCircle className="size-4" />
              </span>
              <div>
                <h2 id="whatsapp-preview-title" className="font-semibold tracking-[-0.02em] text-foreground">
                  WhatsApp Rescue
                </h2>
                <p className="text-xs text-teal-800">Live intervention preview</p>
              </div>
            </div>
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-800">
              <span className="size-2 rounded-full bg-teal-500" />
              Ready
            </span>
          </div>

          <div className="bg-[#edf4f1] p-4 sm:p-5">
            <div className="flex items-center justify-between gap-3 pb-4">
              <div className="flex gap-2 overflow-x-auto">
                {vipEscalations.map((vip) => (
                  <button
                    key={vip.name}
                    type="button"
                    onClick={() => setActiveVipName(vip.name)}
                    className={cn(
                      "whitespace-nowrap rounded-full border px-2.5 py-1 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500/40",
                      activeVip.name === vip.name
                        ? "border-teal-700 bg-teal-700 text-white"
                        : "border-white bg-white/85 text-slate-600 hover:bg-white",
                    )}
                  >
                    {vip.name}
                  </button>
                ))}
              </div>
              <span className="hidden text-xs text-slate-500 sm:block">Now</span>
            </div>

            <div className="space-y-3">
              <div className="max-w-[88%] rounded-2xl rounded-tl-sm bg-white px-3.5 py-3 text-sm leading-5 text-slate-700 shadow-sm">
                <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.1em] text-teal-700">
                  <BrandLogo alt="" className="size-3 rounded-[3px]" />
                  StaylongerAI
                </div>
                {customerMessage(activeVip)}
              </div>
              <div className="ml-auto max-w-[88%] rounded-2xl rounded-tr-sm bg-teal-700 px-3.5 py-3 text-sm leading-5 text-white shadow-sm">
                {activeVip.reply}
                <div className="mt-1.5 flex items-center justify-end gap-1 text-[10px] text-teal-100">
                  <CheckCheck className="size-3" />
                  delivered
                </div>
              </div>
              <div className="max-w-[88%] rounded-2xl rounded-tl-sm border border-teal-100 bg-teal-50 px-3.5 py-3 text-sm leading-5 text-slate-700">
                <span className="font-semibold text-teal-800">AI next step: </span>
                {activeRescueState.assigned
                  ? "A CSM handoff has been opened. Keep the recovery conversation warm in WhatsApp."
                  : "Offer a guided recovery path and confirm the best time for a human follow-up."}
              </div>
            </div>
          </div>

          <div className="grid gap-3 p-4 sm:grid-cols-2">
            <motion.button
              type="button"
              onClick={() => handleAssignCsm(activeVip)}
              whileHover={shouldReduceMotion ? undefined : { y: -1 }}
              whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-900 px-3 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500/40"
            >
              {activeRescueState.assigned ? <CheckCheck className="size-4" /> : <UserRoundPlus className="size-4" />}
              {activeRescueState.assigned ? "CSM handoff opened" : "Assign CSM"}
            </motion.button>
            <motion.button
              type="button"
              onClick={() => handleCallNow(activeVip)}
              whileHover={shouldReduceMotion ? undefined : { y: -1 }}
              whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-teal-200 bg-white px-3 py-2.5 text-sm font-semibold text-teal-800 transition-colors hover:bg-teal-50 focus:outline-none focus:ring-2 focus:ring-teal-500/40"
            >
              {activeRescueState.messageOpened ? <Send className="size-4" /> : <PhoneCall className="size-4" />}
              {activeRescueState.messageOpened ? "Re-open WhatsApp" : "Call now"}
            </motion.button>
          </div>
        </motion.section>
      </motion.div>

      <motion.div
        variants={stackVariants}
        initial={shouldReduceMotion ? false : "hidden"}
        animate="visible"
        className="grid grid-cols-1 gap-6 lg:grid-cols-[1.15fr_0.85fr]"
      >
        <motion.section variants={entranceVariants} aria-labelledby="vip-escalations-title">
          <div className="mb-4 flex items-center justify-between px-1">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.13em] text-teal-700">
                <Crown className="size-3.5" />
                Human attention
              </div>
              <h2 id="vip-escalations-title" className="mt-1 text-lg font-semibold tracking-[-0.02em] text-foreground">
                VIP risk alerts
              </h2>
            </div>
            <span className="rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700">
              {vipEscalations.length} action required
            </span>
          </div>

          <div className="grid gap-3">
            {vipEscalations.map((vip) => {
              const current = rescueState[vip.name] ?? {}
              return (
                <motion.article
                  key={vip.name}
                  variants={entranceVariants}
                  whileHover={shouldReduceMotion ? undefined : { y: -2, boxShadow: "0 18px 38px rgba(15, 23, 42, 0.09)" }}
                  className={cn(
                    "rounded-[24px] border bg-white p-5 shadow-[0_10px_28px_rgba(15,23,42,0.045)] transition-colors",
                    activeVip.name === vip.name ? "border-teal-300" : "border-slate-200/85 hover:border-teal-200",
                  )}
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <button
                      type="button"
                      onClick={() => setActiveVipName(vip.name)}
                      className="text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/40"
                    >
                      <div className="flex items-center gap-2">
                        <span className="flex size-9 items-center justify-center rounded-xl border border-teal-200 bg-teal-50 text-teal-700">
                          <Crown className="size-4" />
                        </span>
                        <div>
                          <h3 className="font-semibold text-foreground">{vip.name}</h3>
                          <p className="mt-0.5 text-xs text-muted-foreground">{vip.lastSignal}</p>
                        </div>
                      </div>
                    </button>
                    <div className="flex items-center gap-2 sm:text-right">
                      <span className="rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700">
                        {vip.risk} risk
                      </span>
                      <span className="text-sm font-semibold tabular-nums text-foreground">{vip.mrr}</span>
                    </div>
                  </div>

                  <p className="mt-4 rounded-2xl border border-slate-100 bg-slate-50 px-3.5 py-3 text-sm leading-6 text-slate-600">
                    <span className="font-semibold text-slate-800">AI diagnosis: </span>
                    {vip.issue}
                  </p>

                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <motion.button
                      type="button"
                      onClick={() => handleAssignCsm(vip)}
                      whileHover={shouldReduceMotion ? undefined : { y: -1 }}
                      whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
                      className="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-900 px-3 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500/40"
                    >
                      {current.assigned ? <CheckCheck className="size-4" /> : <UserRoundPlus className="size-4" />}
                      {current.assigned ? "CSM handoff" : "Assign CSM"}
                    </motion.button>
                    <motion.button
                      type="button"
                      onClick={() => handleCallNow(vip)}
                      whileHover={shouldReduceMotion ? undefined : { y: -1 }}
                      whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
                      className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-teal-50 focus:outline-none focus:ring-2 focus:ring-teal-500/40"
                    >
                      <PhoneCall className="size-4 text-teal-700" />
                      Call Now
                    </motion.button>
                  </div>
                </motion.article>
              )
            })}
          </div>
        </motion.section>

        <motion.section
          variants={entranceVariants}
          aria-labelledby="activity-title"
          className={cn(
            "rounded-[26px] border bg-white p-5 shadow-[0_10px_28px_rgba(15,23,42,0.045)] md:p-6",
            focus === "activity" ? "border-teal-300 ring-4 ring-teal-100/70" : "border-slate-200/85",
          )}
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.13em] text-teal-700">
                <Activity className="size-3.5" />
                Live activity
              </div>
              <h2 id="activity-title" className="mt-1 text-lg font-semibold tracking-[-0.02em] text-foreground">
                Retention timeline
              </h2>
            </div>
            <Clock3 className="size-5 text-slate-400" />
          </div>

          <ol className="mt-6 space-y-5">
            <TimelineItem
              title="Competitor pattern confidence increased"
              detail="The account cohort now matches a coordinated usage decline."
              time="2h ago"
              tone="red"
            />
            <TimelineItem
              title="VIP recovery queue refreshed"
              detail="Two high-value accounts are waiting for a human decision."
              time="48m ago"
              tone="teal"
            />
            <TimelineItem
              title="Value Vault intervention prepared"
              detail="Eligible persuadables can be routed into a re-engagement offer."
              time="12m ago"
              tone="amber"
            />
          </ol>

          <motion.button
            type="button"
            onClick={() => handleAction("/rewards")}
            whileHover={shouldReduceMotion ? undefined : { x: 2 }}
            whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
            className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500/40 focus:ring-offset-2"
          >
            Generate Value Vault interventions
            <ArrowRight className="size-3.5" />
          </motion.button>
        </motion.section>
      </motion.div>
    </motion.div>
  )
}

function AlertStat({
  label,
  value,
  accent = "default",
}: {
  label: string
  value: string
  accent?: "default" | "red" | "teal"
}) {
  const valueClass =
    accent === "red"
      ? "text-red-700"
      : accent === "teal"
        ? "text-teal-700"
        : "text-foreground"

  return (
    <div className="min-w-[5.25rem]">
      <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">{label}</div>
      <div className={cn("mt-1 text-xl font-bold tracking-[-0.04em]", valueClass)}>{value}</div>
    </div>
  )
}

function ActionCenterItem({
  icon,
  title,
  detail,
  tone,
  action,
  onClick,
}: {
  icon: React.ReactNode
  title: string
  detail: string
  tone: "teal" | "amber" | "red"
  action: string
  onClick: () => void
}) {
  const tones = {
    teal: "border-teal-100 bg-teal-50 text-teal-700",
    amber: "border-amber-100 bg-amber-50 text-amber-700",
    red: "border-red-100 bg-red-50 text-red-700",
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full items-center gap-3 px-1 py-4 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/40"
    >
      <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-xl border", tones[tone])}>{icon}</span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-semibold text-foreground">{title}</span>
        <span className="mt-0.5 block truncate text-xs text-muted-foreground">{detail}</span>
      </span>
      <span className="inline-flex shrink-0 items-center gap-1 text-xs font-semibold text-teal-800">
        <span className="hidden sm:inline">{action}</span>
        <ChevronRight className="size-4 transition-transform group-hover:translate-x-0.5" />
      </span>
    </button>
  )
}

function TimelineItem({
  title,
  detail,
  time,
  tone,
}: {
  title: string
  detail: string
  time: string
  tone: "teal" | "amber" | "red"
}) {
  const dotTone = {
    teal: "bg-teal-500 ring-teal-100",
    amber: "bg-amber-500 ring-amber-100",
    red: "bg-red-500 ring-red-100",
  }

  return (
    <li className="relative flex gap-3 pl-1">
      <span className={cn("mt-1.5 size-2.5 shrink-0 rounded-full ring-4", dotTone[tone])} />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
          <p className="text-sm font-semibold text-foreground">{title}</p>
          <span className="text-xs text-muted-foreground">{time}</span>
        </div>
        <p className="mt-1 text-sm leading-5 text-muted-foreground">{detail}</p>
      </div>
    </li>
  )
}
