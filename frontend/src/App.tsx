import * as Dialog from "@radix-ui/react-dialog";
import { Command } from "cmdk";
import { clsx, type ClassValue } from "clsx";
import { lazy, Suspense, useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  Bell,
  BrainCircuit,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Gift,
  Home,
  Menu,
  MessageCircle,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Settings,
  ShieldAlert,
  Users,
  WandSparkles,
  type LucideIcon,
} from "lucide-react";
import { AnimatePresence, MotionConfig, motion, useReducedMotion } from "motion/react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { BrowserRouter } from "react-router-dom";
import { twMerge } from "tailwind-merge";
import BrandLogo from "./components/BrandLogo";
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Customers = lazy(() => import("./pages/Customers"));
const Alerts = lazy(() => import("./pages/Alerts"));
const Rewards = lazy(() => import("./pages/Rewards"));
const RewardClaim = lazy(() => import("./pages/RewardClaim"));
const Reports = lazy(() => import("./pages/Reports"));
const Funds = lazy(() => import("./pages/Funds"));
const SettingsPage = lazy(() => import("./pages/Settings"));

type NavigationItem = {
  to: string;
  icon: LucideIcon;
  label: string;
  description: string;
};

const primaryNavigation: NavigationItem[] = [
  { to: "/", icon: Home, label: "Dashboard", description: "Command center" },
  { to: "/customers", icon: Users, label: "Customers", description: "Customer intelligence" },
  { to: "/customers?focus=triage", icon: BrainCircuit, label: "AI Triage", description: "Customer segments" },
  { to: "/alerts?focus=competitor", icon: ShieldAlert, label: "Competitor Alerts", description: "Market signals" },
  { to: "/alerts?focus=interventions", icon: WandSparkles, label: "Interventions", description: "Retention actions" },
  { to: "/rewards", icon: Gift, label: "Value Vault", description: "Reward reserve" },
  { to: "/alerts?focus=whatsapp", icon: MessageCircle, label: "WhatsApp", description: "Rescue conversations" },
  { to: "/reports", icon: BarChart3, label: "Analytics", description: "Retention performance" },
  { to: "/alerts?focus=activity", icon: Activity, label: "Activity", description: "Agent activity" },
];

const secondaryNavigation: NavigationItem[] = [
  { to: "/settings", icon: Settings, label: "Settings", description: "Workspace preferences" },
];

const mobileNavigation: NavigationItem[] = [
  { to: "/", icon: Home, label: "Home", description: "Dashboard" },
  { to: "/customers", icon: Users, label: "Customers", description: "Customer intelligence" },
  { to: "/alerts", icon: ShieldAlert, label: "Actions", description: "AI action center" },
  { to: "/rewards", icon: Gift, label: "Vault", description: "Reward reserve" },
  { to: "/reports", icon: BarChart3, label: "Reports", description: "Analytics" },
];

const pageMeta: Record<string, { title: string; eyebrow: string }> = {
  "/": { title: "Dashboard", eyebrow: "Retention command center" },
  "/customers": { title: "Customers", eyebrow: "Customer intelligence" },
  "/alerts": { title: "AI action center", eyebrow: "Autonomous retention" },
  "/rewards": { title: "Value Vault", eyebrow: "Reward reserve" },
  "/rewards/funds": { title: "Add reward funds", eyebrow: "Value Vault" },
  "/reward": { title: "Reward claim", eyebrow: "Value Vault" },
  "/reports": { title: "Analytics", eyebrow: "Retention performance" },
  "/settings": { title: "Settings", eyebrow: "Workspace preferences" },
};

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </MotionConfig>
  );
}

