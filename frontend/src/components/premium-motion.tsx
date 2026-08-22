import { type ReactNode, useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import type { HTMLMotionProps } from "motion/react";

const premiumEase = [0.22, 1, 0.36, 1] as const;

export const premiumMotion = {
  ease: premiumEase,
  duration: 0.46,
  page: {
    initial: { opacity: 0, y: 12, filter: "blur(5px)" },
    animate: { opacity: 1, y: 0, filter: "blur(0px)" },
    exit: { opacity: 0, y: -7, filter: "blur(3px)" },
  },
  card: {
    initial: { opacity: 0, y: 16 },
    animate: { opacity: 1, y: 0 },
  },
};

type PremiumCardProps = HTMLMotionProps<"div"> & {
  children: ReactNode;
  delay?: number;
  interactive?: boolean;
};

export function PremiumCard({
  children,
  delay = 0,
  interactive = false,
  transition,
  ...props
}: PremiumCardProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={reduceMotion ? false : premiumMotion.card.initial}
      animate={premiumMotion.card.animate}
      whileHover={interactive && !reduceMotion ? { y: -3, scale: 1.005 } : undefined}
      whileTap={interactive && !reduceMotion ? { scale: 0.992 } : undefined}
      transition={
        transition ?? {
          duration: reduceMotion ? 0 : premiumMotion.duration,
          delay: reduceMotion ? 0 : delay,
          ease: premiumMotion.ease,
        }
      }
      {...props}
    >
      {children}
    </motion.div>
  );
}

type StaggerProps = {
  children: ReactNode;
  className?: string;
  delay?: number;
};

export function StaggerGroup({ children, className, delay = 0 }: StaggerProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: {
          transition: {
            delayChildren: reduceMotion ? 0 : delay,
            staggerChildren: reduceMotion ? 0 : 0.07,
          },
        },
      }}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className }: { children: ReactNode; className?: string }) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      variants={{
        hidden: reduceMotion ? { opacity: 1 } : { opacity: 0, y: 14 },
        visible: {
          opacity: 1,
          y: 0,
          transition: { duration: reduceMotion ? 0 : 0.42, ease: premiumMotion.ease },
        },
      }}
    >
      {children}
    </motion.div>
  );
}

type CountUpProps = {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  className?: string;
};

export function CountUp({ value, prefix = "", suffix = "", decimals = 0, className }: CountUpProps) {
  const reduceMotion = useReducedMotion();
  const [displayValue, setDisplayValue] = useState(reduceMotion ? value : 0);
  const previousValue = useRef(0);

  useEffect(() => {
    if (reduceMotion) {
      setDisplayValue(value);
      previousValue.current = value;
      return;
    }

    const startValue = previousValue.current;
    const startTime = performance.now();
    const duration = 720;
    let frameId = 0;

    const tick = (now: number) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(startValue + (value - startValue) * eased);

      if (progress < 1) {
        frameId = requestAnimationFrame(tick);
      } else {
        previousValue.current = value;
      }
    };

    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [reduceMotion, value]);

  return (
    <span className={className}>
      {prefix}
      {new Intl.NumberFormat("en-MY", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }).format(displayValue)}
      {suffix}
    </span>
  );
}
