import { Sparkles } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";

export default function PlaceholderPage({ title }: { title: string }) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="flex min-h-[70vh] items-center justify-center px-2 text-center">
      <motion.section
        className="glass-card max-w-lg p-8 sm:p-10"
        initial={reduceMotion ? false : { opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reduceMotion ? 0 : 0.45, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand/10 text-brand">
          <Sparkles className="h-5 w-5" />
        </div>
        <h1 className="text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">{title}</h1>
        <p className="mx-auto mt-4 max-w-md text-sm leading-6 text-muted-foreground">
          This part of StaylongerAI is being prepared with the same clear, action-focused experience as your
          dashboard.
        </p>
      </motion.section>
    </div>
  );
}
