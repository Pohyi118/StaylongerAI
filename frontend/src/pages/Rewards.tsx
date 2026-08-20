import { Gift, Wallet, Link, Zap, ArrowRight, CheckCircle2, History, ExternalLink, Crown } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { cn } from "../App";

export default function Rewards() {
  const navigate = useNavigate();

  const handleAction = (route: string) => {
    navigate(route);
  };

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
            Agent Balance: <span className="font-bold">1,240 USDC</span>
          </div>
          <button type="button" onClick={() => handleAction("/reports")} className="bg-foreground text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-foreground/90 transition-colors shadow-sm">
            Add Funds
          </button>
        </div>
      </header>

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
              { title: "Partner Vouchers", desc: "GrabFood, Shopee, Starbucks", status: "Active (x402)", icon: Zap, bg: "bg-amber-100", color: "text-amber-600" },
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

        {/* Live Agent Transactions (Solana/x402) */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Agent Transactions</h2>
            <History className="w-5 h-5 text-muted-foreground" />
          </div>

          <div className="glass-card p-0 overflow-hidden flex flex-col h-full">
            <div className="bg-black/5 p-4 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide flex justify-between">
              <span>Autonomous Executions</span>
              <span>Network: Solana</span>
            </div>
            <div className="divide-y divide-border flex-1 overflow-y-auto">
              {[
                { company: "Nexora Solutions", amount: "50 USDC", type: "GrabFood RM50", time: "12m ago", tx: "4xT9...q2pL" },
                { company: "OrbitWorks", amount: "30 USDC", type: "Shopee RM30", time: "2h ago", tx: "8vM1...z9aK" },
                { company: "Lumina Tech", amount: "100 USDC", type: "AWS Credit", time: "5h ago", tx: "2bN7...m4xR" },
                { company: "ScaleForge", amount: "50 USDC", type: "GrabFood RM50", time: "1d ago", tx: "9pQ3...v1wS" }
              ].map((tx, i) => (
                <div key={i} className="p-4 hover:bg-white/60 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <div className="font-bold text-sm">{tx.company}</div>
                    <div className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Executed
                    </div>
                  </div>
                  <div className="flex justify-between items-end">
                    <div>
                      <div className="text-xs text-foreground font-medium">{tx.type}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">Protocol: x402</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold">{tx.amount}</div>
                      <div className="text-[10px] text-muted-foreground font-mono flex items-center justify-end gap-1 mt-0.5 hover:text-brand cursor-pointer">
                        {tx.tx} <ExternalLink className="w-3 h-3" />
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

// Temporary icon components used in this file
function PauseCircle(props: any) {
  return <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinelinejoin="round" {...props}><circle cx="12" cy="12" r="10"/><line x1="10" x2="10" y1="15" y2="9"/><line x1="14" x2="14" y1="15" y2="9"/></svg>
}