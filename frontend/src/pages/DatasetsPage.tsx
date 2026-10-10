import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { UploadCloud, RefreshCw, Database, AlertCircle, FileSpreadsheet, ArrowRight } from "lucide-react";
import { api, DatasetItem, UploadResponse } from "../api/client";

export const DatasetsPage: React.FC = () => {
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Upload state
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<UploadResponse | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDatasets = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const data = await api.getDatasets();
      setDatasets(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load datasets");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const validateAndUpload = async (file: File) => {
    setUploadError(null);
    setUploadSuccess(null);

    const name = file.name.toLowerCase();
    const isCsv = name.endsWith(".csv");
    const isXlsx = name.endsWith(".xlsx");
    const isXls = name.endsWith(".xls");

    if (!isCsv && !isXlsx && !isXls) {
      setUploadError("Only CSV, XLSX, and XLS files are supported.");
      return;
    }

    setUploading(true);
    try {
      const res = await api.uploadDataset(file);
      setUploadSuccess(res);
      fetchDatasets(true);
    } catch (err: any) {
      setUploadError(err?.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndUpload(e.target.files[0]);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Datasets</h1>
          <p className="text-slate-400 text-sm mt-1">
            Upload and manage raw datasets. All versions maintain complete immutable ancestry.
          </p>
        </div>
        <button
          onClick={() => fetchDatasets(true)}
          disabled={refreshing}
          className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-sm font-medium flex items-center space-x-2 transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin text-cyan-400" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Upload Dropzone */}
      <div
        data-testid="dropzone"
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-8 mb-10 text-center cursor-pointer transition-all ${
          isDragOver
            ? "border-cyan-400 bg-cyan-950/20 scale-[1.01]"
            : "border-slate-700/80 bg-slate-900/40 hover:border-slate-600 hover:bg-slate-900/60"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileChange}
          className="hidden"
          data-testid="file-input"
        />
        <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-tr from-cyan-500/20 to-violet-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
          <UploadCloud className="w-7 h-7" />
        </div>
        <h3 className="text-base font-semibold text-white mb-1">
          {uploading ? "Uploading dataset..." : "Drop your dataset here, or click to browse"}
        </h3>
        <p className="text-xs text-slate-400 max-w-sm mx-auto">
          Supported file types: <span className="text-slate-300 font-mono">.csv</span>,{" "}
          <span className="text-slate-300 font-mono">.xlsx</span>, <span className="text-slate-300 font-mono">.xls</span>. Non-supported files are rejected before upload.
        </p>

        {uploadError && (
          <div data-testid="upload-error" className="mt-4 p-3 rounded-xl bg-rose-950/50 border border-rose-500/40 text-rose-300 text-xs inline-flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{uploadError}</span>
          </div>
        )}

        {uploadSuccess && (
          <div className="mt-4 p-3 rounded-xl bg-emerald-950/50 border border-emerald-500/40 text-emerald-300 text-xs inline-flex items-center space-x-2">
            <FileSpreadsheet className="w-4 h-4 flex-shrink-0" />
            <span>
              Uploaded "{uploadSuccess.file_name}" ({uploadSuccess.row_count} rows, {uploadSuccess.column_count} cols) successfully!
            </span>
          </div>
        )}
      </div>

      {/* Dataset List */}
      <div>
        <h2 className="text-xl font-bold text-white mb-4">Available Datasets</h2>

        {loading ? (
          <div className="p-12 text-center text-slate-400">
            <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm">Loading datasets from backend...</p>
          </div>
        ) : error ? (
          <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-sm flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Failed to fetch datasets</p>
              <p className="text-xs text-rose-400 mt-1">{error}</p>
            </div>
          </div>
        ) : datasets.length === 0 ? (
          <div className="p-12 rounded-2xl border border-slate-800 bg-slate-900/30 text-center">
            <Database className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-300">No datasets found</h3>
            <p className="text-xs text-slate-500 mt-1">Upload a CSV or XLSX file above to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {datasets.map((dataset) => (
              <Link
                key={dataset.id}
                to={`/datasets/${dataset.id}`}
                className="group p-6 rounded-2xl bg-slate-900/50 hover:bg-slate-900/80 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="w-8 h-8 rounded-lg bg-cyan-950/50 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                      <FileSpreadsheet className="w-4 h-4" />
                    </span>
                    <span className="text-[11px] font-mono text-slate-500">
                      {new Date(dataset.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <h3 className="text-base font-semibold text-white group-hover:text-cyan-400 transition-colors">
                    {dataset.name}
                  </h3>
                  <p className="text-xs font-mono text-slate-500 mt-1 truncate">ID: {dataset.id}</p>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-400 group-hover:text-cyan-400">
                  <span>View versions & run pipeline</span>
                  <ArrowRight className="w-3.5 h-3.5 transform group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
