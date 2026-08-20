import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, Activity, ShieldAlert, Target, Heart, PauseCircle, Trash2, Crown, ChevronRight, TrendingUp, Gift, CreditCard, ArrowRight } from "lucide-react";
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { fetchJson } from "../lib/api";

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
  vipAccounts: Array<{ name: string; plan: string; revenueAtRisk: string; healthScore: string; status: string }>;
  segments: Array<{ title: string; description: string; value: number; action: string; theme: string }>;
  rescues: Array<{ name: string; time: string; reward: string; type: string; status: string; network: string }>;
};

const DEFAULT_DASHBOARD: DashboardRecord = {
  title: "Revenue Command Center",
  status: "AI Protection Active",
  totalRevenueProtectedLabel: "RM184,320",
  weekGrowth: "+12% this week",
  roi: "8.4×",
  executiveBrief: "Churn exposure decreased 12% this week. 9 persuadable accounts were automatically rescued. A coordinated activity drop across 127 SME customers may indicate a competitor campaign.",
  metrics: [
    { label: "Accounts Rescued", value: "47", trend: "+4" },
    { label: "MRR at Risk", value: "RM24,500", trend: "-12%" },
    { label: "Agent Payments", value: "RM450", trend: "Solana/x402" },
    { label: "Health Avg", value: "72/100", trend: "Stable" },
  ],
  chartData: [
    { name: '1', revenue: 120000 },
    { name: '5', revenue: 130000 },
    { name: '10', revenue: 128000 },
    { name: '15', revenue: 145000 },
    { name: '20', revenue: 160000 },
    { name: '25', revenue: 175000 },
    { name: '30', revenue: 184320 },
  ],
  alert: {
    tag: "Emergency",
    title: "Sudden drop in user activity detected.",
    message: "Possible competitor move targeting SME segment.",
    activityDrop: "-37%",
    affectedUsers: 2391,
  },
  vipAccounts: [
    { name: "Acme Corp", plan: "Enterprise", revenueAtRisk: "RM12,460", healthScore: "31 / 100 (87% risk)", status: "Human Alert" },
    { name: "Nexus Logistics", plan: "Mid-Market", revenueAtRisk: "RM8,200", healthScore: "42 / 100 (71% risk)", status: "Human Alert" },
  ],
  segments: [
    { title: "Persuadables", description: "High risk, can be saved", value: 45, action: "AI Action: Invest Rewards", theme: "pink" },
    { title: "Sure Things", description: "Loyal & engaged", value: 1204, action: "AI Action: No Discount", theme: "emerald" },
    { title: "Inactive", description: "Low activity, monitor quietly", value: 89, action: "AI Action: Monitor", theme: "amber" },
    { title: "Lost Causes", description: "Unlikely to stay", value: 12, action: "AI Action: Ignore", theme: "slate" },
  ],
  rescues: [
    { name: "Lumina Tech", time: "12m ago", reward: "GrabFood RM50", type: "Value Vault", status: "Claimed", network: "x402/Solana" },
    { name: "ScaleForge", time: "45m ago", reward: "Pause Subscription", type: "Billing", status: "Executed", network: "Internal" },
    { name: "OrbitWorks", time: "2h ago", reward: "Shopee RM30", type: "Value Vault", status: "Claimed", network: "x402/Solana" },
  ],
};

