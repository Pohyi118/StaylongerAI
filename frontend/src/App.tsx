import { BrowserRouter, Routes, Route, NavLink, Navigate } from "react-router-dom";
import { Home, Users, Bell, Gift, BarChart3 } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import Dashboard from "./pages/Dashboard";
import Customers from "./pages/Customers";
import Alerts from "./pages/Alerts";
import Rewards from "./pages/Rewards";
import RewardClaim from "./pages/RewardClaim";
import Reports from "./pages/Reports";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="diffuse-bg min-h-screen pb-24 md:pb-0 md:pl-20 text-foreground antialiased font-sans">
        <DesktopNav />

        <main className="max-w-7xl mx-auto p-4 md:p-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/customers" element={<Customers />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/rewards" element={<Rewards />} />
            <Route path="/reward" element={<RewardClaim />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        <BottomNav />
      </div>
    </BrowserRouter>
  );
}

function BottomNav() {
  const navItems = [
    { to: "/", icon: Home, label: "Dashboard" },
    { to: "/customers", icon: Users, label: "Customers" },
    { to: "/alerts", icon: Bell, label: "Alerts" },
    { to: "/rewards", icon: Gift, label: "Rewards" },
    { to: "/reports", icon: BarChart3, label: "Reports" },
  ];

  return (
    <div className="fixed bottom-0 left-0 right-0 md:hidden p-4 z-50 pointer-events-none">
      <nav className="glass-card pointer-events-auto flex items-center justify-around p-2 rounded-full shadow-lg border border-white/20 bg-white/70">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex flex-col items-center justify-center p-2 rounded-full transition-all duration-300 relative group",
                isActive
                  ? "text-brand"
                  : "text-muted-foreground hover:text-foreground"
              )
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute inset-0 bg-brand/10 rounded-full scale-110 -z-10" />
                )}
                <item.icon
                  className="w-6 h-6"
                  strokeWidth={isActive ? 2.5 : 2}
                />
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

function DesktopNav() {
  const navItems = [
    { to: "/", icon: Home, label: "Dashboard" },
    { to: "/customers", icon: Users, label: "Customers" },
    { to: "/alerts", icon: Bell, label: "Alerts" },
    { to: "/rewards", icon: Gift, label: "Rewards" },
    { to: "/reports", icon: BarChart3, label: "Reports" },
  ];

  return (
    <div className="hidden md:flex flex-col fixed top-0 bottom-0 left-0 w-20 p-4 z-50">
      <nav className="glass-card flex-1 flex flex-col items-center py-6 gap-6 rounded-3xl">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand to-pink-500 mb-4 flex items-center justify-center shadow-lg">
          <span className="text-white font-bold text-xl">C</span>
        </div>

        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            title={item.label}
            className={({ isActive }) =>
              cn(
                "flex items-center justify-center w-12 h-12 rounded-xl transition-all duration-300 relative group",
                isActive
                  ? "text-brand bg-brand/10"
                  : "text-muted-foreground hover:bg-black/5 hover:text-foreground"
              )
            }
          >
            <item.icon className="w-6 h-6" strokeWidth={2} />
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
