import { useEffect, useState } from "react";
import { Users, Search, Filter, Target, Heart, PauseCircle, Trash2, Crown, ChevronRight } from "lucide-react";
import { cn } from "../App";
import { apiUrl, fetchJson } from "../lib/api";

const CUSTOMER_FALLBACK = [
  { id: 1, name: "Acme Corp", plan: "Enterprise", mrr: "RM12,460", health: 31, risk: "87%", segment: "VIP", status: "Human Alert", icon: "Crown", color: "text-brand", bg: "bg-brand/10", border: "border-brand/20" },
  { id: 2, name: "Nexora Solutions", plan: "Growth", mrr: "RM4,200", health: 42, risk: "78%", segment: "Persuadable", status: "AI Target", icon: "Target", color: "text-pink-600", bg: "bg-pink-100", border: "border-pink-200" },
  { id: 3, name: "Kinetic Labs", plan: "Pro", mrr: "RM1,850", health: 94, risk: "4%", segment: "Sure Thing", status: "Healthy", icon: "Heart", color: "text-emerald-600", bg: "bg-emerald-100", border: "border-emerald-200" },
  { id: 4, name: "OrbitWorks", plan: "Pro", mrr: "RM2,100", health: 38, risk: "82%", segment: "Persuadable", status: "Action Needed", icon: "Target", color: "text-pink-600", bg: "bg-pink-100", border: "border-pink-200" },
  { id: 5, name: "Vertex Systems", plan: "Starter", mrr: "RM450", health: 51, risk: "45%", segment: "Inactive", status: "Monitor", icon: "PauseCircle", color: "text-amber-600", bg: "bg-amber-100", border: "border-amber-200" },
  { id: 6, name: "Maju Digital", plan: "Starter", mrr: "RM290", health: 12, risk: "95%", segment: "Lost Cause", status: "Ignore", icon: "Trash2", color: "text-slate-600", bg: "bg-slate-200", border: "border-slate-300" },
  { id: 7, name: "Nexus Logistics", plan: "Mid-Market", mrr: "RM8,200", health: 42, risk: "71%", segment: "VIP", status: "Human Alert", icon: "Crown", color: "text-brand", bg: "bg-brand/10", border: "border-brand/20" },
];

const iconMap = {
  Crown,
  Target,
  Heart,
  PauseCircle,
  Trash2,
};