export default function Dashboard() {
  const [dashboard, setDashboard] = useState<DashboardRecord>(DEFAULT_DASHBOARD);
  const navigate = useNavigate();

  const handleAction = (route: string) => {
    navigate(route);
  };

  const handleNotifyExecTeam = () => {
    const message = encodeURIComponent(
      "Executive Alert: churn risk is rising in the SME segment. Activity has dropped by 37% and 2,391 users are affected. Please review the retention plan immediately."
    );

    if (typeof window !== "undefined") {
      window.open(`https://wa.me/?text=${message}`, "_blank", "noopener,noreferrer");
    }
  };

  useEffect(() => {
    let isMounted = true;

    fetchJson<DashboardRecord>("/api/dashboard")
      .then((data) => {
        if (isMounted) {
          setDashboard(data);
        }
      })
      .catch(() => {
        if (isMounted) {
          setDashboard(DEFAULT_DASHBOARD);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mt-2">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground">{dashboard.title}</h1>
          <div className="flex items-center gap-2 mt-1 text-sm font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full w-fit border border-emerald-100">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            {dashboard.status}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block text-sm">
            <div className="text-foreground font-medium">Acme Admin</div>
            <div className="text-muted-foreground">Admin Workspace</div>
          </div>
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-brand/20 to-pink-500/20 border border-brand/20 flex items-center justify-center text-brand font-semibold shadow-sm">
            A
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 glass-card p-6 md:p-8 relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-brand/10 to-transparent opacity-50 z-0"></div>

          <div className="relative z-10">
            <h2 className="text-sm font-semibold text-muted-foreground tracking-wide uppercase mb-1">Total Revenue Protected</h2>
            <div className="text-4xl md:text-6xl font-bold tracking-tighter text-foreground tabular-nums">
              {dashboard.totalRevenueProtectedLabel}
            </div>
            <div className="flex items-center gap-2 mt-4 text-sm">
              <div className="flex items-center text-emerald-600 font-medium bg-emerald-50 px-2 py-0.5 rounded text-xs border border-emerald-100">
                <TrendingUp className="w-3 h-3 mr-1" />
                {dashboard.weekGrowth}
              </div>
              <span className="text-muted-foreground">Intervention ROI: <strong className="text-foreground">{dashboard.roi}</strong></span>
            </div>
          </div>

          <div className="h-[120px] md:h-[160px] w-full mt-6 z-10 relative">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={dashboard.chartData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--brand)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--brand)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="revenue" stroke="var(--brand)" strokeWidth={3} fillOpacity={1} fill="url(#colorRevenue)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card p-6 md:p-8 relative flex flex-col">
          <div className="absolute top-0 right-0 p-4 opacity-50">
            <Sparkles className="text-brand w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">AI Executive Brief</h3>
          <p className="text-foreground/80 leading-relaxed text-sm flex-1">
            {dashboard.executiveBrief}
          </p>
          <button type="button" onClick={() => handleAction("/reports")} className="mt-6 flex items-center justify-center w-full py-2.5 rounded-xl bg-foreground text-white font-medium hover:bg-foreground/90 transition-colors shadow-md text-sm">
            View Analysis <ArrowRight className="w-4 h-4 ml-2" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {dashboard.metrics.map((metric, i) => (
          <div key={i} className="glass-card p-4 flex flex-col justify-center">
            <div className="text-xs text-muted-foreground font-medium mb-1">{metric.label}</div>
            <div className="text-2xl font-bold tabular-nums">{metric.value}</div>
            <div className="text-xs text-brand font-medium mt-1">{metric.trend}</div>
          </div>
        ))}
      </div>

      <div className="glass-card p-6 border-l-4 border-l-[#FF5A5F] relative overflow-hidden bg-gradient-to-r from-[#FF5A5F]/5 to-transparent">
        <div className="absolute top-0 right-0 p-4 opacity-20">
          <Activity className="text-[#FF5A5F] w-24 h-24 -mt-4 -mr-4" />
        </div>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="bg-[#FF5A5F] text-white text-[10px] font-bold px-2 py-0.5 rounded tracking-wider uppercase flex items-center gap-1 shadow-sm">
                <ShieldAlert className="w-3 h-3" /> {dashboard.alert.tag}
              </span>
              <span className="text-sm font-semibold text-[#FF5A5F]">Competitor Alert</span>
            </div>
            <h3 className="text-xl font-bold text-foreground mb-1">{dashboard.alert.title}</h3>
            <p className="text-sm text-muted-foreground">{dashboard.alert.message}</p>
          </div>

          <div className="flex items-center gap-6">
            <div>
              <div className="text-xs text-muted-foreground">Activity Drop</div>
              <div className="text-xl font-bold text-[#FF5A5F]">{dashboard.alert.activityDrop}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Affected Users</div>
              <div className="text-xl font-bold">{dashboard.alert.affectedUsers.toLocaleString()}</div>
            </div>
            <button type="button" onClick={handleNotifyExecTeam} className="bg-white border border-[#FF5A5F]/20 text-[#FF5A5F] hover:bg-[#FF5A5F]/5 font-medium px-4 py-2 rounded-xl shadow-sm text-sm transition-colors whitespace-nowrap">
              Notify Exec Team
            </button>
          </div>
        </div>
      </div>

      <div className="mt-4 mb-2 flex items-center justify-between">
        <h2 className="text-xl font-bold">The 90/10 Retention Model</h2>
        <span className="text-sm font-medium text-muted-foreground">Operating framework</span>
      </div>

      <div className="glass-card p-6 border border-brand/20">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand/10 flex items-center justify-center">
              <Crown className="w-5 h-5 text-brand" />
            </div>
            <div>
              <h3 className="text-lg font-bold">Top 10% VIPs</h3>
              <p className="text-sm text-muted-foreground">High-value accounts • <span className="text-[#FF5A5F] font-medium">Human Alert</span></p>
            </div>
          </div>
          <button type="button" onClick={() => handleAction("/customers")} className="text-sm font-medium text-brand flex items-center hover:underline">
            View All <ChevronRight className="w-4 h-4 ml-1" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {dashboard.vipAccounts.map((account) => (
            <div key={account.name} className="bg-white/50 border border-border p-4 rounded-2xl shadow-sm flex flex-col gap-4 hover:shadow-md transition-shadow cursor-pointer">
              <div className="flex justify-between items-start">
                <div>
                  <div className="font-bold text-lg">{account.name}</div>
                  <div className="text-xs text-muted-foreground">{account.plan}</div>
                </div>
                <div className="bg-[#FF5A5F]/10 text-[#FF5A5F] px-2 py-1 rounded text-xs font-bold border border-[#FF5A5F]/20">
                  HUMAN DECISION REQUIRED
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="bg-black/5 p-2 rounded-lg">
                  <div className="text-xs text-muted-foreground mb-0.5">Revenue at Risk</div>
                  <div className="font-bold">{account.revenueAtRisk}</div>
                </div>
                <div className="bg-black/5 p-2 rounded-lg">
                  <div className="text-xs text-muted-foreground mb-0.5">Health Score</div>
                  <div className="font-bold text-[#FF5A5F]">{account.healthScore}</div>
                </div>
              </div>

              <div className="flex gap-2 mt-2">
                <button type="button" onClick={() => handleAction("/customers")} className="flex-1 bg-foreground text-white rounded-lg py-2 text-sm font-medium hover:bg-foreground/90 transition-colors">Assign CSM</button>
                <button type="button" onClick={() => handleAction("/alerts")} className="flex-1 bg-white border border-border text-foreground rounded-lg py-2 text-sm font-medium hover:bg-gray-50 transition-colors">Call Now</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-gray-600" />
          </div>
          <div>
            <h3 className="text-lg font-bold">Bottom 90% SMEs</h3>
            <p className="text-sm text-muted-foreground">AI-handled automatically • <span className="text-emerald-600 font-medium">Auto Rescue Enabled</span></p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {dashboard.segments.map((segment) => {
            const themeStyles = {
              pink: { card: "from-pink-50 to-white border-pink-100", icon: "bg-pink-100 text-pink-500", value: "text-pink-600", badge: "text-white bg-pink-500" },
              emerald: { card: "from-emerald-50 to-white border-emerald-100", icon: "bg-emerald-100 text-emerald-600", value: "text-emerald-600", badge: "text-emerald-700 bg-emerald-100 border-emerald-200" },
              amber: { card: "from-amber-50 to-white border-amber-100", icon: "bg-amber-100 text-amber-600", value: "text-amber-600", badge: "text-amber-700 bg-amber-100 border-amber-200" },
              slate: { card: "from-slate-50 to-white border-slate-200", icon: "bg-slate-200 text-slate-600", value: "text-slate-600", badge: "text-slate-700 bg-slate-200 border-slate-300" },
            };

            const currentTheme = themeStyles[segment.theme as keyof typeof themeStyles] ?? themeStyles.pink;
            const Icon = segment.title === "Persuadables" ? Target : segment.title === "Sure Things" ? Heart : segment.title === "Inactive" ? PauseCircle : Trash2;

            return (
              <div key={segment.title} className={`bg-gradient-to-br ${currentTheme.card} border p-4 rounded-2xl shadow-sm relative overflow-hidden group hover:-translate-y-1 transition-transform cursor-pointer`}>
                <div className="absolute right-0 bottom-0 p-4 opacity-10 transform group-hover:scale-110 transition-transform">
                  <Icon className={`w-16 h-16 ${currentTheme.icon}`} />
                </div>
                <div className={`w-8 h-8 rounded-full ${currentTheme.icon} flex items-center justify-center mb-3`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="font-bold text-lg text-foreground mb-1">{segment.title}</div>
                <div className="text-xs text-muted-foreground mb-3">{segment.description}</div>
                <div className={`text-2xl font-bold ${currentTheme.value} tabular-nums mb-3`}>{segment.value}</div>
                <div className={`text-xs font-bold rounded py-1 px-2 inline-block border ${currentTheme.badge}`}>{segment.action}</div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="glass-card p-0 overflow-hidden mt-2">
        <div className="p-6 border-b border-border flex justify-between items-center bg-white/40">
          <h3 className="text-lg font-bold">Recent Autonomous Rescues</h3>
          <button type="button" onClick={() => handleAction("/alerts")} className="text-sm font-medium text-brand hover:underline">View Log</button>
        </div>
        <div className="divide-y divide-border">
          {dashboard.rescues.map((rescue) => (
            <div key={`${rescue.name}-${rescue.time}`} className="p-4 md:px-6 flex items-center justify-between hover:bg-white/60 transition-colors cursor-pointer group">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-brand/10 flex items-center justify-center group-hover:scale-105 transition-transform">
                  {rescue.type === 'Value Vault' ? <Gift className="w-4 h-4 text-brand" /> : <CreditCard className="w-4 h-4 text-brand" />}
                </div>
                <div>
                  <div className="font-bold">{rescue.name}</div>
                  <div className="text-xs text-muted-foreground flex items-center gap-2 mt-0.5">
                    <span>{rescue.time}</span>
                    <span className="w-1 h-1 rounded-full bg-border"></span>
                    <span className="text-brand font-medium">{rescue.reward}</span>
                  </div>
                </div>
              </div>
              <div className="text-right hidden sm:block">
                <div className="text-sm font-bold text-emerald-600">{rescue.status}</div>
                <div className="text-[10px] text-muted-foreground uppercase tracking-wide mt-0.5">{rescue.network}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
