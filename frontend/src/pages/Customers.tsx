import { useEffect, useMemo, useState } from "react"
import * as Dialog from "@radix-ui/react-dialog"
import {
  AnimatePresence,
  motion,
  useReducedMotion,
  type Variants,
} from "motion/react"
import {
  ArrowUpRight,
  Bot,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Crown,
  Filter,
  Heart,
  MessageCircle,
  PauseCircle,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Target,
  Trash2,
  Upload,
  Users,
  X,
} from "lucide-react"
import { useSearchParams } from "react-router-dom"
import { cn } from "../App"
import { apiUrl, fetchJson } from "../lib/api"
import { openWhatsApp } from "../whatsapp"

type Customer = {
  id: number | string
  name: string
  plan?: string
  mrr?: string
  health?: number | string
  risk?: number | string
  segment?: string
  status?: string
  icon?: string
  color?: string
  bg?: string
  border?: string
  lastActive?: string
  riskReason?: string
  reason?: string
  recommendation?: string
}

const CUSTOMER_FALLBACK: Customer[] = [
  {
    id: 1,
    name: "Acme Corp",
    plan: "Enterprise",
    mrr: "RM12,460",
    health: 31,
    risk: "87%",
    segment: "VIP",
    status: "Human Alert",
    icon: "Crown",
    lastActive: "14 days ago",
    riskReason: "Executive sponsor stopped logging in.",
    recommendation: "Assign a CSM and start a WhatsApp rescue.",
  },
  {
    id: 2,
    name: "Nexora Solutions",
    plan: "Growth",
    mrr: "RM4,200",
    health: 42,
    risk: "78%",
    segment: "Persuadable",
    status: "AI Target",
    icon: "Target",
    lastActive: "3 days ago",
    riskReason: "Feature adoption has fallen below the account baseline.",
    recommendation: "Launch reverse onboarding before the next renewal cycle.",
  },
  {
    id: 3,
    name: "Kinetic Labs",
    plan: "Pro",
    mrr: "RM1,850",
    health: 94,
    risk: "4%",
    segment: "Sure Thing",
    status: "Healthy",
    icon: "Heart",
    lastActive: "Today",
    riskReason: "Engagement and product adoption remain stable.",
    recommendation: "Keep the account on its current success cadence.",
  },
  {
    id: 4,
    name: "OrbitWorks",
    plan: "Pro",
    mrr: "RM2,100",
    health: 38,
    risk: "82%",
    segment: "Persuadable",
    status: "Action Needed",
    icon: "Target",
    lastActive: "5 days ago",
    riskReason: "Product usage is down while support activity is increasing.",
    recommendation: "Offer a guided workflow review in WhatsApp.",
  },
  {
    id: 5,
    name: "Vertex Systems",
    plan: "Starter",
    mrr: "RM450",
    health: 51,
    risk: "45%",
    segment: "Sleeping Dogs",
    status: "Monitor",
    icon: "PauseCircle",
    lastActive: "19 days ago",
    riskReason: "The account is inactive but its subscription is still active.",
    recommendation: "Use a Value Vault incentive to restart engagement.",
  },
  {
    id: 6,
    name: "Maju Digital",
    plan: "Starter",
    mrr: "RM290",
    health: 12,
    risk: "95%",
    segment: "Lost Cause",
    status: "Ignore",
    icon: "Trash2",
    lastActive: "31 days ago",
    riskReason: "No meaningful engagement has been detected recently.",
    recommendation: "Do not spend intervention budget without a new signal.",
  },
  {
    id: 7,
    name: "Nexus Logistics",
    plan: "Mid-Market",
    mrr: "RM8,200",
    health: 42,
    risk: "71%",
    segment: "VIP",
    status: "Human Alert",
    icon: "Crown",
    lastActive: "2 days ago",
    riskReason: "Severe API latency tickets are affecting a key workflow.",
    recommendation: "Assign an owner and open an executive recovery path.",
  },
]

const iconMap = {
  Crown,
  Target,
  Heart,
  PauseCircle,
  Trash2,
}

const segmentTabs = [
  { value: "All", label: "All accounts" },
  { value: "VIP", label: "VIPs" },
  { value: "Persuadable", label: "Persuadables" },
] as const

const PAGE_SIZE = 8

const listVariants: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.055, delayChildren: 0.08 },
  },
}

const rowVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 340, damping: 30, mass: 0.8 },
  },
}

function getPercentage(value: Customer["health"] | Customer["risk"], fallback = 0) {
  const parsed = Number.parseFloat(String(value ?? fallback).replace(/[^\d.]/g, ""))
  return Number.isFinite(parsed) ? Math.min(100, Math.max(0, parsed)) : fallback
}

function getRevenue(value?: string) {
  const parsed = Number.parseFloat(String(value ?? "0").replace(/[^\d.]/g, ""))
  return Number.isFinite(parsed) ? parsed : 0
}

function formatRevenue(value: number) {
  return `RM${new Intl.NumberFormat("en-MY", {
    maximumFractionDigits: 0,
  }).format(value)}`
}

function displaySegment(segment?: string) {
  const normalized = segment?.toLowerCase().trim()
  if (
    normalized === "inactive" ||
    normalized === "sleeping dog" ||
    normalized === "sleeping dogs"
  ) {
    return "Sleeping Dogs"
  }
  return segment || "Persuadable"
}

function segmentTone(segment?: string) {
  switch (displaySegment(segment)) {
    case "VIP":
      return "border-teal-200 bg-teal-50 text-teal-700"
    case "Persuadable":
      return "border-orange-200 bg-orange-50 text-orange-700"
    case "Sure Thing":
      return "border-emerald-200 bg-emerald-50 text-emerald-700"
    case "Sleeping Dogs":
      return "border-amber-200 bg-amber-50 text-amber-700"
    default:
      return "border-slate-200 bg-slate-100 text-slate-700"
  }
}

function riskTone(risk: number) {
  if (risk >= 70) return "border-red-200 bg-red-50 text-red-700"
  if (risk >= 45) return "border-amber-200 bg-amber-50 text-amber-700"
  return "border-teal-200 bg-teal-50 text-teal-700"
}

function healthTone(health: number) {
  if (health >= 70) return "bg-teal-500"
  if (health >= 40) return "bg-amber-500"
  return "bg-red-500"
}

function initialism(name: string) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase()
}

function customerReason(customer: Customer) {
  if (customer.riskReason || customer.reason) {
    return customer.riskReason || customer.reason || "No primary risk signal is available."
  }

  switch (displaySegment(customer.segment)) {
    case "VIP":
      return "High-value account needs a human decision before the risk compounds."
    case "Persuadable":
      return "Recent engagement signals indicate the account is still recoverable."
    case "Sleeping Dogs":
      return "The subscription is active, but meaningful product activity is absent."
    case "Sure Thing":
      return "Healthy engagement and adoption signals are holding steady."
    default:
      return "Signals show limited recovery potential without a new engagement event."
  }
}