function AppShell() {
  const [collapsed, setCollapsed] = useLocalBoolean("staylonger-sidebar-collapsed", false);
  const [commandOpen, setCommandOpen] = useState(false);
  const location = useLocation();
  const reduceMotion = useReducedMotion();
  const meta = pageMeta[location.pathname] ?? pageMeta["/"];

  return (
    <div className="command-center-shell min-h-screen bg-background text-foreground antialiased">
      <DesktopSidebar collapsed={collapsed} onCollapsedChange={setCollapsed} />

      <div
        className={cn(
          "min-h-screen transition-[padding] duration-200 lg:pl-[252px]",
          collapsed && "lg:pl-[92px]",
        )}
      >
        <TopBar meta={meta} onOpenCommand={() => setCommandOpen(true)} />
        <main id="main-content" className="mobile-main-content mx-auto w-full max-w-[1640px] px-4 pb-10 pt-5 sm:px-6 lg:px-8 lg:pt-7">
          <AnimatePresence mode="wait" initial={!reduceMotion}>
            <motion.div
              key={`${location.pathname}${location.search}`}
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? undefined : { opacity: 0, y: -5 }}
              transition={{ duration: reduceMotion ? 0 : 0.24, ease: [0.22, 1, 0.36, 1] }}
            >
              <Suspense fallback={<PageLoading />}>
                <Routes location={location}>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/customers" element={<Customers />} />
                  <Route path="/alerts" element={<Alerts />} />
                  <Route path="/rewards" element={<Rewards />} />
                  <Route path="/rewards/funds" element={<Funds />} />
                  <Route path="/reward" element={<RewardClaim />} />
                  <Route path="/reports" element={<Reports />} />
                  <Route path="/settings" element={<SettingsPage />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </Suspense>
            </motion.div>
          </AnimatePresence>
        </main>
        <MobileBottomNavigation />
      </div>

      <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} />
    </div>
  );
}

function PageLoading() {
  return (
    <div className="grid gap-5" aria-label="Loading page" aria-busy="true">
      <div className="h-7 w-44 animate-pulse rounded-md bg-slate-200" />
      <div className="grid gap-4 md:grid-cols-3">
        <div className="h-32 animate-pulse rounded-2xl border border-border bg-white" />
        <div className="h-32 animate-pulse rounded-2xl border border-border bg-white" />
        <div className="h-32 animate-pulse rounded-2xl border border-border bg-white" />
      </div>
      <div className="h-80 animate-pulse rounded-2xl border border-border bg-white" />
    </div>
  );
}

function useLocalBoolean(key: string, fallback: boolean) {
  const [value, setValue] = useState(() => {
    try {
      const stored = window.localStorage.getItem(key);
      return stored === null ? fallback : stored === "true";
    } catch {
      return fallback;
    }
  });

  const updateValue = (next: boolean) => {
    setValue(next);
    try {
      window.localStorage.setItem(key, String(next));
    } catch {
      // The shell still works when storage is unavailable.
    }
  };

  return [value, updateValue] as const;
}

function DesktopSidebar({
  collapsed,
  onCollapsedChange,
}: {
  collapsed: boolean;
  onCollapsedChange: (collapsed: boolean) => void;
}) {
  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-40 hidden border-r border-border/80 bg-white/95 px-3 py-4 backdrop-blur lg:flex lg:flex-col",
        "transition-[width] duration-200",
        collapsed ? "w-[92px]" : "w-[252px]",
      )}
    >
      <div className={cn("flex h-11 items-center", collapsed ? "justify-center" : "justify-between px-1")}>
        <Link to="/" aria-label="StaylongerAI dashboard" className="flex min-w-0 items-center gap-3">
          <BrandLogo alt="" className="h-9 w-9 shrink-0 rounded-xl shadow-[0_8px_18px_-10px_rgba(14,116,144,0.5)]" />
          {!collapsed ? (
            <span className="truncate text-[15px] font-semibold tracking-[-0.025em] text-foreground">StaylongerAI</span>
          ) : null}
        </Link>
        {!collapsed ? (
          <button
            type="button"
            onClick={() => onCollapsedChange(true)}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose className="h-4 w-4" />
          </button>
        ) : null}
      </div>

      {collapsed ? (
        <button
          type="button"
          onClick={() => onCollapsedChange(false)}
          className="mt-5 flex h-9 w-full items-center justify-center rounded-lg border border-border text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          aria-label="Expand sidebar"
        >
          <PanelLeftOpen className="h-4 w-4" />
        </button>
      ) : null}

      <nav aria-label="Main navigation" className="mt-7 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {!collapsed ? <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Workspace</p> : null}
        <NavigationList items={primaryNavigation} collapsed={collapsed} />
        <div className="my-4 h-px bg-border/70" />
        <NavigationList items={secondaryNavigation} collapsed={collapsed} />
      </nav>

      <div className="mt-4 space-y-1 border-t border-border/70 pt-4">
        <Link
          to="/settings"
          className={cn(
            "flex items-center rounded-xl px-2.5 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
            collapsed ? "justify-center" : "gap-3",
          )}
          title={collapsed ? "Product help" : undefined}
        >
          <CircleHelp className="h-[18px] w-[18px] shrink-0" />
          {!collapsed ? <span>Product help</span> : null}
        </Link>
        <Link
          to="/settings"
          className={cn(
            "flex items-center rounded-xl px-2.5 py-2 transition-colors hover:bg-muted",
            collapsed ? "justify-center" : "gap-3",
          )}
          title={collapsed ? "Staylonger workspace" : undefined}
        >
          <BrandLogo alt="" className="h-8 w-8 shrink-0 rounded-lg shadow-sm" />
          {!collapsed ? (
            <span className="min-w-0">
              <span className="block truncate text-sm font-medium text-foreground">Staylonger workspace</span>
              <span className="block truncate text-xs text-muted-foreground">Admin account</span>
            </span>
          ) : null}
        </Link>
      </div>
    </aside>
  );
}

