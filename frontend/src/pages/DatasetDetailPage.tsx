import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Play, Download, History, AlertCircle, FileSpreadsheet, ArrowLeft, GitFork } from "lucide-react";
import { api, DatasetVersionItem } from "../api/client";

export const DatasetDetailPage: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();

  const [versions, setVersions] = useState<DatasetVersionItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [startingInv, setStartingInv] = useState<boolean>(false);
  const [invError, setInvError] = useState<string | null>(null);

  const fetchVersions = async () => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDatasetVersions(datasetId);
      setVersions(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load versions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVersions();
  }, [datasetId]);

  const handleStartInvestigation = async () => {
    if (!datasetId) return;
    setStartingInv(true);
    setInvError(null);
    try {
      const res = await api.createInvestigation(datasetId);
      navigate(`/investigations/${res.investigation_id}`);
    } catch (err: any) {
      setInvError(err?.message || "Failed to start investigation");
    } finally {
      setStartingInv(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <button
        onClick={() => navigate("/datasets")}
        className="inline-flex items-center space-x-2 text-xs font-semibold text-slate-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to datasets</span>
      </button>

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center space-x-3">
            <span>Dataset Versions</span>
          </h1>
          <p className="text-slate-400 text-xs font-mono mt-1">Dataset ID: {datasetId}</p>
        </div>

        <button
          onClick={handleStartInvestigation}
          disabled={startingInv || versions.length === 0}
          className="px-6 py-3 rounded-xl font-semibold bg-gradient-to-r from-cyan-500 to-violet-600 text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center space-x-2 disabled:opacity-50"
        >
          {startingInv ? (
            <span className="flex items-center space-x-2">
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              <span>Launching Investigation...</span>
            </span>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>Investigate</span>
            </>
          )}
        </button>
      </div>

      {invError && (
        <div className="p-4 mb-6 rounded-xl bg-rose-950/50 border border-rose-500/30 text-rose-300 text-sm flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{invError}</span>
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-slate-400">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm">Fetching versions...</p>
        </div>
      ) : error ? (
        <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-sm flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Error loading dataset versions</p>
            <p className="text-xs text-rose-400 mt-1">{error}</p>
          </div>
        </div>
      ) : versions.length === 0 ? (
        <div className="p-12 rounded-2xl border border-slate-800 bg-slate-900/30 text-center">
          <History className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">No versions available</h3>
        </div>
      ) : (
        <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl overflow-hidden backdrop-blur">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/50 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-4 px-6">Version</th>
                  <th className="py-4 px-6">Source File</th>
                  <th className="py-4 px-6">Rows × Cols</th>
                  <th className="py-4 px-6">File Size</th>
                  <th className="py-4 px-6">Parent Version</th>
                  <th className="py-4 px-6">SHA-256</th>
                  <th className="py-4 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-sm">
                {versions.map((ver) => (
                  <tr key={ver.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-4 px-6">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-white">v{ver.version_number}</span>
                        {ver.is_original && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-cyan-950/60 text-cyan-400 border border-cyan-500/30">
                            Original
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-4 px-6">
                      <div className="flex items-center space-x-2 text-slate-200 font-medium">
                        <FileSpreadsheet className="w-4 h-4 text-slate-400 flex-shrink-0" />
                        <span className="truncate max-w-[200px]">{ver.source_name}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-slate-300">
                      {ver.row_count.toLocaleString()} rows × {ver.column_count} cols
                    </td>
                    <td className="py-4 px-6 text-slate-400 font-mono text-xs">
                      {ver.file_size_bytes ? `${(ver.file_size_bytes / 1024).toFixed(1)} KB` : "—"}
                    </td>
                    <td className="py-4 px-6">
                      {ver.parent_version_id ? (
                        <div className="flex items-center space-x-1.5 text-xs text-violet-400 font-mono">
                          <GitFork className="w-3.5 h-3.5" />
                          <span title={ver.parent_version_id}>
                            {ver.parent_version_id.substring(0, 8)}...
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-600 font-mono">—</span>
                      )}
                    </td>
                    <td className="py-4 px-6">
                      <span className="text-[11px] font-mono text-slate-500" title={ver.sha256}>
                        {ver.sha256.substring(0, 12)}...
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <a
                        href={api.getDownloadUrl(ver.id)}
                        download
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Download</span>
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
