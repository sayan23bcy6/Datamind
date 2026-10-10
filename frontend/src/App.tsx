import { useEffect, useRef, useState } from "react";

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  `${window.location.protocol}//${window.location.hostname}:8000`;

async function fetchWithRetry(
  url: string,
  options?: RequestInit,
  attempts = 10,
): Promise<Response> {
  let lastError: unknown;
  const method = (options?.method || "GET").toUpperCase();
  const retryable =
    method === "GET" || method === "HEAD" || method === "OPTIONS";

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const response = await fetch(url, options);
      if (response.ok || !retryable || attempt === attempts - 1) {
        return response;
      }
    } catch (error) {
      lastError = error;
      if (!retryable || attempt === attempts - 1) {
        throw error;
      }
    }

    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  throw lastError instanceof Error
    ? lastError
    : new Error("The backend request failed.");
}

type Health = {
  status?: string;
  service?: string;
  environment?: string;
};

type Dataset = {
  id: string;
  name: string;
  created_at: string;
};

type DatasetVersion = {
  id: string;
  version_number: number;
  source_name: string;
  row_count: number;
  column_count: number;
  file_size_bytes: number;
  created_at: string;
};

export default function App() {
  const [status, setStatus] = useState("Checking backend...");
  const [health, setHealth] = useState<Health | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [versions, setVersions] = useState<DatasetVersion[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [datasetName, setDatasetName] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const pipelineRef = useRef<HTMLDivElement>(null);

  async function loadDatasets() {
    const response = await fetchWithRetry(`${API_BASE_URL}/api/v1/datasets`);
    if (!response.ok) {
      throw new Error("Datasets could not be loaded.");
    }

    const payload = (await response.json()) as Dataset[];
    setDatasets(payload);
    return payload;
  }

  async function selectDataset(dataset: Dataset) {
    setSelectedDataset(dataset);
    setVersions([]);
    setActionMessage("");

    try {
      const response = await fetchWithRetry(
        `${API_BASE_URL}/api/v1/datasets/${dataset.id}/versions`,
      );
      if (!response.ok) {
        throw new Error("Dataset versions could not be loaded.");
      }
      setVersions((await response.json()) as DatasetVersion[]);
    } catch (error) {
      setActionMessage(
        error instanceof Error ? error.message : "The request failed.",
      );
    }
  }

  useEffect(() => {
    async function initializeHealth() {
      try {
        const healthResponse = await fetchWithRetry(
          `${API_BASE_URL}/api/v1/health`,
        );
        const healthPayload = (await healthResponse.json()) as Health;
        if (!healthResponse.ok) {
          throw new Error("The backend health check failed.");
        }
        setHealth(healthPayload);
        setStatus("Backend ready");
      } catch {
        setStatus("Backend unreachable");
        setHealth(null);
        setActionMessage(
          "The backend health check failed. Check Docker and try again.",
        );
      }
    }

    async function initializeDatasets() {
      try {
        const loadedDatasets = await loadDatasets();
        if (loadedDatasets.length > 0) {
          await selectDataset(loadedDatasets[0]);
        }
      } catch (error) {
        setActionMessage(
          error instanceof Error
            ? error.message
            : "Datasets could not be loaded.",
        );
      }
    }

    void initializeHealth();
    void initializeDatasets();
  }, []);

  async function uploadDataset(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      setActionMessage("Choose a CSV or Excel file first.");
      return;
    }

    setIsBusy(true);
    setActionMessage("");
    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("dataset_name", datasetName);

    try {
      const response = await fetchWithRetry(
        `${API_BASE_URL}/api/v1/datasets/upload`,
        { method: "POST", body: formData },
      );
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "The dataset could not be uploaded.");
      }

      const loadedDatasets = await loadDatasets();
      const uploadedDataset = loadedDatasets.find(
        (dataset) => dataset.id === payload.dataset_id,
      );
      if (uploadedDataset) {
        await selectDataset(uploadedDataset);
      }
      setSelectedFile(null);
      setDatasetName("");
      setActionMessage(
        `Uploaded ${payload.file_name}: ${payload.row_count} rows, ${payload.column_count} columns.`,
      );
    } catch (error) {
      setActionMessage(
        error instanceof Error ? error.message : "The upload failed.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  async function createDemoDataset(action: string) {
    setIsBusy(true);
    setActionMessage("");

    try {
      const response = await fetchWithRetry(
        `${API_BASE_URL}/api/v1/datasets/demo`,
        { method: "POST" },
      );
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(
          payload.detail || "The demo dataset could not be created.",
        );
      }

      const loadedDatasets = await loadDatasets();
      const demoDataset = loadedDatasets.find(
        (dataset) => dataset.id === payload.dataset_id,
      );
      if (demoDataset) {
        await selectDataset(demoDataset);
      }
      setActionMessage(`${action}: ${payload.message}`);
    } catch (error) {
      setActionMessage(
        error instanceof Error ? error.message : "The request failed.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex max-w-6xl flex-col px-6 py-12 sm:py-16">
        <header className="mb-12 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">
              Autonomous data quality
            </p>
            <h1 className="mt-3 text-4xl font-black tracking-tight sm:text-5xl">
              DataMind
            </h1>
          </div>
          <button
            className="rounded-full border border-cyan-400/40 bg-cyan-400/10 px-5 py-2.5 text-sm font-medium text-cyan-200 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isBusy}
            onClick={() => void createDemoDataset("Demo dataset")}
          >
            {isBusy ? "Working..." : "Try the demo dataset"}
          </button>
        </header>

        <section className="grid gap-8 lg:grid-cols-[1.4fr_0.6fr] lg:items-center">
          <div>
            <p className="inline-flex rounded-full border border-violet-400/40 bg-violet-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-violet-200">
              LLM reasoning + deterministic checks
            </p>
            <h2 className="mt-6 max-w-xl text-5xl font-black leading-tight tracking-tight text-white">
              Detect issues. Explain them. Verify the fix.
            </h2>
            <p className="mt-5 max-w-xl text-lg text-slate-300">
              Upload a messy CSV or spreadsheet, inspect its versions, and
              prepare it for quality analysis.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <button
                className="rounded-xl bg-gradient-to-r from-violet-500 to-cyan-500 px-5 py-3 font-semibold text-white shadow-xl shadow-violet-900/20 transition hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isBusy}
                onClick={() => void createDemoDataset("Demo dataset")}
              >
                {isBusy ? "Preparing..." : "Start with demo data"}
              </button>
              <button
                className="rounded-xl border border-slate-700 bg-slate-900/70 px-5 py-3 font-semibold text-slate-200 transition hover:border-cyan-400/50"
                onClick={() =>
                  pipelineRef.current?.scrollIntoView({ behavior: "smooth" })
                }
              >
                View pipeline
              </button>
            </div>
            {actionMessage ? (
              <p className="mt-4 text-sm text-cyan-200" role="status">
                {actionMessage}
              </p>
            ) : null}
          </div>

          <div
            ref={pipelineRef}
            className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl shadow-slate-950/50 backdrop-blur"
          >
            <div className="mb-5 flex items-center justify-between gap-3">
              <span className="text-sm font-medium text-slate-300">
                Pipeline status
              </span>
              <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-300">
                {status}
              </span>
            </div>
            <div className="space-y-4">
              {[
                [
                  "Profile data",
                  datasets.length ? "Ready" : "Waiting for data",
                ],
                ["Investigate issues", "Queued"],
                ["Critic review", "Queued"],
                ["Verify repairs", "Queued"],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-xl border border-slate-800 bg-slate-950/60 p-3"
                >
                  <div className="flex items-center justify-between text-sm text-slate-300">
                    <span>{label}</span>
                    <span className="font-medium text-slate-100">{value}</span>
                  </div>
                </div>
              ))}
            </div>
            {health ? (
              <div className="mt-6 rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-3 text-sm text-cyan-100">
                <div>service: {health.service}</div>
                <div>environment: {health.environment}</div>
                <div>status: {health.status}</div>
              </div>
            ) : null}
          </div>
        </section>

        <section className="mt-12 grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">
                  Workspace
                </p>
                <h2 className="mt-2 text-2xl font-bold text-white">
                  Add a dataset
                </h2>
              </div>
              <span className="text-xs text-slate-400">CSV, XLSX, XLS</span>
            </div>
            <form className="space-y-4" onSubmit={uploadDataset}>
              <label className="block text-sm text-slate-300">
                Dataset name <span className="text-slate-500">(optional)</span>
                <input
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none transition focus:border-cyan-400"
                  value={datasetName}
                  onChange={(event) => setDatasetName(event.target.value)}
                  placeholder="Customer records"
                />
              </label>
              <label className="block text-sm text-slate-300">
                Data file
                <input
                  className="mt-2 block w-full cursor-pointer rounded-lg border border-dashed border-slate-600 bg-slate-950 px-3 py-3 text-sm text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-cyan-400/15 file:px-3 file:py-2 file:text-cyan-200"
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={(event) =>
                    setSelectedFile(event.target.files?.[0] ?? null)
                  }
                />
              </label>
              <button
                className="w-full rounded-lg bg-cyan-400 px-4 py-2.5 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
                type="submit"
                disabled={isBusy || !selectedFile}
              >
                {isBusy ? "Uploading..." : "Upload dataset"}
              </button>
            </form>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-300">
                  Data catalog
                </p>
                <h2 className="mt-2 text-2xl font-bold text-white">
                  Your datasets
                </h2>
              </div>
              <button
                className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 transition hover:border-cyan-400/50"
                onClick={() =>
                  void loadDatasets().catch((error) =>
                    setActionMessage(error.message),
                  )
                }
              >
                Refresh
              </button>
            </div>
            {datasets.length === 0 ? (
              <p className="rounded-xl border border-dashed border-slate-700 p-6 text-sm text-slate-400">
                No datasets yet. Upload a file or start with the demo dataset.
              </p>
            ) : (
              <div className="space-y-3">
                {datasets.map((dataset) => (
                  <button
                    key={dataset.id}
                    className={`w-full rounded-xl border p-4 text-left transition ${selectedDataset?.id === dataset.id ? "border-cyan-400/70 bg-cyan-400/10" : "border-slate-800 bg-slate-950/60 hover:border-slate-600"}`}
                    onClick={() => void selectDataset(dataset)}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium text-slate-100">
                        {dataset.name}
                      </span>
                      <span className="text-xs text-slate-500">
                        {new Date(dataset.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>

        {selectedDataset ? (
          <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">
                  Selected dataset
                </p>
                <h2 className="mt-2 text-2xl font-bold text-white">
                  {selectedDataset.name}
                </h2>
              </div>
              <span className="text-sm text-slate-400">
                {versions.length} version{versions.length === 1 ? "" : "s"}
              </span>
            </div>
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[540px] text-left text-sm">
                <thead className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="pb-3 pr-4">Version</th>
                    <th className="pb-3 pr-4">Source</th>
                    <th className="pb-3 pr-4">Rows</th>
                    <th className="pb-3 pr-4">Columns</th>
                    <th className="pb-3">Size</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((version) => (
                    <tr
                      key={version.id}
                      className="border-b border-slate-800/70 text-slate-300"
                    >
                      <td className="py-3 pr-4 font-medium text-white">
                        v{version.version_number}
                      </td>
                      <td className="py-3 pr-4">{version.source_name}</td>
                      <td className="py-3 pr-4">
                        {version.row_count.toLocaleString()}
                      </td>
                      <td className="py-3 pr-4">{version.column_count}</td>
                      <td className="py-3">
                        {(version.file_size_bytes / 1024).toFixed(1)} KB
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}