function NavigationList({ items, collapsed, onNavigate }: { items: NavigationItem[]; collapsed: boolean; onNavigate?: () => void }) {
  const location = useLocation();

  return (
    <>
      {items.map((item) => {
        const [path, query] = item.to.split("?");
        const isActive = location.pathname === path && (!query || location.search.includes(query));
        const Icon = item.icon;

        return (
          <Link
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            title={collapsed ? item.label : undefined}
            className={cn(
              "group relative flex items-center rounded-xl px-2.5 py-2 text-sm transition-colors",
              collapsed ? "justify-center" : "gap-3",
              isActive ? "bg-brand/10 font-semibold text-brand" : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={isActive ? 2.2 : 1.9} />
            {!collapsed ? <span className="truncate">{item.label}</span> : null}
            {isActive && !collapsed ? <span className="ml-auto h-1.5 w-1.5 rounded-full bg-brand" /> : null}
          </Link>
        );
      })}
    </>
  );
}

function TopBar({ meta, onOpenCommand }: { meta: { title: string; eyebrow: string }; onOpenCommand: () => void }) {
  return (
    <header className="sticky top-0 z-30 border-b border-border/70 bg-background/92 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-[1640px] items-center gap-2 px-3 sm:h-[68px] sm:gap-3 sm:px-6 lg:px-8">
        <MobileNavigation />
        <div className="min-w-0 flex-1">
          <p className="hidden text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground sm:block">{meta.eyebrow}</p>
          <h1 className="truncate text-lg font-semibold tracking-[-0.025em] text-foreground sm:mt-0.5">{meta.title}</h1>
        </div>

        <button
          type="button"
          onClick={onOpenCommand}
          className="hidden h-9 w-[min(30vw,272px)] items-center gap-2 rounded-lg border border-border bg-white px-3 text-left text-sm text-muted-foreground shadow-sm transition-colors hover:border-brand/30 hover:text-foreground md:flex"
          aria-label="Open command palette"
        >
          <Search className="h-4 w-4" />
          <span className="flex-1">Search or jump to…</span>
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-medium">⌘ K</kbd>
        </button>

        <div className="hidden items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs font-medium text-emerald-800 sm:flex">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-600" />
          </span>
          AI Agent active
        </div>

        <button
          type="button"
          onClick={onOpenCommand}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-white text-muted-foreground shadow-sm transition-colors hover:text-foreground max-[420px]:hidden md:hidden"
          aria-label="Search or open command palette"
        >
          <Search className="h-4 w-4" />
        </button>
        <Link
          to="/alerts?focus=activity"
          className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-white text-muted-foreground shadow-sm transition-colors hover:text-foreground"
          aria-label="View notifications and activity"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-rose-500 ring-2 ring-white" />
        </Link>
        <Link
          to="/settings"
          className="flex h-9 w-9 items-center justify-center rounded-xl shadow-sm"
          aria-label="Open workspace settings"
        >
          <BrandLogo alt="" className="h-9 w-9 rounded-xl" />
        </Link>
      </div>
    </header>
  );
}

function MobileBottomNavigation() {
  const location = useLocation();

  return (
    <nav
      aria-label="Quick navigation"
      className="mobile-bottom-navigation fixed inset-x-0 bottom-0 z-40 border-t border-border/80 bg-white/95 px-1.5 pt-2 shadow-[0_-10px_28px_-20px_rgba(15,23,42,0.45)] backdrop-blur lg:hidden"
    >
      <div className="mx-auto grid w-full max-w-lg grid-cols-5">
        {mobileNavigation.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.to === "/rewards"
              ? ["/rewards", "/rewards/funds", "/reward"].includes(location.pathname)
              : location.pathname === item.to;

          return (
            <Link
              key={item.to}
              to={item.to}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "relative flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl px-1 py-1 text-[10px] font-medium transition-colors",
                isActive ? "text-brand" : "text-muted-foreground hover:text-foreground",
              )}
            >
              <span
                className={cn(
                  "flex h-7 w-9 items-center justify-center rounded-lg transition-colors",
                  isActive ? "bg-brand/10" : "bg-transparent",
                )}
              >
                <Icon className="h-[18px] w-[18px]" strokeWidth={isActive ? 2.3 : 1.9} />
              </span>
              <span className="truncate leading-none">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

function MobileNavigation() {
  const [open, setOpen] = useState(false);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-white text-muted-foreground shadow-sm lg:hidden"
          aria-label="Open navigation"
        >
          <Menu className="h-4 w-4" />
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/28 backdrop-blur-[1px] lg:hidden" />
        <Dialog.Content className="fixed inset-y-0 left-0 z-50 flex w-[min(85vw,320px)] flex-col border-r border-border bg-white p-4 shadow-2xl lg:hidden">
          <Dialog.Title className="sr-only">StaylongerAI navigation</Dialog.Title>
          <div className="flex h-10 items-center justify-between">
            <Link to="/" onClick={() => setOpen(false)} className="flex items-center gap-3">
              <BrandLogo alt="" className="h-9 w-9 shrink-0 rounded-xl shadow-sm" />
              <span className="text-[15px] font-semibold tracking-[-0.025em]">StaylongerAI</span>
            </Link>
            <Dialog.Close asChild>
              <button type="button" className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted" aria-label="Close navigation">
                <ChevronLeft className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>
          <nav aria-label="Main navigation" className="mt-7 flex-1 overflow-y-auto">
            <NavigationList items={primaryNavigation} collapsed={false} onNavigate={() => setOpen(false)} />
            <div className="my-4 h-px bg-border/70" />
            <NavigationList items={secondaryNavigation} collapsed={false} onNavigate={() => setOpen(false)} />
          </nav>
          <div className="rounded-xl bg-muted px-3 py-3 text-xs leading-5 text-muted-foreground">
            Stay ahead of churn with transparent AI recommendations.
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onOpenChange, open]);

  const selectItem = (item: NavigationItem) => {
    navigate(item.to);
    onOpenChange(false);
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/28 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-[18vh] z-50 w-[min(calc(100vw-2rem),620px)] -translate-x-1/2 overflow-hidden rounded-2xl border border-border bg-white shadow-[0_28px_90px_rgba(15,23,42,0.22)]">
          <Dialog.Title className="sr-only">Command palette</Dialog.Title>
          <Command label="StaylongerAI command palette" className="overflow-hidden">
            <div className="flex items-center gap-3 border-b border-border px-4">
              <Search className="h-4 w-4 text-muted-foreground" />
              <Command.Input className="h-13 w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground" placeholder="Search pages and actions…" />
              <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">ESC</kbd>
            </div>
            <Command.List className="max-h-[min(52vh,360px)] overflow-y-auto p-2">
              <Command.Empty className="px-3 py-8 text-center text-sm text-muted-foreground">No matching command.</Command.Empty>
              <Command.Group heading="Navigate" className="text-xs text-muted-foreground [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:pb-2 [&_[cmdk-group-heading]]:pt-1 [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.13em]">
                {[...primaryNavigation, ...secondaryNavigation].map((item) => {
                  const Icon = item.icon;
                  return (
                    <Command.Item
                      key={item.to}
                      value={`${item.label} ${item.description}`}
                      onSelect={() => selectItem(item)}
                      className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-foreground aria-selected:bg-brand/10 aria-selected:text-brand"
                    >
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted text-muted-foreground"><Icon className="h-4 w-4" /></span>
                      <span className="flex-1">
                        <span className="block font-medium">{item.label}</span>
                        <span className="block text-xs text-muted-foreground">{item.description}</span>
                      </span>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </Command.Item>
                  );
                })}
              </Command.Group>
            </Command.List>
            <div className="flex items-center justify-between border-t border-border bg-muted/60 px-4 py-2.5 text-[11px] text-muted-foreground">
              <span>Use ↑ ↓ to move</span>
              <span>Enter to open</span>
            </div>
          </Command>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
