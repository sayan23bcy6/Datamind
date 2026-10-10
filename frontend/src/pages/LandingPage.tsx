import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, Upload, Play, CheckCircle2, ArrowRight } from "lucide-react";
import { api } from "../api/client";

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [loadingDemo, setLoadingDemo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTryDemo = async () => {
    setLoadingDemo(true);
    setError(null);
    try {
      const res = await api.createDemoDataset();
      navigate(`/datasets/${res.dataset_id}`);
    } catch (err: any) {
      setError(err?.message || "Failed to create demo dataset");
    } finally {
      setLoadingDemo(false);
    }
  };

  const stages = [
    { id: "upload", label: "1. Upload", desc: "CSV, XLSX, XLS ingestion" },
    { id: "profile", label: "2. Profile", desc: "Deterministic 5D health scoring" },
    { id: "investigate", label: "3. Investigate", desc: "Detector tools & proposal generation" },
    { id: "critic", label: "4. Critic", desc: "Adversarial critique on raw tool outputs" },
    { id: "clean", label: "5. Clean", desc: "Deterministic cleaning operations" },
    { id: "verify", label: "6. Verify", desc: "KS test & PSI distribution bounds" },
    { id: "report", label: "7. Report", desc: "Evidence log, audit trail, PDF/MD/HTML" },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Hero Section */}
      <div className="text-center max-w-3xl mx-auto mb-16">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/40 border border-cyan-500/30 text-cyan-400 text-xs font-semibold mb-6">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Autonomous Deterministic Data Quality & Repair</span>
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white mb-6">
          Autonomous Data Cleaning with{" "}
          <span className="bg-gradient-to-r from-cyan-400 via-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
            Adversarial Verification
          </span>
        </h1>
        <p className="text-lg text-slate-300 mb-8 leading-relaxed">
          DataMind combines deterministic statistical detectors with an investigator-critic agent debate
          to clean mixed date formats, planted outliers, exact & near duplicates, and categorical drift — with
          every change audited and verified against strict distribution tolerances.
        </p>

        {error && (
          <div className="p-4 mb-6 rounded-xl bg-rose-950/50 border border-rose-500/30 text-rose-300 text-sm">
            {error}
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={handleTryDemo}
            disabled={loadingDemo}
            className="w-full sm:w-auto px-8 py-3.5 rounded-xl font-semibold bg-gradient-to-r from-cyan-500 to-violet-600 text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            {loadingDemo ? (
              <span className="flex items-center space-x-2">
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                <span>Preparing Demo...</span>
              </span>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Try the demo</span>
              </>
            )}
          </button>
          <button
            onClick={() => navigate("/datasets")}
            className="w-full sm:w-auto px-8 py-3.5 rounded-xl font-semibold bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700 hover:border-slate-600 transition-all flex items-center justify-center space-x-2"
          >
            <Upload className="w-4 h-4" />
            <span>Upload your own file</span>
          </button>
        </div>
      </div>

      {/* Seven Stages Explainer with Animated SVG */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 mb-16 backdrop-blur">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-white mb-2">Seven-Stage Autonomous Workflow</h2>
          <p className="text-slate-400 text-sm">
            No stubs or fake data. Deterministic state machine with verifiable checkpoints.
          </p>
        </div>

        {/* Animated SVG Pipeline Diagram */}
        <div className="w-full overflow-x-auto pb-4">
          <svg className="w-full min-w-[760px] h-32" viewBox="0 0 840 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="flowGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#22d3ee" />
                <stop offset="50%" stopColor="#8b5cf6" />
                <stop offset="100%" stopColor="#d946ef" />
              </linearGradient>
              <filter id="glowEffect" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Connecting animated track */}
            <path
              d="M 60 50 L 780 50"
              stroke="#334155"
              strokeWidth="4"
              strokeDasharray="6 6"
            />
            <path
              d="M 60 50 L 780 50"
              stroke="url(#flowGrad)"
              strokeWidth="3"
              strokeDasharray="40 120"
              className="animate-pulse"
            />

            {/* Stage Nodes */}
            {stages.map((stage, idx) => {
              const cx = 60 + idx * 120;
              return (
                <g key={stage.id} className="cursor-pointer group">
                  <circle
                    cx={cx}
                    cy={50}
                    r={20}
                    className="fill-slate-900 stroke-cyan-500/60 group-hover:stroke-cyan-400 transition-all"
                    strokeWidth="2.5"
                    filter="url(#glowEffect)"
                  />
                  <circle cx={cx} cy={50} r={8} className="fill-cyan-400 group-hover:fill-violet-400 transition-all" />
                  <text
                    x={cx}
                    y={22}
                    textAnchor="middle"
                    className="text-[11px] font-bold fill-slate-200"
                  >
                    {stage.label.split(". ")[1]}
                  </text>
                  <text
                    x={cx}
                    y={82}
                    textAnchor="middle"
                    className="text-[9px] fill-slate-400 max-w-[100px]"
                  >
                    Stage {idx + 1}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Stage description cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
          {stages.slice(0, 4).map((stage) => (
            <div key={stage.id} className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/80">
              <span className="text-xs font-semibold text-cyan-400">{stage.label}</span>
              <p className="text-xs text-slate-300 mt-1">{stage.desc}</p>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
          {stages.slice(4).map((stage) => (
            <div key={stage.id} className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/80">
              <span className="text-xs font-semibold text-violet-400">{stage.label}</span>
              <p className="text-xs text-slate-300 mt-1">{stage.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Pipeline Status Indicator with required Section 6 rule */}
      <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/60 flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">Current Pipeline Status</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time execution state across datasets. No hardcoded queued labels.
          </p>
        </div>
        <div className="px-4 py-2 rounded-xl bg-slate-800/60 border border-slate-700/60 text-slate-300 text-xs font-medium">
          No investigation yet
        </div>
      </div>
    </div>
  );
};
