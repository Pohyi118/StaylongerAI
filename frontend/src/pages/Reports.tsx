import { BarChart3, TrendingUp, ShieldCheck, Download, Calendar, Activity, ChevronDown } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { cn } from "../App";

const revenueData = [
  { name: 'W1', protected: 12000, lost: 4000 },
  { name: 'W2', protected: 18000, lost: 3000 },
  { name: 'W3', protected: 24000, lost: 5000 },
  { name: 'W4', protected: 45000, lost: 2000 },
  { name: 'W5', protected: 85320, lost: 1000 },
];

const segmentData = [
  { name: 'Persuadables', rate: 74, color: '#FF5A5F' },
  { name: 'Sure Things', rate: 98, color: '#10B981' },
  { name: 'Inactive', rate: 22, color: '#F59E0B' },
  { name: 'Lost Causes', rate: 4, color: '#64748B' },
];

export default function Reports() {
  const navigate = useNavigate();

  const handleAction = (route: string) => {
    navigate(route);
  };

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mt-2">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-brand" />
            Analytics & Reports
          </h1>
          <p className="text-muted-foreground mt-1">Measure actual revenue protected, not just predictions.</p>
        </div>
        <div className="flex items-center gap-3">
          <button type="button" onClick={() => handleAction("/alerts")} className="bg-white/50 border border-border px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 hover:bg-white transition-colors">
            <Calendar className="w-4 h-4" /> Last 30 Days <ChevronDown className="w-4 h-4 text-muted-foreground" />
          </button>
          <button type="button" onClick={() => handleAction("/rewards")} className="bg-foreground text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-foreground/90 transition-colors shadow-sm flex items-center gap-2">
            <Download className="w-4 h-4" /> Export
          </button>
        </div>
      </header>

      {/* Main KPI Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-card p-6 border-l-4 border-l-brand relative overflow-hidden group">
          <div className="absolute right-0 top-0 p-4 opacity-10 group-hover:scale-110 transition-transform">
             <ShieldCheck className="w-16 h-16 text-brand" />
          </div>
          <div className="text-sm font-medium text-muted-foreground mb-2">Total Revenue Protected</div>
          <div className="text-4xl font-bold text-foreground tabular-nums mb-2">RM184,320</div>
          <div className="text-sm text-emerald-600 font-medium flex items-center bg-emerald-50 w-fit px-2 py-0.5 rounded border border-emerald-100">
            <TrendingUp className="w-3 h-3 mr-1" /> +24% vs last period
          </div>
        </div>
        
        <div className="glass-card p-6">
          <div className="text-sm font-medium text-muted-foreground mb-2">Intervention ROI</div>
          <div className="text-4xl font-bold text-foreground tabular-nums mb-2">8.4×</div>
          <div className="text-sm text-muted-foreground">For every RM1 spent on rewards</div>
        </div>

        <div className="glass-card p-6">
          <div className="text-sm font-medium text-muted-foreground mb-2">Accounts Rescued</div>
          <div className="text-4xl font-bold text-foreground tabular-nums mb-2">47</div>
          <div className="text-sm text-muted-foreground flex items-center gap-2">
            <span className="text-brand font-medium">38 Auto</span> 
            <span className="w-1 h-1 rounded-full bg-border"></span> 
            <span className="text-amber-600 font-medium">9 Human</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Protected vs Lost Chart */}
        <div className="lg:col-span-2 glass-card p-6 flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold">Revenue: Protected vs Lost</h2>
            <div className="flex items-center gap-4 text-sm">
               <div className="flex items-center gap-2">
                 <div className="w-3 h-3 rounded-full bg-brand"></div>
                 <span className="text-muted-foreground">Protected</span>
               </div>
               <div className="flex items-center gap-2">
                 <div className="w-3 h-3 rounded-full bg-slate-300"></div>
                 <span className="text-muted-foreground">Lost</span>
               </div>
            </div>
          </div>
          <div className="w-full" style={{height: 250}}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={revenueData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorProtected" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--brand)" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="var(--brand)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#6B7280', fontSize: 12}} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: '#6B7280', fontSize: 12}} dx={-10} tickFormatter={(val) => `RM${val/1000}k`} />
                <Tooltip 
                  contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 10px 40px -10px rgba(0,0,0,0.1)' }}
                  itemStyle={{ fontWeight: 'bold' }}
                />
                <Area type="monotone" dataKey="lost" stackId="2" stroke="#CBD5E1" fill="#F1F5F9" />
                <Area type="monotone" dataKey="protected" stackId="1" stroke="var(--brand)" strokeWidth={3} fillOpacity={1} fill="url(#colorProtected)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Retention Rate by Segment */}
        <div className="glass-card p-6 flex flex-col">
          <h2 className="text-lg font-bold mb-6">Retention by Segment</h2>
          <div className="w-full relative" style={{height: 200}}>
             <ResponsiveContainer width="100%" height="100%">
                <BarChart layout="vertical" data={segmentData} margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(0,0,0,0.05)" />
                  <XAxis type="number" hide />
                  <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{fill: '#0B1021', fontSize: 12, fontWeight: 500}} width={90} />
                  <Tooltip cursor={{fill: 'rgba(0,0,0,0.02)'}} contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }} />
                  <Bar dataKey="rate" radius={[0, 4, 4, 0]} barSize={24}>
                    {segmentData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
             </ResponsiveContainer>
          </div>
          <div className="mt-4 p-3 bg-brand/5 border border-brand/10 rounded-xl text-sm flex items-start gap-2">
            <Activity className="w-4 h-4 text-brand shrink-0 mt-0.5" />
            <p className="text-foreground/80 leading-snug">
              Interventions targeting <strong className="text-foreground">Persuadables</strong> are yielding the highest ROI this month (12.4×).
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}