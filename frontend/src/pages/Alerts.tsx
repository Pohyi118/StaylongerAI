import { Bell, ShieldAlert, Activity, Crown, AlertTriangle, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { cn } from "../App";

export default function Alerts() {
  const navigate = useNavigate();

  const handleAction = (route: string) => {
    navigate(route);
  };

  const handleNotifyExecTeam = () => {
    const message = encodeURIComponent(
      "Executive Alert: competitor activity is impacting SME retention. Activity has dropped by 37% and 2,391 users are affected. Please review the escalation response immediately."
    );

    if (typeof window !== "undefined") {
      window.open(`https://wa.me/?text=${message}`, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mt-2">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <Bell className="w-8 h-8 text-brand" />
            Alerts & Anomalies
          </h1>
          <p className="text-muted-foreground mt-1">System-wide threat detection and VIP escalations.</p>
        </div>
      </header>

      {/* Critical Competitor Alert (From Dashboard) */}
      <div className="glass-card p-6 border-l-4 border-l-[#FF5A5F] relative overflow-hidden bg-gradient-to-r from-[#FF5A5F]/5 to-transparent shadow-lg shadow-[#FF5A5F]/5">
         <div className="absolute top-0 right-0 p-4 opacity-20">
            <Activity className="text-[#FF5A5F] w-32 h-32 -mt-8 -mr-8" />
         </div>
         <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="bg-[#FF5A5F] text-white text-[10px] font-bold px-2 py-0.5 rounded tracking-wider uppercase flex items-center gap-1 shadow-sm">
                  <ShieldAlert className="w-3 h-3" /> Emergency
                </span>
                <span className="text-sm font-semibold text-[#FF5A5F]">Competitor Alert</span>
                <span className="text-xs text-muted-foreground ml-2">Detected 09:41 AM</span>
              </div>
              <h3 className="text-2xl font-bold text-foreground mb-2">Sudden drop in user activity detected.</h3>
              <p className="text-base text-muted-foreground max-w-2xl">
                A coordinated activity drop across 127 SME customers may indicate a competitor campaign targeting your logistics software segment.
              </p>
            </div>
            
            <div className="flex flex-wrap md:flex-nowrap items-center gap-6 bg-white/50 p-4 rounded-xl border border-[#FF5A5F]/20">
               <div>
                 <div className="text-xs text-muted-foreground">Activity Drop</div>
                 <div className="text-2xl font-bold text-[#FF5A5F]">-37%</div>
               </div>
               <div className="w-px h-10 bg-border hidden md:block"></div>
               <div>
                 <div className="text-xs text-muted-foreground">Affected Users</div>
                 <div className="text-2xl font-bold">2,391</div>
               </div>
               <button type="button" onClick={handleNotifyExecTeam} className="w-full md:w-auto bg-[#FF5A5F] text-white font-medium px-6 py-3 rounded-xl shadow-sm text-sm hover:bg-[#FF5A5F]/90 transition-colors whitespace-nowrap mt-2 md:mt-0">
                 Notify Exec Team
               </button>
            </div>
         </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 relative z-10">
        
        {/* VIP Attention Required */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Crown className="w-5 h-5 text-brand" /> VIP Escalations
            </h2>
            <span className="text-xs font-bold bg-brand/10 text-brand px-2 py-1 rounded">2 Action Required</span>
          </div>

          {[
            { name: "Acme Corp", mrr: "RM12,460", risk: "87%", issue: "Executive sponsor stopped logging in for 14 days." },
            { name: "Nexus Logistics", mrr: "RM8,200", risk: "71%", issue: "Multiple severe support tickets opened regarding API latency." }
          ].map((vip, i) => (
            <div key={i} className="glass-card p-5 border border-brand/20 hover:border-brand/40 transition-colors">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-bold text-lg">{vip.name}</h3>
                  <div className="text-xs text-[#FF5A5F] font-bold mt-1 uppercase tracking-wide">Human Decision Required</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-foreground">{vip.mrr} at risk</div>
                  <div className="text-xs text-muted-foreground">{vip.risk} Churn Prob.</div>
                </div>
              </div>
              <div className="bg-white/50 p-3 rounded-lg border border-border text-sm text-muted-foreground mb-4">
                <strong>AI Diagnosis:</strong> {vip.issue}
              </div>
              <div className="flex gap-3">
                <button type="button" onClick={() => handleAction("/customers")} className="flex-1 bg-foreground text-white py-2 rounded-lg text-sm font-medium hover:bg-foreground/90 transition-colors">Assign CSM</button>
                <button type="button" onClick={() => handleAction("/customers")} className="flex-1 bg-white border border-border text-foreground py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">Call Now</button>
              </div>
            </div>
          ))}
        </div>

        {/* System Warnings */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" /> System Warnings
            </h2>
          </div>

          <div className="glass-card p-0 overflow-hidden border border-border">
            <div className="divide-y divide-border">
              <div className="p-4 bg-white/40 hover:bg-white/60 transition-colors flex gap-4 cursor-pointer">
                <div className="mt-1"><AlertTriangle className="w-5 h-5 text-amber-500" /></div>
                <div>
                  <div className="font-bold text-foreground">Usage Quota Stagnation</div>
                  <p className="text-sm text-muted-foreground mt-1">45 accounts on the Growth plan have used less than 10% of their included automation runs this month.</p>
                  <button type="button" onClick={() => handleAction("/rewards")} className="text-sm font-medium text-brand mt-2 flex items-center">Generate Value Vault Interventions <ArrowRight className="w-3 h-3 ml-1" /></button>
                </div>
              </div>

              <div className="p-4 bg-white/40 hover:bg-white/60 transition-colors flex gap-4 cursor-pointer">
                <div className="mt-1"><AlertTriangle className="w-5 h-5 text-amber-500" /></div>
                <div>
                  <div className="font-bold text-foreground">Payment Gateway Latency</div>
                  <p className="text-sm text-muted-foreground mt-1">Stripe webhooks are experiencing 300ms delays. Retention calculations are relying on cached billing states.</p>
                  <span className="text-xs text-muted-foreground mt-2 block">System monitoring automatically.</span>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}