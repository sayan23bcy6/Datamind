import React, { useState, useEffect } from "react";
import { Clock, Plus, Trash2, AlertCircle, CheckCircle2, ShieldCheck } from "lucide-react";
import { api, WatchItem, DatasetItem } from "../api/client";

export const WatchesPage: React.FC = () => {
  const [watches, setWatches] = useState<WatchItem[]>([]);
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // New watch form state
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const [schedule, setSchedule] = useState<string>("@daily");
  const [driftThreshold, setDriftThreshold] = useState<string>("0.10");
  const [creating, setCreating] = useState<boolean>(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [wList, dList] = await Promise.all([api.getWatches(), api.getDatasets()]);
      setWatches(wList);
      setDatasets(dList);
      if (dList.length > 0 && !selectedDatasetId) {
        setSelectedDatasetId(dList[0].id);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load watches");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateWatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDatasetId) {
      setCreateError("Please select a dataset.");
      return;
    }

    setCreating(true);
    setCreateError(null);
    try {
      await api.createWatch({
        dataset_id: selectedDatasetId,
        schedule,
        drift_threshold: driftThreshold,
        enabled: true,
      });
      setShowCreateModal(false);
      fetchData();
    } catch (err: any) {
      setCreateError(err?.message || "Failed to create watch");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteWatch = async (id: string) => {
    try {
      await api.deleteWatch(id);
      setWatches((prev) => prev.filter((w) => w.id !== id));
    } catch (err: any) {
      setError(err?.message || "Failed to delete watch");
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center space-x-3">
            <Clock className="w-8 h-8 text-cyan-400" />
            <span>Dataset Monitoring & Drift Watches</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Automated drift detection via Celery beat. Spawns investigations when distribution drift exceeds thresholds.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="px-5 py-2.5 rounded-xl font-semibold bg-gradient-to-r from-cyan-500 to-violet-600 text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center space-x-2 text-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Create Watch</span>
        </button>
      </div>

      {error && (
        <div className="p-4 mb-6 rounded-xl bg-rose-950/50 border border-rose-500/30 text-rose-300 text-sm flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-slate-400">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm">Loading watches...</p>
        </div>
      ) : watches.length === 0 ? (
        <div className="p-12 rounded-2xl border border-slate-800 bg-slate-900/30 text-center">
          <Clock className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">No active drift watches</h3>
          <p className="text-xs text-slate-500 mt-1">Create a watch to monitor datasets on a recurring schedule.</p>
        </div>
      ) : (
        <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl overflow-hidden backdrop-blur">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/50 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-4 px-6">Dataset ID</th>
                  <th className="py-4 px-6">Schedule</th>
                  <th className="py-4 px-6">Drift Threshold</th>
                  <th className="py-4 px-6">Status</th>
                  <th className="py-4 px-6">Last Checked</th>
                  <th className="py-4 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-sm font-mono">
                {watches.map((w) => (
                  <tr key={w.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-4 px-6 text-white font-semibold">{w.dataset_id}</td>
                    <td className="py-4 px-6 text-slate-300 font-sans">{w.schedule}</td>
                    <td className="py-4 px-6 text-cyan-400 font-bold">{w.drift_threshold}</td>
                    <td className="py-4 px-6">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-950 text-emerald-400 border border-emerald-500/30">
                        {w.enabled ? "Active" : "Disabled"}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-slate-400 text-xs">
                      {w.last_checked_at ? new Date(w.last_checked_at).toLocaleString() : "Never"}
                    </td>
                    <td className="py-4 px-6 text-right">
                      <button
                        onClick={() => handleDeleteWatch(w.id)}
                        className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 transition-colors"
                        title="Delete watch"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal for creating a watch */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Create Dataset Watch</h3>

            {createError && (
              <div className="p-3 mb-4 rounded-xl bg-rose-950/50 border border-rose-500/30 text-rose-300 text-xs">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateWatch} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Target Dataset
                </label>
                <select
                  value={selectedDatasetId}
                  onChange={(e) => setSelectedDatasetId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-400"
                >
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.id.substring(0, 8)}...)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Schedule (cron or alias)
                </label>
                <input
                  type="text"
                  value={schedule}
                  onChange={(e) => setSchedule(e.target.value)}
                  placeholder="@daily, */5 * * * *"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Drift Threshold (PSI / KS)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="1.00"
                  value={driftThreshold}
                  onChange={(e) => setDriftThreshold(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl text-slate-400 hover:text-white text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold transition-all disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Save Watch"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
