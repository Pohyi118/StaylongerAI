import { useEffect, useState } from "react";
import { Gift, Wallet, Zap, CheckCircle2, History, Crown, PauseCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { cn } from "../App";
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
  reason: "Blockchain credentials are not configured, so reward payments are simulated.",
};

const SAMPLE_TRANSACTIONS = [
  { company: "Nexora Solutions", amount: 50, type: "GrabFood RM50", time: "12m ago" },
  { company: "OrbitWorks", amount: 30, type: "Shopee RM30", time: "2h ago" },
  { company: "Lumina Tech", amount: 100, type: "AWS Credit", time: "5h ago" },
  { company: "ScaleForge", amount: 50, type: "GrabFood RM50", time: "1d ago" },
];

export default function Rewards() {
  const navigate = useNavigate();
  const [rewardStatus, setRewardStatus] = useState<RewardStatus>(DEMO_REWARD_STATUS);
  const isLive = rewardStatus.configured && rewardStatus.mode?.toLowerCase() === "live";

  const handleAction = (route: string) => {
    navigate(route);
  };

  useEffect(() => {
    let isMounted = true;

    fetchJson<RewardStatus>("/api/rewards/status", { cache: "no-store" })
      .then((status) => {
        if (isMounted) {
          setRewardStatus({ ...DEMO_REWARD_STATUS, ...status });
        }
      })
      .catch(() => {
        if (isMounted) setRewardStatus(DEMO_REWARD_STATUS);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mt-2">
        <div className="relative">
          <div className="absolute -inset-4 bg-gradient-to-r from-amber-500/20 via-peach-500/20 to-transparent blur-2xl -z-10 rounded-full"></div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <Gift className="w-8 h-8 text-amber-500" />
            Value Vault
          </h1>
          <p className="text-muted-foreground mt-1">Convert unused subscription value into personalized retention credits.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="bg-white/50 border border-border px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 shadow-sm">
            <Wallet className="w-4 h-4 text-brand" />
            {isLive ? "Live Agent" : "Demo Agent"}: <span className="font-bold">{rewardStatus.defaultAmount} {rewardStatus.asset} default</span>
          </div>
          <button type="button" onClick={() => handleAction("/reports")} className="bg-foreground text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-foreground/90 transition-colors shadow-sm">
            Add Funds
          </button>
        </div>
      </header>

      <div className={cn(
        "px-4 py-3 rounded-xl border text-sm flex items-start gap-2",
        isLive ? "bg-emerald-50 text-emerald-700 border-emerald-100" : "bg-amber-50 text-amber-700 border-amber-100"
      )}>
        <Zap className="w-4 h-4 shrink-0 mt-0.5" />
        <span>
          <strong>{isLive ? "Live reward settlement configured." : "Demo reward mode."}</strong>{" "}
          {isLive
            ? `${rewardStatus.network} will settle rewards in ${rewardStatus.asset}.`
            : rewardStatus.reason || "No live blockchain transaction will be submitted."}
        </span>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-card p-5 relative overflow-hidden bg-gradient-to-br from-amber-50/50 to-white">
          <div className="text-sm font-medium text-muted-foreground mb-1">Total Unused Value Identified</div>
          <div className="text-3xl font-bold text-foreground tabular-nums">RM12,450</div>
        </div>
        <div className="glass-card p-5 relative overflow-hidden bg-gradient-to-br from-emerald-50/50 to-white">
          <div className="text-sm font-medium text-muted-foreground mb-1">Value Converted to Credits</div>
          <div className="text-3xl font-bold text-emerald-600 tabular-nums">RM4,820</div>
        </div>
        <div className="glass-card p-5 relative overflow-hidden bg-gradient-to-br from-brand/5 to-white">
          <div className="text-sm font-medium text-muted-foreground mb-1">Average Intervention Cost</div>
          <div className="text-3xl font-bold text-brand tabular-nums">RM45.50</div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Intervention Library */}
        <div className="xl:col-span-2 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Intervention Library</h2>
            <button type="button" onClick={() => handleAction("/alerts")} className="text-sm text-brand font-medium hover:underline">Manage Integrations</button>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { title: "Partner Vouchers", desc: "GrabFood, Shopee, Starbucks", status: isLive ? "Ready (x402)" : "Demo (x402)", icon: Zap, bg: "bg-amber-100", color: "text-amber-600" },
              { title: "Subscription Pause", desc: "Pause billing for 1-3 months", status: "Active (Internal)", icon: PauseCircle, bg: "bg-slate-100", color: "text-slate-600" },
              { title: "Feature Upgrade", desc: "Unlock premium tier for 30 days", status: "Active (Internal)", icon: Crown, bg: "bg-brand/10", color: "text-brand" },
              { title: "Product Credits", desc: "Apply credits to next invoice", status: "Active (Stripe)", icon: Wallet, bg: "bg-emerald-100", color: "text-emerald-600" }
            ].map((lib, i) => (
              <div key={i} className="glass-card p-5 hover:border-brand/30 transition-colors cursor-pointer group">
                <div className="flex justify-between items-start mb-4">
                  <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center", lib.bg)}>
                    <lib.icon className={cn("w-5 h-5", lib.color)} />
                  </div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground bg-black/5 px-2 py-1 rounded">
                    {lib.status}
                  </div>
                </div>
                <h3 className="font-bold text-lg">{lib.title}</h3>
                <p className="text-sm text-muted-foreground mt-1">{lib.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Agent transaction examples and Solana/x402 configuration status */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Agent Transactions</h2>
            <History className="w-5 h-5 text-muted-foreground" />
          </div>

          <div className="glass-card p-0 overflow-hidden flex flex-col h-full">
            <div className="bg-black/5 p-4 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide flex justify-between">
              <span>Autonomous Execution Examples</span>
              <span>{isLive ? "Connected" : "Demo"}: {rewardStatus.network}</span>
            </div>
            <div className="divide-y divide-border flex-1 overflow-y-auto">
              {SAMPLE_TRANSACTIONS.map((tx, i) => (
                <div key={i} className="p-4 hover:bg-white/60 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <div className="font-bold text-sm">{tx.company}</div>
                    <div className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> {isLive ? "Example" : "Simulated"}
                    </div>
                  </div>
                  <div className="flex justify-between items-end">
                    <div>
                      <div className="text-xs text-foreground font-medium">{tx.type}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">Protocol: x402</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold">{tx.amount} {rewardStatus.asset}</div>
                      <div className="text-[10px] text-muted-foreground flex items-center justify-end gap-1 mt-0.5">
                        {isLive ? "Illustrative record" : "No on-chain transaction"}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
