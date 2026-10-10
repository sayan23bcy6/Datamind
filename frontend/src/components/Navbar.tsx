import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Sun, Moon, Database, Activity, ShieldAlert, Clock, ArrowRight } from "lucide-react";
import { api, HealthResponse } from "../api/client";

interface NavbarProps {
  darkMode: boolean;
  setDarkMode: React.Dispatch<React.SetStateAction<boolean>>;
}

export const Navbar: React.FC<NavbarProps> = ({ darkMode, setDarkMode }) => {
  const location = useLocation();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    api.getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const navLinks = [
    { to: "/", label: "Home", icon: ArrowRight },
    { to: "/datasets", label: "Datasets", icon: Database },
    { to: "/reviews", label: "Reviews", icon: ShieldAlert },
    { to: "/watches", label: "Watches", icon: Clock },
  ];

  return (
    <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur sticky top-0 z-50 transition-colors dark:border-slate-800/80 dark:bg-slate-950/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-violet-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 group-hover:shadow-cyan-500/40 transition-all">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-cyan-400 via-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
              DataMind
            </span>
          </Link>

          <nav className="hidden md:flex items-center space-x-1">
            {navLinks.map((item) => {
              const active = location.pathname === item.to || (item.to !== "/" && location.pathname.startsWith(item.to));
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    active
                      ? "bg-violet-600/20 text-cyan-400 border border-violet-500/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center space-x-4">
          {health ? (
            <div className="hidden sm:flex items-center space-x-2 px-2.5 py-1 rounded-full bg-emerald-950/40 border border-emerald-500/30 text-emerald-400 text-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Stack Ready</span>
            </div>
          ) : (
            <div className="hidden sm:flex items-center space-x-2 px-2.5 py-1 rounded-full bg-amber-950/40 border border-amber-500/30 text-amber-400 text-xs">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              <span>Connecting</span>
            </div>
          )}

          <button
            onClick={() => setDarkMode((prev) => !prev)}
            aria-label="Toggle theme"
            className="p-2 rounded-lg border border-slate-700/60 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
          >
            {darkMode ? <Sun className="w-4 h-4 text-amber-300" /> : <Moon className="w-4 h-4 text-violet-400" />}
          </button>
        </div>
      </div>
    </header>
  );
};
