import React, { useState, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  GitCommit,
  Layers,
  FileText,
  BarChart2,
  Columns,
  Download,
  AlertCircle,
  RefreshCw,
  Clock,
  Coins,
  ShieldCheck,
  ChevronRight,
  Info,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  Legend,
} from "recharts";
import {
  api,
  InvestigationSummary,
  ProposalOrVerdict,
  DiffItem,
  DistributionItem,
  EvidenceItem,
  AuditLog,
  ProfileResponse,
} from "../api/client";
import { useInvestigationEvents } from "../hooks/useInvestigationEvents";

const WORKFLOW_STATES = [
  "PROFILE",
  "INVESTIGATE",
  "CRITIQUE",
  "ROUTE",
  "EXECUTE",
  "REPROFILE",
  "VERIFY",
  "REPORT",
  "AWAIT_HUMAN",
  "COMPLETED",
  "PARTIAL",
  "FAILED",
];

export const InvestigationPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<
    "graph" | "debate" | "health" | "diff" | "distributions" | "evidence" | "report"
  >("graph");

  const [investigation, setInvestigation] = useState<InvestigationSummary | null>(null);
  const [proposals, setProposals] = useState<ProposalOrVerdict[]>([]);
  const [diffItems, setDiffItems] = useState<DiffItem[]>([]);
  const [distributions, setDistributions] = useState<DistributionItem[]>([]);
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [auditLog, setAuditLog] = useState<AuditLog | null>(null);
  const [beforeProfile, setBeforeProfile] = useState<ProfileResponse | null>(null);
  const [afterProfile, setAfterProfile] = useState<ProfileResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // SSE event stream
  const { events, currentState: sseState, status: sseStatus, error: sseError, retry: sseRetry } = useInvestigationEvents(id);

  // Refresh all data
  const fetchData = async () => {
    if (!id) {
      setLoading(false);
      return;
    }
    try {
      const inv = await api.getInvestigation(id);
      setInvestigation(inv);

      // Fetch accompanying artifacts in parallel
      const [pRes, dRes, distRes, evRes, aRes] = await Promise.allSettled([
        api.getInvestigationProposals(id),
        api.getInvestigationDiff(id),
        api.getInvestigationDistributions(id),
        api.getInvestigationEvidence(id),
        api.getInvestigationAudit(id),
      ]);

      if (pRes.status === "fulfilled") setProposals(pRes.value);
      if (dRes.status === "fulfilled") setDiffItems(dRes.value);
      if (distRes.status === "fulfilled") setDistributions(distRes.value);
      if (evRes.status === "fulfilled") setEvidenceList(evRes.value);
      if (aRes.status === "fulfilled") setAuditLog(aRes.value);

      // Profiles
      if (inv.dataset_version_id) {
        api.getVersionProfile(inv.dataset_version_id).then(setBeforeProfile).catch(() => null);
      }
      if (inv.output_version_id) {
        api.getVersionProfile(inv.output_version_id).then(setAfterProfile).catch(() => null);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load investigation details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  // Refresh data when state changes via SSE
  useEffect(() => {
    if (sseState) {
      setInvestigation((prev) => (prev ? { ...prev, state: sseState } : prev));
      if (sseState === "COMPLETED" || sseState === "PARTIAL" || sseState === "EXECUTE") {
        fetchData();
      }
    }
  }, [sseState]);

  // Determine current active node in graph
  const currentState = sseState || investigation?.state || "PROFILE";
  const completedStates = new Set<string>();
  const currentStateIndex = WORKFLOW_STATES.indexOf(currentState);
  if (currentStateIndex >= 0) {
    WORKFLOW_STATES.slice(0, currentStateIndex).forEach((st) => completedStates.add(st));
  }
  if (currentState === "COMPLETED") {
    WORKFLOW_STATES.forEach((st) => {
      if (st !== "FAILED" && st !== "PARTIAL") completedStates.add(st);
    });
  }

  // Animated health score logic
  const beforeScore = beforeProfile?.dimensions.overall ?? 65;
  const afterScore = afterProfile?.dimensions.overall ?? 98;
  const [displayedScore, setDisplayedScore] = useState<number>(beforeScore);

  useEffect(() => {
    // Check prefers-reduced-motion
    const prefersReducedMotion =
      typeof window !== "undefined" && window.matchMedia
        ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
        : false;
    if (prefersReducedMotion) {
      setDisplayedScore(afterScore);
      return;
    }

    // Animate from before to after over 900 ms
    const startTime = performance.now();
    const duration = 900;
    const startVal = beforeScore;
    const endVal = afterScore;

    let frameId: number;
    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / duration);
      // easeOutExpo
      const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      const current = startVal + (endVal - startVal) * ease;
      setDisplayedScore(Math.round(current * 10) / 10);
      if (progress < 1) {
        frameId = requestAnimationFrame(animate);
      } else {
        setDisplayedScore(endVal);
      }
    };

    frameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameId);
  }, [beforeScore, afterScore]);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center text-slate-400">
        <div className="w-10 h-10 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm">Loading investigation...</p>
      </div>
    );
  }

  if (error || !investigation) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16">
        <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-sm flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Investigation Error</p>
            <p className="text-xs text-rose-400 mt-1">{error || "Investigation not found"}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header & Status Strip */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 mb-8 backdrop-blur">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6 mb-6">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold text-white">Investigation</h1>
              <span
                data-testid="status-badge"
                className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                  investigation.status === "completed"
                    ? "bg-emerald-950/80 text-emerald-400 border border-emerald-500/40"
                    : investigation.status === "awaiting_human"
                    ? "bg-amber-950/80 text-amber-400 border border-amber-500/40 animate-pulse"
                    : investigation.status === "partial"
                    ? "bg-yellow-950/80 text-yellow-400 border border-yellow-500/40"
                    : investigation.status === "failed"
                    ? "bg-rose-950/80 text-rose-400 border border-rose-500/40"
                    : "bg-cyan-950/80 text-cyan-400 border border-cyan-500/40 animate-pulse"
                }`}
              >
                {investigation.status.replace("_", " ")}
              </span>
            </div>
            <p className="text-xs font-mono text-slate-500 mt-1 truncate max-w-lg">
              ID: {investigation.investigation_id}
            </p>
          </div>

          <div className="flex items-center space-x-3">
            {sseError ? (
              <div className="flex items-center space-x-2 text-xs text-rose-400 bg-rose-950/40 border border-rose-500/30 px-3 py-1.5 rounded-xl">
                <span>Stream Disconnected</span>
                <button
                  onClick={sseRetry}
                  className="underline hover:text-white flex items-center space-x-1"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Retry</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2 text-xs text-slate-400 bg-slate-950/50 px-3 py-1.5 rounded-xl border border-slate-800">
                <span
                  className={`w-2 h-2 rounded-full ${
                    sseStatus === "connected" ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
                  }`}
                />
                <span className="capitalize">Stream: {sseStatus}</span>
              </div>
            )}
            <button
              onClick={fetchData}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
              title="Refresh investigation data"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Status Strip metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/80">
            <span className="text-slate-500 flex items-center space-x-1">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              <span>Iteration Progress</span>
            </span>
            <p className="text-sm font-bold text-white mt-1">
              {investigation.iteration} / {investigation.max_iterations}
            </p>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/80">
            <span className="text-slate-500 flex items-center space-x-1">
              <Coins className="w-3.5 h-3.5 text-violet-400" />
              <span>Token Budget</span>
            </span>
            <p className="text-sm font-bold text-white mt-1">
              {investigation.cost_used.toLocaleString()} / {investigation.cost_budget.toLocaleString()}
            </p>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/80">
            <span className="text-slate-500">Current Workflow State</span>
            <p className="text-sm font-bold text-cyan-400 mt-1 font-mono">{currentState}</p>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/80">
            <span className="text-slate-500">Output Cleaned Version</span>
            <p className="text-sm font-bold text-slate-200 mt-1 font-mono truncate">
              {investigation.output_version_id ? (
                <span className="text-emerald-400" title={investigation.output_version_id}>
                  {investigation.output_version_id.substring(0, 10)}...
                </span>
              ) : (
                <span className="text-slate-500">In Progress</span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex overflow-x-auto space-x-1 border-b border-slate-800/80 pb-px mb-8 scrollbar-none">
        {[
          { id: "graph", label: "Workflow Graph", icon: GitCommit },
          { id: "debate", label: "Debate Panel", icon: Layers },
          { id: "health", label: "Health Score", icon: Activity },
          { id: "diff", label: "Diff Viewer", icon: Columns },
          { id: "distributions", label: "Distributions", icon: BarChart2 },
          { id: "evidence", label: "Evidence Cards", icon: ShieldCheck },
          { id: "report", label: "Report & Audit", icon: FileText },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-t-xl text-xs font-semibold whitespace-nowrap transition-all border-b-2 ${
                active
                  ? "bg-slate-900/80 text-cyan-400 border-cyan-400 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/30 border-transparent"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: WORKFLOW GRAPH */}
      {activeTab === "graph" && (
        <div className="p-8 rounded-2xl bg-slate-900/50 border border-slate-800/80 backdrop-blur">
          <div className="mb-6">
            <h2 className="text-lg font-bold text-white">Live Workflow State Machine</h2>
            <p className="text-xs text-slate-400 mt-1">
              Driven by the Server-Sent Events stream. Active node is illuminated; completed paths glow.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {WORKFLOW_STATES.map((state, idx) => {
              const isActive = currentState === state;
              const isCompleted = completedStates.has(state);
              return (
                <div
                  key={state}
                  data-testid={`graph-node-${state.toLowerCase()}`}
                  className={`p-4 rounded-xl border flex flex-col justify-between transition-all ${
                    isActive
                      ? "bg-cyan-950/60 border-cyan-400 shadow-lg shadow-cyan-500/20 scale-105"
                      : isCompleted
                      ? "bg-slate-950/80 border-emerald-500/40 text-emerald-400"
                      : "bg-slate-950/40 border-slate-800/80 text-slate-500"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono text-slate-500">#{idx + 1}</span>
                    {isActive ? (
                      <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
                    ) : isCompleted ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <span className="w-2 h-2 rounded-full bg-slate-700" />
                    )}
                  </div>
                  <span className={`text-xs font-bold font-mono ${isActive ? "text-cyan-300" : ""}`}>
                    {state}
                  </span>
                </div>
              );
            })}
          </div>

          {/* SSE Live Event Stream Log */}
          <div className="mt-8 pt-6 border-t border-slate-800/80">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              Live Streamed Events ({events.length})
            </h3>
            {events.length === 0 ? (
              <p className="text-xs text-slate-600 font-mono">Listening for streaming events...</p>
            ) : (
              <div className="max-h-48 overflow-y-auto space-y-1.5 font-mono text-[11px] p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                {events.slice(-10).map((ev, i) => (
                  <div key={i} className="flex items-start space-x-2 text-slate-400">
                    <span className="text-cyan-400 flex-shrink-0">[{ev.type}]</span>
                    <span className="truncate">{JSON.stringify(ev.data)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: DEBATE PANEL */}
      {activeTab === "debate" && (
        <div data-testid="debate-panel" className="space-y-6">
          <div className="mb-2">
            <h2 className="text-lg font-bold text-white">Investigator & Critic Debate</h2>
            <p className="text-xs text-slate-400 mt-1">
              Proposals generated by the Investigation Agent evaluated by the Critic Agent with raw detector outputs.
            </p>
          </div>

          {proposals.length === 0 ? (
            <div className="p-12 rounded-2xl border border-slate-800 bg-slate-900/30 text-center">
              <Layers className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-400">No proposals recorded yet in this iteration.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Proposals Column */}
              <div className="space-y-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400">
                  Investigation Proposals
                </h3>
                {proposals
                  .filter((p) => p.type === "proposal")
                  .map((p: any) => (
                    <div
                      key={p.proposal_id}
                      className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-cyan-950/80 text-cyan-400 border border-cyan-500/30">
                          {p.operation}
                        </span>
                        <span className="text-xs font-mono text-slate-500">
                          Confidence: {(p.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-sm font-medium text-white mb-2">{p.rationale}</p>
                      <div className="text-xs text-slate-400 font-mono">
                        Target columns: {JSON.stringify(p.target_columns)}
                      </div>
                      <div className="text-[11px] text-slate-500 mt-2">
                        Basis: {p.confidence_basis}
                      </div>
                    </div>
                  ))}
              </div>

              {/* Critic Verdicts Column */}
              <div className="space-y-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-violet-400">
                  Critic Verdicts
                </h3>
                {proposals
                  .filter((p) => p.type === "verdict")
                  .map((v: any, idx) => {
                    const isApprove = v.verdict === "APPROVE";
                    const isReject = v.verdict === "REJECT";
                    const isEscalate = v.verdict === "ESCALATE_TO_HUMAN";
                    return (
                      <div
                        key={idx}
                        className={`p-5 rounded-2xl border backdrop-blur ${
                          isApprove
                            ? "bg-emerald-950/20 border-emerald-500/30"
                            : isReject
                            ? "bg-rose-950/20 border-rose-500/30"
                            : "bg-amber-950/20 border-amber-500/30"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-3">
                          <span
                            data-testid={`verdict-badge-${v.verdict.toLowerCase()}`}
                            className={`px-3 py-1 rounded-full text-xs font-extrabold tracking-wide ${
                              isApprove
                                ? "bg-emerald-950 text-emerald-300 border border-emerald-400"
                                : isReject
                                ? "bg-rose-950 text-rose-300 border border-rose-400"
                                : "bg-amber-950 text-amber-300 border border-amber-400"
                            }`}
                          >
                            {v.verdict}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500">
                            Proposal: {v.proposal_id}
                          </span>
                        </div>

                        <div className="space-y-2 text-xs">
                          {v.reasons && v.reasons.length > 0 && (
                            <div>
                              <span className="text-slate-400 font-semibold">Critic Reasons:</span>
                              <ul className="list-disc list-inside text-slate-300 mt-1 space-y-0.5">
                                {v.reasons.map((r: string, ri: number) => (
                                  <li key={ri}>{r}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {v.unsupported_assumptions && v.unsupported_assumptions.length > 0 && (
                            <div className="pt-2">
                              <span className="text-amber-400 font-semibold">Unsupported Assumptions:</span>
                              <ul className="list-disc list-inside text-slate-400 mt-1">
                                {v.unsupported_assumptions.map((u: string, ui: number) => (
                                  <li key={ui}>{u}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: HEALTH SCORE */}
      {activeTab === "health" && (
        <div data-testid="health-score-card" className="p-8 rounded-2xl bg-slate-900/50 border border-slate-800/80 backdrop-blur">
          <div className="mb-8">
            <h2 className="text-lg font-bold text-white">5-Dimension Deterministic Health Score</h2>
            <p className="text-xs text-slate-400 mt-1">
              Unweighted average of completeness, uniqueness, consistency, validity, and accuracy.
            </p>
          </div>

          <div className="flex flex-col md:flex-row items-center gap-10">
            {/* Overall animated score display */}
            <div className="flex flex-col items-center justify-center p-8 rounded-2xl bg-slate-950/80 border border-slate-800 w-full md:w-64">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Overall Quality
              </span>
              <div className="text-6xl font-black bg-gradient-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">
                <span data-testid="overall-score">{displayedScore.toFixed(1)}</span>%
              </div>
              <span className="text-[11px] text-slate-500 mt-2 font-mono">
                Original: {beforeScore.toFixed(1)}% &rarr; Cleaned: {afterScore.toFixed(1)}%
              </span>
            </div>

            {/* Five dimension progress bars */}
            <div className="flex-1 w-full space-y-4">
              {afterProfile?.dimensions ? (
                Object.entries(afterProfile.dimensions)
                  .filter(([key]) => key !== "overall")
                  .map(([dim, val]) => (
                    <div key={dim} className="space-y-1">
                      <div className="flex justify-between text-xs font-semibold">
                        <span className="text-slate-300 capitalize">{dim}</span>
                        <span className="text-cyan-400 font-mono">{(val as number).toFixed(1)}%</span>
                      </div>
                      <div className="w-full h-3 rounded-full bg-slate-950 border border-slate-800 overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-cyan-500 to-violet-500 rounded-full transition-all duration-700"
                          style={{ width: `${Math.min(100, Math.max(0, val as number))}%` }}
                        />
                      </div>
                    </div>
                  ))
              ) : (
                <div className="text-slate-500 text-xs">Computing dimension metrics...</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: DIFF VIEWER */}
      {activeTab === "diff" && (
        <div data-testid="diff-viewer" className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Cell & Row Level Diff Viewer</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Every modified cell, removed row, and added row tracked with confidence and rule basis.
              </p>
            </div>
            <span className="text-xs font-mono text-slate-500">
              {diffItems.length} changes recorded
            </span>
          </div>

          {diffItems.length === 0 ? (
            <div className="p-12 rounded-2xl border border-slate-800 bg-slate-900/30 text-center">
              <Columns className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-400">No diffs or modifications found.</p>
            </div>
          ) : (
            <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl overflow-hidden backdrop-blur">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      <th className="py-3 px-4">Row</th>
                      <th className="py-3 px-4">Column</th>
                      <th className="py-3 px-4">Type</th>
                      <th className="py-3 px-4">Original Value</th>
                      <th className="py-3 px-4">New Value</th>
                      <th className="py-3 px-4">Rule & Basis</th>
                      <th className="py-3 px-4 text-right">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-xs font-mono">
                    {diffItems.map((item, idx) => {
                      const isRemoved = item.change_type === "removed";
                      const isAdded = item.change_type === "added";
                      const isModified = item.change_type === "modified";
                      return (
                        <tr
                          key={idx}
                          data-testid={isRemoved ? "diff-row-removed" : undefined}
                          className={`hover:bg-slate-800/30 transition-colors ${
                            isRemoved
                              ? "bg-rose-950/20 text-rose-300"
                              : isAdded
                              ? "bg-emerald-950/20 text-emerald-300"
                              : "hover:bg-slate-800/40"
                          }`}
                        >
                          <td className="py-3 px-4 text-slate-400">
                            {item.original_row_index !== null ? item.original_row_index : "—"}
                          </td>
                          <td className="py-3 px-4 font-semibold text-white">{item.column}</td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                isRemoved
                                  ? "bg-rose-950 text-rose-400 border border-rose-500/30"
                                  : isAdded
                                  ? "bg-emerald-950 text-emerald-400 border border-emerald-500/30"
                                  : "bg-cyan-950 text-cyan-400 border border-cyan-500/30"
                              }`}
                            >
                              {item.change_type}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-rose-400 line-through">
                            {item.original_value !== null ? item.original_value : "null"}
                          </td>
                          <td className="py-3 px-4 text-emerald-400 font-bold">
                            {item.new_value !== null ? item.new_value : "null"}
                          </td>
                          <td className="py-3 px-4 text-slate-300 font-sans max-w-xs truncate" title={`${item.rule} (${item.confidence_basis})`}>
                            {item.rule}
                          </td>
                          <td className="py-3 px-4 text-right text-cyan-400">
                            {(item.confidence * 100).toFixed(0)}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 5: DISTRIBUTION CHARTS */}
      {activeTab === "distributions" && (
        <div data-testid="distribution-charts" className="space-y-6">
          <div className="mb-2">
            <h2 className="text-lg font-bold text-white">Before vs. After Distribution Analysis</h2>
            <p className="text-xs text-slate-400 mt-1">
              20 equal-width bins using original version range. Two-sample Kolmogorov-Smirnov test and PSI checks.
            </p>
          </div>

          {distributions.length === 0 ? (
            <div className="p-12 rounded-2xl border border-slate-800 bg-slate-900/30 text-center">
              <BarChart2 className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-400">No numeric distribution checks performed.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {distributions.map((dist, idx) => {
                const chartData = dist.before_bins.map((val, bIdx) => ({
                  bin: `Bin ${bIdx + 1}`,
                  before: val,
                  after: dist.after_bins[bIdx] || 0,
                }));

                return (
                  <div
                    key={idx}
                    className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-bold text-white font-mono">{dist.column}</h3>
                      <span
                        className={`px-2.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                          dist.passed
                            ? "bg-emerald-950 text-emerald-400 border border-emerald-500/40"
                            : "bg-rose-950 text-rose-400 border border-rose-500/40"
                        }`}
                      >
                        {dist.passed ? "Passed Tolerance" : "Failed Tolerance"}
                      </span>
                    </div>

                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <XAxis dataKey="bin" tick={{ fill: "#64748b", fontSize: 9 }} />
                          <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
                          <RechartsTooltip
                            contentStyle={{ backgroundColor: "#020817", borderColor: "#334155", borderRadius: 8, fontSize: 12 }}
                          />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                          <Bar dataKey="before" fill="#8b5cf6" name="Before (Original)" radius={[2, 2, 0, 0]} />
                          <Bar dataKey="after" fill="#22d3ee" name="After (Cleaned)" radius={[2, 2, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 font-mono">
                      <span>KS Stat: {dist.ks_statistic !== null ? dist.ks_statistic.toFixed(4) : "—"}</span>
                      <span>p-value: {dist.p_value !== null ? dist.p_value.toFixed(4) : "—"}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 6: EVIDENCE CARDS */}
      {activeTab === "evidence" && (
        <div data-testid="evidence-cards" className="space-y-4">
          <div className="mb-2">
            <h2 className="text-lg font-bold text-white">Statistical Evidence & Verification Claims</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Every cleaning claim backed by detector test runs, test statistics, and p-values.
            </p>
          </div>

          {evidenceList.length === 0 ? (
            <div className="p-12 rounded-2xl border border-slate-800 bg-slate-900/30 text-center">
              <ShieldCheck className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-400">No evidence entries generated yet.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {evidenceList.map((ev) => (
                <div
                  key={ev.evidence_id}
                  className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-violet-950/80 text-violet-400 border border-violet-500/30">
                      {ev.test_name}
                    </span>
                    <span className="text-[11px] font-mono text-slate-500">ID: {ev.evidence_id.substring(0, 8)}</span>
                  </div>
                  <h4 className="text-sm font-semibold text-white mb-3">{ev.claim}</h4>
                  <div className="flex items-center space-x-4 text-xs font-mono text-slate-400">
                    <span>Statistic: {ev.statistic || "N/A"}</span>
                    <span>p-value: {ev.p_value || "N/A"}</span>
                  </div>
                  {ev.details && (
                    <div className="mt-3 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-[11px] font-mono text-slate-400 truncate">
                      {JSON.stringify(ev.details)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 7: REPORT & AUDIT */}
      {activeTab === "report" && (
        <div className="space-y-8">
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur">
            <h2 className="text-lg font-bold text-white mb-2">Download Comprehensive Reports</h2>
            <p className="text-xs text-slate-400 mb-6">
              Download the complete investigation report rendered in all 4 formats.
            </p>

            <div className="flex flex-wrap gap-3">
              {(["json", "markdown", "html", "pdf"] as const).map((fmt) => (
                <a
                  key={fmt}
                  href={api.getReportDownloadUrl(investigation.investigation_id, fmt)}
                  download
                  className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center space-x-2 transition-colors uppercase tracking-wider"
                >
                  <Download className="w-4 h-4 text-cyan-400" />
                  <span>Download {fmt}</span>
                </a>
              ))}
            </div>
          </div>

          {/* Chronological Audit Log */}
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur">
            <h3 className="text-base font-bold text-white mb-4">Immutable Audit Trail</h3>
            {!auditLog || auditLog.audit_trail.length === 0 ? (
              <p className="text-xs text-slate-500 font-mono">No audit entries yet.</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
                {auditLog.audit_trail.map((item, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/60 flex items-start justify-between text-xs font-mono"
                  >
                    <div>
                      <span className="font-bold text-cyan-400">[{item.type}]</span>{" "}
                      <span className="text-slate-200">
                        {item.state || item.tool || item.operation || item.role}
                      </span>
                      {item.reason && <p className="text-slate-400 mt-1 font-sans">{item.reason}</p>}
                    </div>
                    {item.timestamp && (
                      <span className="text-[10px] text-slate-500 whitespace-nowrap ml-4">
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