function customerRecommendation(customer: Customer) {
  if (customer.recommendation) return customer.recommendation

  const risk = getPercentage(customer.risk)
  if (risk >= 70) return "Start a WhatsApp rescue and assign a human owner."
  if (risk >= 45) return "Offer a Value Vault incentive and monitor the next activity signal."
  return "Maintain the current customer-success cadence."
}

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>(CUSTOMER_FALLBACK)
  const [selectedSegment, setSelectedSegment] = useState<
    "All" | "VIP" | "Persuadable"
  >("All")
  const [searchTerm, setSearchTerm] = useState("")
  const [sortBy, setSortBy] = useState<"risk" | "health" | "revenue">("risk")
  const [isFilterOpen, setIsFilterOpen] = useState(false)
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [searchParams] = useSearchParams()
  const shouldReduceMotion = useReducedMotion()
  const focus = searchParams.get("focus")
  const isTriageFocus = focus === "triage"

  const handleImportCustomers = async () => {
    const input = document.createElement("input")
    input.type = "file"
    input.accept = ".csv,.json,.txt"
    input.multiple = false

    input.onchange = async (event) => {
      const file = (event.target as HTMLInputElement).files?.[0]
      if (!file) return

      const formData = new FormData()
      formData.append("file", file)

      try {
        const response = await fetch(apiUrl("/api/customers/import"), {
          method: "POST",
          body: formData,
        })
        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.detail || "Upload failed")
        }

        if (Array.isArray(data.customers)) {
          setCustomers(data.customers as Customer[])
        }

        window.alert(`Customer file uploaded successfully: ${data.filename}`)
      } catch (error) {
        window.alert(
          error instanceof Error
            ? error.message
            : "Could not upload customer file.",
        )
      }
    }

    input.click()
  }

  const handleLaunchRescue = (customer: Customer) => {
    openWhatsApp({
      phone: import.meta.env.VITE_CUSTOMER_WHATSAPP_NUMBER,
      message: `Hi ${customer.name} team, this is your StaylongerAI customer success team. We noticed ${customerReason(customer).toLowerCase()} We would like to help with a quick recovery plan - is now a good time to chat?`,
    })
  }

  const applySegmentFilter = (segment: "All" | "VIP" | "Persuadable") => {
    setSelectedSegment(segment)
    setCurrentPage(1)
    setIsFilterOpen(false)
  }

  const normalizeSegment = (value: string) =>
    displaySegment(value).toLowerCase().replace(/s$/, "").trim()

  const visibleCustomers = useMemo(() => {
    const filtered = customers.filter((customer) => {
      const matchesSegment =
        selectedSegment === "All" ||
        normalizeSegment(customer.segment ?? "") ===
          normalizeSegment(selectedSegment === "VIP" ? "VIP" : "Persuadable")
      const matchesSearch = customer.name
        .toLowerCase()
        .includes(searchTerm.toLowerCase())

      return matchesSegment && matchesSearch
    })

    return [...filtered].sort((first, second) => {
      if (sortBy === "health") {
        return getPercentage(first.health) - getPercentage(second.health)
      }
      if (sortBy === "revenue") {
        return getRevenue(second.mrr) - getRevenue(first.mrr)
      }
      return getPercentage(second.risk) - getPercentage(first.risk)
    })
  }, [customers, searchTerm, selectedSegment, sortBy])

  const triageSummary = useMemo(() => {
    const highRisk = customers.filter((customer) => getPercentage(customer.risk) >= 70)
    const revenueExposed = highRisk.reduce(
      (total, customer) => total + getRevenue(customer.mrr),
      0,
    )
    const persuadables = customers.filter(
      (customer) => displaySegment(customer.segment) === "Persuadable",
    ).length

    return {
      highRisk: highRisk.length,
      revenueExposed,
      persuadables,
    }
  }, [customers])

  const pageCount = Math.max(1, Math.ceil(visibleCustomers.length / PAGE_SIZE))
  const activePage = Math.min(currentPage, pageCount)
  const pageStart = (activePage - 1) * PAGE_SIZE
  const pagedCustomers = visibleCustomers.slice(pageStart, pageStart + PAGE_SIZE)

  useEffect(() => {
    let isMounted = true

    fetchJson<{ customers: Customer[] }>("/api/customers")
      .then((data) => {
        if (isMounted && Array.isArray(data.customers)) {
          setCustomers(data.customers)
        }
      })
      .catch(() => {
        if (isMounted) setCustomers(CUSTOMER_FALLBACK)
      })

    return () => {
      isMounted = false
    }
  }, [])

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
            {isTriageFocus ? "AI triage" : "Customer intelligence"}
          </div>
          <h1 className="flex items-center gap-3 text-3xl font-bold tracking-[-0.045em] text-foreground md:text-[2.1rem]">
            <span className="flex size-11 items-center justify-center rounded-2xl border border-teal-200 bg-teal-50 text-teal-700 shadow-[0_8px_24px_rgba(13,148,136,0.12)]">
              {isTriageFocus ? <Sparkles className="size-5" /> : <Users className="size-5" />}
            </span>
            {isTriageFocus ? "AI Triage" : "Customer Directory"}
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground md:text-base">
            {isTriageFocus
              ? "Prioritize the accounts where an intervention can still protect revenue."
              : "A decision-ready view of account health, churn signals, and the next best retention move."}
          </p>
        </div>
        <motion.button
          type="button"
          onClick={handleImportCustomers}
          whileHover={
            shouldReduceMotion
              ? undefined
              : { y: -2, boxShadow: "0 14px 28px rgba(15, 118, 110, 0.2)" }
          }
          whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
          className="inline-flex items-center justify-center gap-2 rounded-2xl bg-teal-700 px-4 py-3 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(15,118,110,0.18)] transition-colors hover:bg-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500/45 focus:ring-offset-2"
        >
          <Upload className="size-4" />
          Import customers
        </motion.button>
      </header>

      <section
        aria-label="AI triage summary"
        className={cn(
          "grid gap-3 rounded-[26px] border bg-white p-3 shadow-[0_14px_38px_rgba(15,23,42,0.05)] md:grid-cols-3 md:p-4",
          isTriageFocus ? "border-teal-200 ring-4 ring-teal-100/70" : "border-slate-200/85",
        )}
      >
        <SummaryMetric
          label="High-risk accounts"
          value={String(triageSummary.highRisk)}
          detail="Need an owner now"
          icon={<CircleAlert className="size-4" />}
          tone="red"
        />
        <SummaryMetric
          label="Revenue exposed"
          value={formatRevenue(triageSummary.revenueExposed)}
          detail="Across current high-risk accounts"
          icon={<ArrowUpRight className="size-4" />}
          tone="teal"
        />
        <SummaryMetric
          label="Persuadables ready"
          value={String(triageSummary.persuadables)}
          detail="Best fit for an AI intervention"
          icon={<Bot className="size-4" />}
          tone="amber"
        />
      </section>

      <section className="relative z-10 flex flex-col gap-4 rounded-[26px] border border-slate-200/85 bg-white p-3 shadow-[0_14px_40px_rgba(15,23,42,0.05)] md:flex-row md:items-center md:justify-between md:p-4">
        <label className="relative block w-full md:w-[25rem]">
          <span className="sr-only">Search customers</span>
          <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={searchTerm}
            onChange={(event) => {
              setSearchTerm(event.target.value)
              setCurrentPage(1)
            }}
            placeholder="Search customers..."
            className="w-full rounded-2xl border border-slate-200 bg-slate-50/70 py-3 pl-11 pr-4 text-sm text-foreground outline-none transition-[box-shadow,border-color,background-color] placeholder:text-muted-foreground/75 focus:border-teal-400 focus:bg-white focus:ring-4 focus:ring-teal-100"
          />
        </label>

        <div className="flex w-full min-w-0 flex-col gap-2 md:w-auto md:flex-row md:items-center">
          <div className="min-w-0 md:w-auto">
            <div className="mb-1 flex items-center justify-between px-1 md:hidden">
              <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                Customer segment
              </span>
              <span className="inline-flex items-center gap-0.5 text-[11px] font-medium text-teal-700">
                Swipe <ChevronRight className="size-3" />
              </span>
            </div>
            <div className="relative">
              <div className="flex min-w-0 overflow-x-auto overscroll-x-contain rounded-2xl border border-slate-200 bg-slate-50 p-1 pr-9 md:pr-1">
                {segmentTabs.map((tab) => {
                  const isActive = selectedSegment === tab.value
                  return (
                    <button
                      key={tab.value}
                      type="button"
                      onClick={() => {
                        setSelectedSegment(tab.value)
                        setCurrentPage(1)
                      }}
                      className={cn(
                        "relative isolate shrink-0 whitespace-nowrap rounded-xl px-3 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/50",
                        isActive
                          ? "text-teal-800"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {isActive ? (
                        <motion.span
                          layoutId="customer-segment-pill"
                          className="absolute inset-0 -z-10 rounded-xl bg-white shadow-[0_2px_10px_rgba(15,23,42,0.1)]"
                          transition={{ type: "spring", stiffness: 380, damping: 32 }}
                        />
                      ) : null}
                      {tab.label}
                    </button>
                  )
                })}
              </div>
              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-y-1 right-1 flex w-9 items-center justify-end bg-gradient-to-l from-slate-50 via-slate-50/90 to-transparent pr-1 text-teal-700 md:hidden"
              >
                <ChevronRight className="size-4" />
              </span>
            </div>
          </div>

          <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2 md:flex md:items-center">
            <label className="sr-only" htmlFor="customer-sort">
              Sort customers
            </label>
            <div className="relative min-w-0 md:w-auto">
              <select
                id="customer-sort"
                value={sortBy}
                onChange={(event) => {
                  setSortBy(event.target.value as "risk" | "health" | "revenue")
                  setCurrentPage(1)
                }}
                className="w-full appearance-none rounded-2xl border border-slate-200 bg-white py-2 pl-3 pr-8 text-sm font-medium text-foreground outline-none transition-colors hover:bg-slate-50 focus:border-teal-400 focus:ring-4 focus:ring-teal-100 md:w-auto"
              >
                <option value="risk">Highest risk</option>
                <option value="health">Lowest health</option>
                <option value="revenue">Highest revenue</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            </div>

            <div className="relative">
              <motion.button
                type="button"
                onClick={() => setIsFilterOpen((current) => !current)}
                whileTap={shouldReduceMotion ? undefined : { scale: 0.97 }}
                aria-expanded={isFilterOpen}
                aria-controls="customer-filter-menu"
                className="inline-flex min-h-10 items-center gap-2 whitespace-nowrap rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-teal-500/40"
              >
                <SlidersHorizontal className="size-4 text-muted-foreground" />
                <span>Filters</span>
                <Filter className="size-3.5 text-muted-foreground" />
              </motion.button>

              <AnimatePresence>
                {isFilterOpen ? (
                  <motion.div
                    id="customer-filter-menu"
                    initial={shouldReduceMotion ? false : { opacity: 0, y: -6, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -4, scale: 0.98 }}
                    transition={{ duration: 0.16, ease: "easeOut" }}
                    className="absolute right-0 top-full z-30 mt-2 w-52 rounded-2xl border border-slate-200 bg-white p-2 shadow-[0_18px_48px_rgba(15,23,42,0.16)]"
                  >
                    <p className="px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.13em] text-muted-foreground">
                      Show segment
                    </p>
                    {segmentTabs.map((tab) => (
                      <button
                        key={tab.value}
                        type="button"
                        onClick={() => applySegmentFilter(tab.value)}
                        className={cn(
                          "mt-1 flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm transition-colors",
                          selectedSegment === tab.value
                            ? "bg-teal-50 font-semibold text-teal-800"
                            : "text-foreground hover:bg-slate-50",
                        )}
                      >
                        {tab.label}
                        {selectedSegment === tab.value ? (
                          <span className="size-1.5 rounded-full bg-teal-600" />
                        ) : null}
                      </button>
                    ))}
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </section>

      <section
        aria-labelledby="customer-risk-table-title"
        className="overflow-hidden rounded-[26px] border border-slate-200/85 bg-white shadow-[0_16px_42px_rgba(15,23,42,0.055)]"
      >
        <div className="flex flex-col gap-2 border-b border-slate-200/85 px-5 py-4 sm:flex-row sm:items-center sm:justify-between md:px-6">
          <div>
            <h2 id="customer-risk-table-title" className="text-lg font-semibold tracking-[-0.02em] text-foreground">
              Customer risk queue
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Select an account to review its AI diagnosis and recovery path.
            </p>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-800">
            <ShieldCheck className="size-3.5" />
            {visibleCustomers.length} accounts in view
          </span>
        </div>

        {visibleCustomers.length === 0 ? (
          <div className="px-6 py-14 text-center">
            <Search className="mx-auto mb-3 size-6 text-muted-foreground" />
            <h3 className="font-semibold text-foreground">No accounts found</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Try a different search or segment filter.
            </p>
          </div>
        ) : (
          <>
            <motion.div
              variants={listVariants}
              initial={shouldReduceMotion ? false : "hidden"}
              animate="visible"
              className="grid gap-3 p-3 md:hidden"
            >
              {pagedCustomers.map((customer) => {
                const Icon = iconMap[customer.icon as keyof typeof iconMap] ?? Users
                const health = getPercentage(customer.health, 50)
                const risk = getPercentage(customer.risk, 50)
                const recommendation = customerRecommendation(customer)

                return (
                  <motion.button
                    key={customer.id}
                    type="button"
                    variants={rowVariants}
                    onClick={() => setSelectedCustomer(customer)}
                    whileTap={shouldReduceMotion ? undefined : { scale: 0.985 }}
                    className="group w-full rounded-[22px] border border-slate-200 bg-white p-4 text-left shadow-[0_7px_20px_rgba(15,23,42,0.04)] transition-colors hover:border-teal-200 hover:bg-teal-50/35 focus:outline-none focus:ring-2 focus:ring-teal-500/45 focus:ring-offset-2"
                    aria-label={`Open customer intelligence for ${customer.name}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-3">
                        <div className={cn("flex size-10 shrink-0 items-center justify-center rounded-xl border", segmentTone(customer.segment))}>
                          <Icon className="size-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate font-semibold text-foreground transition-colors group-hover:text-teal-800">
                            {customer.name}
                          </p>
                          <p className="mt-0.5 truncate text-sm text-muted-foreground">
                            {customer.plan || "Account plan"}
                          </p>
                        </div>
                      </div>
                      <ChevronRight className="mt-1 size-5 shrink-0 text-slate-400 transition-transform group-hover:translate-x-0.5 group-hover:text-teal-700" />
                    </div>

                    <div className="mt-4 flex items-center justify-between gap-3">
                      <span className={cn("truncate rounded-full border px-2.5 py-1 text-xs font-semibold", segmentTone(customer.segment))}>
                        {displaySegment(customer.segment)}
                      </span>
                      <span className={cn("shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold tabular-nums", riskTone(risk))}>
                        {risk}% risk
                      </span>
                    </div>

                    <div className="mt-4 border-y border-slate-100 py-3">
                      <div className="flex items-center justify-between gap-3 text-sm">
                        <span className="text-muted-foreground">Health score</span>
                        <span className="font-semibold tabular-nums text-foreground">{health}/100</span>
                      </div>
                      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
                        <motion.div
                          initial={shouldReduceMotion ? false : { width: 0 }}
                          animate={{ width: `${health}%` }}
                          transition={{ duration: 0.56, ease: "easeOut" }}
                          className={cn("h-full rounded-full", healthTone(health))}
                        />
                      </div>
                    </div>

                    <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                      <div className="min-w-0">
                        <p className="text-xs text-muted-foreground">Monthly revenue</p>
                        <p className="mt-1 truncate font-semibold tabular-nums text-foreground">{customer.mrr || "RM0"}</p>
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs text-muted-foreground">Last active</p>
                        <p className="mt-1 truncate font-semibold text-foreground">{customer.lastActive || "Not available"}</p>
                      </div>
                    </div>

                    <div className="mt-4 rounded-xl bg-slate-50 px-3 py-2.5">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.11em] text-teal-700">AI recommendation</p>
                      <p className="mt-1 line-clamp-2 text-sm leading-5 text-muted-foreground" title={recommendation}>
                        {recommendation}
                      </p>
                    </div>
                  </motion.button>
                )
              })}
            </motion.div>

            <div className="hidden overflow-x-auto md:block">
            <motion.table
              variants={listVariants}
              initial={shouldReduceMotion ? false : "hidden"}
              animate="visible"
              className="w-full min-w-[920px] border-separate border-spacing-0 text-left"
            >
              <thead className="bg-slate-50/85 text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                <tr>
                  <th scope="col" className="px-6 py-3.5">Customer</th>
                  <th scope="col" className="px-4 py-3.5">Health</th>
                  <th scope="col" className="px-4 py-3.5">Churn risk</th>
                  <th scope="col" className="px-4 py-3.5">Revenue</th>
                  <th scope="col" className="px-4 py-3.5">Last active</th>
                  <th scope="col" className="px-4 py-3.5">AI recommendation</th>
                  <th scope="col" className="px-6 py-3.5 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pagedCustomers.map((customer) => {
                  const Icon = iconMap[customer.icon as keyof typeof iconMap] ?? Users
                  const health = getPercentage(customer.health, 50)
                  const risk = getPercentage(customer.risk, 50)
                  const recommendation = customerRecommendation(customer)

                  return (
                    <motion.tr
                      key={customer.id}
                      variants={rowVariants}
                      onClick={() => setSelectedCustomer(customer)}
                      whileHover={shouldReduceMotion ? undefined : { backgroundColor: "rgba(240, 253, 250, 0.72)" }}
                      className="group cursor-pointer transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div className="flex min-w-[180px] items-center gap-3">
                          <div className={cn("flex size-10 shrink-0 items-center justify-center rounded-xl border", segmentTone(customer.segment))}>
                            <Icon className="size-4" />
                          </div>
                          <div className="min-w-0">
                            <div className="truncate font-semibold text-foreground group-hover:text-teal-800">
                              {customer.name}
                            </div>
                            <div className="mt-0.5 text-sm text-muted-foreground">
                              {customer.plan || "Account plan"}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex w-24 items-center gap-2">
                          <span className="text-sm font-semibold tabular-nums text-foreground">{health}</span>
                          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                            <motion.div
                              initial={shouldReduceMotion ? false : { width: 0 }}
                              animate={{ width: `${health}%` }}
                              transition={{ duration: 0.56, ease: "easeOut" }}
                              className={cn("h-full rounded-full", healthTone(health))}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className={cn("inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold tabular-nums", riskTone(risk))}>
                          {risk}%
                        </span>
                      </td>
                      <td className="px-4 py-4 text-sm font-semibold tabular-nums text-foreground">
                        {customer.mrr || "RM0"}
                      </td>
                      <td className="px-4 py-4 text-sm text-muted-foreground">
                        {customer.lastActive || "Not available"}
                      </td>
                      <td className="max-w-[245px] px-4 py-4">
                        <div className="line-clamp-2 text-sm leading-5 text-muted-foreground" title={recommendation}>
                          {recommendation}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center justify-end gap-3">
                          <span className={cn("whitespace-nowrap rounded-full border px-2.5 py-1 text-xs font-semibold", segmentTone(customer.segment))}>
                            {displaySegment(customer.segment)}
                          </span>
                          <button
                            type="button"
                            onClick={() => setSelectedCustomer(customer)}
                            className="flex size-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-teal-50 hover:text-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500/40"
                            aria-label={`View customer intelligence for ${customer.name}`}
                          >
                            <ChevronRight className="size-4 transition-transform group-hover:translate-x-0.5" />
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  )
                })}
              </tbody>
            </motion.table>
            </div>
          </>
        )}
        {visibleCustomers.length > PAGE_SIZE ? (
          <div className="flex flex-col gap-3 border-t border-slate-200 px-5 py-3.5 text-sm sm:flex-row sm:items-center sm:justify-between md:px-6">
            <p className="text-muted-foreground">
              Showing <span className="font-medium text-foreground">{pageStart + 1}–{Math.min(pageStart + PAGE_SIZE, visibleCustomers.length)}</span> of {visibleCustomers.length} accounts
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                disabled={activePage === 1}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-2 font-medium text-foreground transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-45"
              >
                <ChevronLeft className="size-4" /> Previous
              </button>
              <span className="min-w-16 text-center text-xs font-semibold tabular-nums text-muted-foreground">Page {activePage} / {pageCount}</span>
              <button
                type="button"
                onClick={() => setCurrentPage((page) => Math.min(pageCount, page + 1))}
                disabled={activePage === pageCount}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-2 font-medium text-foreground transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-45"
              >
                Next <ChevronRight className="size-4" />
              </button>
            </div>
          </div>
        ) : null}
      </section>

      <CustomerDrawer
        customer={selectedCustomer}
        shouldReduceMotion={shouldReduceMotion}
        onOpenChange={(open) => {
          if (!open) setSelectedCustomer(null)
        }}
        onLaunchRescue={handleLaunchRescue}
      />
    </motion.div>
  )
}

function SummaryMetric({
  label,
  value,
  detail,
  icon,
  tone,
}: {
  label: string
  value: string
  detail: string
  icon: React.ReactNode
  tone: "teal" | "amber" | "red"
}) {
  const tones = {
    teal: "border-teal-100 bg-teal-50/65 text-teal-700",
    amber: "border-amber-100 bg-amber-50/65 text-amber-700",
    red: "border-red-100 bg-red-50/65 text-red-700",
  }

  return (
    <div className="flex items-center gap-3 rounded-[20px] border border-slate-100 bg-slate-50/55 px-4 py-3.5">
      <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-xl border", tones[tone])}>
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <p className="mt-0.5 text-lg font-bold tracking-[-0.03em] text-foreground">{value}</p>
        <p className="mt-0.5 truncate text-xs text-muted-foreground">{detail}</p>
      </div>
    </div>
  )
}

function CustomerDrawer({
  customer,
  shouldReduceMotion,
  onOpenChange,
  onLaunchRescue,
}: {
  customer: Customer | null
  shouldReduceMotion: boolean | null
  onOpenChange: (open: boolean) => void
  onLaunchRescue: (customer: Customer) => void
}) {
  if (!customer) return null

  const health = getPercentage(customer.health, 50)
  const risk = getPercentage(customer.risk, 50)
  const recommendation = customerRecommendation(customer)
  const segment = displaySegment(customer.segment)

  return (
    <Dialog.Root open onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[70] bg-slate-950/30 backdrop-blur-[2px]" />
        <Dialog.Content asChild>
          <motion.aside
            initial={shouldReduceMotion ? false : { opacity: 0, x: 28 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ type: "spring", stiffness: 320, damping: 30 }}
            className="fixed inset-y-0 right-0 z-[71] flex w-full max-w-xl flex-col overflow-y-auto border-l border-slate-200 bg-[#fcfdfd] shadow-[-24px_0_64px_rgba(15,23,42,0.16)] outline-none"
          >
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-5 sm:px-7">
              <div className="flex min-w-0 items-center gap-3">
                <div className={cn("flex size-12 shrink-0 items-center justify-center rounded-2xl border text-sm font-bold", segmentTone(segment))}>
                  {initialism(customer.name)}
                </div>
                <div className="min-w-0">
                  <Dialog.Title className="truncate text-xl font-bold tracking-[-0.035em] text-foreground">
                    {customer.name}
                  </Dialog.Title>
                  <Dialog.Description className="mt-1 text-sm text-muted-foreground">
                    {customer.plan || "Customer account"} · {customer.mrr || "RM0"} monthly revenue
                  </Dialog.Description>
                </div>
              </div>
              <Dialog.Close asChild>
                <button
                  type="button"
                  aria-label="Close customer details"
                  className="ml-3 flex size-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-muted-foreground transition-colors hover:bg-slate-50 hover:text-foreground focus:outline-none focus:ring-2 focus:ring-teal-500/40"
                >
                  <X className="size-4" />
                </button>
              </Dialog.Close>
            </div>

            <div className="flex flex-1 flex-col gap-6 px-5 py-6 sm:px-7">
              <section className="grid grid-cols-2 gap-3">
                <div className="rounded-[20px] border border-slate-200 bg-white p-4 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-[0.11em] text-muted-foreground">Health score</p>
                  <div className="mt-3 flex items-end gap-2">
                    <span className="text-4xl font-bold tracking-[-0.055em] text-foreground">{health}</span>
                    <span className="mb-1 text-sm text-muted-foreground">/ 100</span>
                  </div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                    <motion.div
                      initial={shouldReduceMotion ? false : { width: 0 }}
                      animate={{ width: `${health}%` }}
                      transition={{ duration: 0.65, ease: "easeOut" }}
                      className={cn("h-full rounded-full", healthTone(health))}
                    />
                  </div>
                </div>
                <div className="rounded-[20px] border border-slate-200 bg-white p-4 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-[0.11em] text-muted-foreground">Churn risk</p>
                  <div className="mt-3 flex items-end gap-2">
                    <span className="text-4xl font-bold tracking-[-0.055em] text-foreground">{risk}%</span>
                  </div>
                  <span className={cn("mt-3 inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold", riskTone(risk))}>
                    {segment}
                  </span>
                </div>
              </section>

              <section className="rounded-[22px] border border-teal-100 bg-teal-50/65 p-4">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-teal-800">
                  <Sparkles className="size-3.5" />
                  AI diagnosis
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-700">{customerReason(customer)}</p>
                <div className="mt-4 grid grid-cols-2 gap-3 border-t border-teal-100 pt-4 text-sm">
                  <div>
                    <p className="text-xs text-muted-foreground">Last activity</p>
                    <p className="mt-1 font-semibold text-foreground">{customer.lastActive || "Not available"}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">AI confidence</p>
                    <p className="mt-1 font-semibold text-foreground">{risk >= 70 ? "High" : risk >= 45 ? "Medium" : "Monitoring"}</p>
                  </div>
                </div>
              </section>

              <section className="rounded-[22px] border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                  <Target className="size-3.5 text-teal-700" />
                  Recommended action
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-700">{recommendation}</p>
                <div className="mt-4 flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2.5 text-sm">
                  <span className="text-muted-foreground">Current status</span>
                  <span className="font-semibold text-foreground">{customer.status || "Monitoring"}</span>
                </div>
              </section>

              <div className="mt-auto grid gap-3 sm:grid-cols-2">
                <motion.button
                  type="button"
                  onClick={() => onLaunchRescue(customer)}
                  whileHover={shouldReduceMotion ? undefined : { y: -1 }}
                  whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl bg-teal-700 px-4 py-3 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(15,118,110,0.18)] transition-colors hover:bg-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500/40 focus:ring-offset-2"
                >
                  <MessageCircle className="size-4" />
                  Launch WhatsApp rescue
                </motion.button>
                <Dialog.Close asChild>
                  <button
                    type="button"
                    className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-foreground transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-teal-500/40"
                  >
                    Keep monitoring
                  </button>
                </Dialog.Close>
              </div>
            </div>
          </motion.aside>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
