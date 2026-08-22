import { BellRing, Bot, Check, ChevronRight, LockKeyhole, ShieldCheck, SlidersHorizontal, UsersRound } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { cn } from "../App";

type PreferenceKey = "competitorAlerts" | "vipEscalations" | "weeklyDigest";

type WorkspacePreferences = Record<PreferenceKey, boolean>;

const defaultPreferences: WorkspacePreferences = {
  competitorAlerts: true,
  vipEscalations: true,
  weeklyDigest: false,
};

const preferenceRows: Array<{ key: PreferenceKey; title: string; description: string }> = [
  {
    key: "competitorAlerts",
    title: "Competitor alerts",
    description: "Notify the workspace when a coordinated engagement drop is detected.",
  },
  {
    key: "vipEscalations",
    title: "VIP escalations",
    description: "Surface human-review tasks for high-value accounts immediately.",
  },
  {
    key: "weeklyDigest",
    title: "Weekly executive digest",
    description: "Prepare a weekly retention-impact summary for workspace leaders.",
  },
];

export default function SettingsPage() {
  const shouldReduceMotion = useReducedMotion();
  const [preferences, setPreferences] = useState<WorkspacePreferences>(() => {
    try {
      const stored = window.localStorage.getItem("staylonger-workspace-preferences");
      return stored ? { ...defaultPreferences, ...(JSON.parse(stored) as Partial<WorkspacePreferences>) } : defaultPreferences;
    } catch {
      return defaultPreferences;
    }
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    try {
      window.localStorage.setItem("staylonger-workspace-preferences", JSON.stringify(preferences));
    } catch {
      // Local preferences remain usable for the current session.
    }
  }, [preferences]);

  useEffect(() => {
    if (!saved) return;
    const timer = window.setTimeout(() => setSaved(false), 1800);
    return () => window.clearTimeout(timer);
  }, [saved]);

  const updatePreference = (key: PreferenceKey) => {
    setPreferences((current) => ({ ...current, [key]: !current[key] }));
    setSaved(true);
  };

  const entrance = shouldReduceMotion ? { duration: 0 } : { duration: 0.28, ease: [0.22, 1, 0.36, 1] as const };

  return (
    <motion.div initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={entrance} className="mx-auto flex max-w-5xl flex-col gap-6">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-brand">Workspace controls</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-foreground">Settings</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Tune how your retention workspace keeps the team informed. Preferences are saved in this browser.</p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-800">
          <ShieldCheck className="h-3.5 w-3.5" /> Workspace protected
        </span>
      </header>

      <section className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="glass-card overflow-hidden">
          <div className="flex items-start gap-3 border-b border-border px-5 py-5 sm:px-6">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10 text-brand"><BellRing className="h-5 w-5" /></span>
            <div>
              <h3 className="font-semibold tracking-[-0.02em]">Notifications & escalation</h3>
              <p className="mt-1 text-sm leading-5 text-muted-foreground">Keep the right humans involved when risk needs attention.</p>
            </div>
          </div>
          <div className="divide-y divide-border/80">
            {preferenceRows.map((row) => {
              const enabled = preferences[row.key];
              return (
                <div key={row.key} className="flex items-center gap-4 px-5 py-4 sm:px-6">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">{row.title}</p>
                    <p className="mt-1 text-sm leading-5 text-muted-foreground">{row.description}</p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={enabled}
                    aria-label={`Toggle ${row.title}`}
                    onClick={() => updatePreference(row.key)}
                    className={cn("relative h-6 w-11 shrink-0 rounded-full transition-colors", enabled ? "bg-brand" : "bg-slate-300")}
                  >
                    <motion.span
                      layout
                      transition={{ type: "spring", stiffness: 520, damping: 32 }}
                      className={cn("absolute top-1 h-4 w-4 rounded-full bg-white shadow-sm", enabled ? "left-6" : "left-1")}
                    />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        <div className="space-y-5">
          <section className="glass-card p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700"><Bot className="h-5 w-5" /></span>
              <div>
                <h3 className="font-semibold tracking-[-0.02em]">AI operating mode</h3>
                <p className="mt-1 text-sm text-muted-foreground">Transparent, human-aware automation.</p>
              </div>
            </div>
            <div className="mt-5 rounded-xl border border-emerald-100 bg-emerald-50/70 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-emerald-800"><span className="h-2 w-2 rounded-full bg-emerald-500" /> Active with guardrails</div>
              <p className="mt-2 text-sm leading-5 text-emerald-900/75">The agent can identify risk and prepare recommended interventions; human escalation remains enabled for VIP accounts.</p>
            </div>
          </section>

          <section className="glass-card p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-50 text-sky-700"><UsersRound className="h-5 w-5" /></span>
              <div>
                <h3 className="font-semibold tracking-[-0.02em]">Workspace</h3>
                <p className="mt-1 text-sm text-muted-foreground">StaylongerAI demo workspace</p>
              </div>
            </div>
            <div className="mt-5 flex w-full items-center justify-between rounded-xl border border-border bg-muted/35 px-3.5 py-3 text-sm font-medium text-foreground">
              Team controls available in your connected workspace <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </div>
          </section>
        </div>
      </section>

      <section className="glass-card flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground"><LockKeyhole className="h-5 w-5" /></span>
          <div>
            <h3 className="font-semibold tracking-[-0.02em]">Data & privacy</h3>
            <p className="mt-1 max-w-2xl text-sm leading-5 text-muted-foreground">Sensitive payment credentials and WhatsApp provider secrets stay in backend environment configuration and are never exposed in this workspace.</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-2 text-sm font-medium text-brand"><SlidersHorizontal className="h-4 w-4" /> Local preferences</span>
      </section>

      <span className="sr-only" aria-live="polite">{saved ? "Workspace preference saved." : ""}</span>
      {saved ? <div className="fixed bottom-24 right-4 z-50 flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-medium text-white shadow-xl sm:right-5 lg:bottom-5"><Check className="h-4 w-4 text-emerald-400" /> Preference saved</div> : null}
    </motion.div>
  );
}