export default function Customers() {
  const [customers, setCustomers] = useState(CUSTOMER_FALLBACK);
  const [selectedSegment, setSelectedSegment] = useState<"All" | "VIP" | "Persuadable">("All");
  const [searchTerm, setSearchTerm] = useState("");
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const handleImportCustomers = async () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".csv,.json,.txt";
    input.multiple = false;

    input.onchange = async (event) => {
      const file = (event.target as HTMLInputElement).files?.[0];
      if (!file) return;

      const formData = new FormData();
      formData.append("file", file);

      try {
        const response = await fetch(apiUrl("/api/customers/import"), {
          method: "POST",
          body: formData,
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Upload failed");
        }

        if (Array.isArray(data.customers)) {
          setCustomers(data.customers);
        }

        window.alert(`Customer file uploaded successfully: ${data.filename}`);
      } catch (error) {
        window.alert(error instanceof Error ? error.message : "Could not upload customer file.");
      }
    };

    input.click();
  };

  const applySegmentFilter = (segment: "All" | "VIP" | "Persuadable") => {
    setSelectedSegment(segment);
    setIsFilterOpen(false);
  };

  const normalizeSegment = (value: string) => value.toLowerCase().replace(/s$/, "").trim();

  const visibleCustomers = customers.filter((customer) => {
    const matchesSegment =
      selectedSegment === "All" ||
      normalizeSegment(customer.segment ?? "") === normalizeSegment(selectedSegment === "VIP" ? "VIP" : "Persuadable");
    const matchesSearch = customer.name.toLowerCase().includes(searchTerm.toLowerCase());

    return matchesSegment && matchesSearch;
  });

  useEffect(() => {
    let isMounted = true;

    fetchJson<{ customers: typeof CUSTOMER_FALLBACK }>('/api/customers')
      .then((data) => {
        if (isMounted) {
          setCustomers(data.customers);
        }
      })
      .catch(() => {
        if (isMounted) {
          setCustomers(CUSTOMER_FALLBACK);
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
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <Users className="w-8 h-8 text-brand" />
            Customer Directory
          </h1>
          <p className="text-muted-foreground mt-1">Manage accounts, health scores, and AI retention status.</p>
        </div>
        <button type="button" onClick={handleImportCustomers} className="bg-foreground text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-foreground/90 transition-colors shadow-sm">
          Import Customers (AI)
        </button>
      </header>

      <div className="glass-card p-4 flex flex-col md:flex-row gap-4 items-center justify-between z-10 relative">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Search companies, domains..."
            className="w-full bg-white/50 border border-border rounded-xl pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/50 transition-all"
          />
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto pb-2 md:pb-0 hide-scrollbar">
          <button
            type="button"
            onClick={() => setSelectedSegment("All")}
            className={cn("whitespace-nowrap px-4 py-2 rounded-lg text-sm font-medium transition-colors", selectedSegment === "All" ? "bg-brand text-white shadow-sm" : "bg-white/50 hover:bg-white text-foreground border border-border")}
          >
            All
          </button>
          <button
            type="button"
            onClick={() => setSelectedSegment("VIP")}
            className={cn("whitespace-nowrap px-4 py-2 rounded-lg text-sm font-medium transition-colors", selectedSegment === "VIP" ? "bg-brand text-white shadow-sm" : "bg-white/50 hover:bg-white text-foreground border border-border")}
          >
            VIPs
          </button>
          <button
            type="button"
            onClick={() => setSelectedSegment("Persuadable")}
            className={cn("whitespace-nowrap px-4 py-2 rounded-lg text-sm font-medium transition-colors", selectedSegment === "Persuadable" ? "bg-brand text-white shadow-sm" : "bg-white/50 hover:bg-white text-foreground border border-border")}
          >
            Persuadables
          </button>
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsFilterOpen((current) => !current)}
              className="whitespace-nowrap px-2 py-2 bg-white/50 hover:bg-white text-foreground border border-border rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            >
              <Filter className="w-4 h-4" /> Filters
            </button>

            {isFilterOpen && (
              <div className="absolute right-0 mt-2 w-48 rounded-xl border border-border bg-white/90 p-2 shadow-lg backdrop-blur-sm z-20">
                {(["All", "VIP", "Persuadable"] as const).map((segment) => (
                  <button
                    key={segment}
                    type="button"
                    onClick={() => applySegmentFilter(segment)}
                    className={cn(
                      "w-full text-left px-3 py-2 rounded-lg text-sm transition-colors",
                      selectedSegment === segment ? "bg-brand text-white" : "hover:bg-muted/60 text-foreground"
                    )}
                  >
                    {segment === "Persuadable" ? "Persuadables" : segment === "VIP" ? "VIPs" : "All"}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-4 relative z-10">
        {visibleCustomers.length === 0 ? (
          <div className="glass-card p-8 text-center text-muted-foreground">
            No customers match the current filter.
          </div>
        ) : visibleCustomers.map((customer) => {
          const Icon = iconMap[customer.icon as keyof typeof iconMap] ?? Users;

          return (
            <div key={customer.id} className="glass-card p-4 md:p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:shadow-md transition-all cursor-pointer group hover:-translate-y-0.5">
              <div className="flex items-center gap-4 md:w-1/3">
                <div className={cn("w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 border", customer.bg, customer.border)}>
                  <Icon className={cn("w-6 h-6", customer.color)} />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-foreground group-hover:text-brand transition-colors">{customer.name}</h3>
                  <div className="text-sm text-muted-foreground flex items-center gap-2">
                    <span>{customer.plan}</span>
                    <span className="w-1 h-1 rounded-full bg-border"></span>
                    <span className="font-medium text-foreground">{customer.mrr}</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full md:w-2/3 items-center">
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Health</div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-black/5 rounded-full overflow-hidden">
                      <div
                        className={cn("h-full rounded-full", customer.health > 70 ? "bg-emerald-500" : customer.health > 40 ? "bg-amber-500" : "bg-[#FF5A5F]")}
                        style={{ width: `${customer.health}%` }}
                      />
                    </div>
                    <span className="text-sm font-bold w-6">{customer.health}</span>
                  </div>
                </div>

                <div>
                  <div className="text-xs text-muted-foreground mb-1">Churn Risk</div>
                  <div className={cn("font-bold text-sm", parseInt(customer.risk) > 70 ? "text-[#FF5A5F]" : "text-foreground")}>
                    {customer.risk}
                  </div>
                </div>

                <div>
                  <div className="text-xs text-muted-foreground mb-1">Segment</div>
                  <div className={cn("text-xs font-bold px-2 py-1 rounded w-fit border", customer.bg, customer.color, customer.border)}>
                    {customer.segment}
                  </div>
                </div>

                <div className="flex items-center justify-between md:justify-end gap-4">
                  <div className="text-right hidden sm:block">
                    <div className="text-xs text-muted-foreground mb-1">Action</div>
                    <div className="text-sm font-medium">{customer.status}</div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-brand transition-colors" />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
