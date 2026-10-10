import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { BrowserRouter, MemoryRouter, Routes, Route } from "react-router-dom";
import { DatasetsPage } from "../pages/DatasetsPage";
import { LandingPage } from "../pages/LandingPage";
import { ReviewsPage } from "../pages/ReviewsPage";
import { InvestigationPage } from "../pages/InvestigationPage";
import { api } from "../api/client";

// Mock API client
vi.mock("../api/client", () => {
  return {
    api: {
      getHealth: vi.fn().mockResolvedValue({
        status: "ok",
        service: "DataMind",
        environment: "test",
        postgres: "ok",
        redis: "ok",
      }),
      getDatasets: vi.fn().mockResolvedValue([
        { id: "ds-1", name: "Customer Dataset", created_at: "2026-10-10T10:00:00Z" },
      ]),
      uploadDataset: vi.fn().mockResolvedValue({
        dataset_id: "ds-1",
        version_id: "ver-1",
        dataset_name: "Test",
        file_name: "test.csv",
        row_count: 20,
        column_count: 5,
        sha256: "abc",
      }),
      createDemoDataset: vi.fn().mockResolvedValue({
        dataset_id: "ds-demo",
        version_id: "ver-demo",
        message: "Demo created",
        created: true,
      }),
      getDatasetVersions: vi.fn().mockResolvedValue([]),
      getVersionProfile: vi.fn().mockResolvedValue({
        row_count: 25,
        column_count: 8,
        columns: [],
        dimensions: {
          completeness: 95.0,
          uniqueness: 90.0,
          consistency: 92.0,
          validity: 98.0,
          accuracy: 96.0,
          overall: 94.2,
        },
      }),
      getInvestigation: vi.fn().mockResolvedValue({
        investigation_id: "inv-100",
        status: "completed",
        state: "COMPLETED",
        iteration: 1,
        max_iterations: 3,
        cost_used: 1250,
        cost_budget: 200000,
        dataset_version_id: "ver-1",
        output_version_id: "ver-2",
        error: null,
      }),
      getInvestigationProposals: vi.fn().mockResolvedValue([
        {
          type: "proposal",
          iteration: 1,
          proposal_id: "prop-1",
          operation: "deduplicate",
          target_columns: ["customer_id"],
          parameters: {},
          rationale: "Exact duplicates found",
          confidence: 0.95,
          confidence_basis: "Hash equality",
        },
        {
          type: "verdict",
          proposal_id: "prop-1",
          verdict: "APPROVE",
          reasons: ["Verified identical rows"],
          unsupported_assumptions: [],
          created_at: "2026-10-10T10:01:00Z",
        },
        {
          type: "verdict",
          proposal_id: "prop-2",
          verdict: "REJECT",
          reasons: ["Threshold too aggressive"],
          unsupported_assumptions: ["Assumes normal distribution"],
          created_at: "2026-10-10T10:02:00Z",
        },
        {
          type: "verdict",
          proposal_id: "prop-3",
          verdict: "ESCALATE_TO_HUMAN",
          reasons: ["Severe outlier requires human review"],
          unsupported_assumptions: [],
          created_at: "2026-10-10T10:03:00Z",
        },
      ]),
      getInvestigationDiff: vi.fn().mockResolvedValue([
        {
          column: "customer_id",
          row_index: 2,
          original_row_index: 2,
          change_type: "removed",
          original_value: "C-101",
          new_value: null,
          rule: "Exact duplicate elimination",
          confidence: 1.0,
          confidence_basis: "Identical hash",
        },
      ]),
      getInvestigationDistributions: vi.fn().mockResolvedValue([
        {
          column: "transaction_amount",
          before_bins: [10, 5, 2],
          after_bins: [10, 5, 0],
          ks_statistic: 0.05,
          p_value: 0.98,
          passed: true,
        },
      ]),
      getInvestigationEvidence: vi.fn().mockResolvedValue([
        {
          evidence_id: "ev-1",
          claim: "Planted duplicate rows removed.",
          test_name: "detect_duplicates",
          statistic: "2",
          p_value: "0.00",
          details: {},
        },
      ]),
      getInvestigationAudit: vi.fn().mockResolvedValue({
        investigation_id: "inv-100",
        audit_trail: [
          { type: "state_transition", state: "PROFILE", timestamp: "2026-10-10T10:00:00Z" },
        ],
      }),
      getReportDownloadUrl: vi.fn().mockReturnValue("http://localhost/report"),
      getDownloadUrl: vi.fn().mockReturnValue("http://localhost/download"),
      getEventsUrl: vi.fn().mockReturnValue("http://localhost/events"),
      getReviews: vi.fn().mockResolvedValue([
        {
          review_id: "rev-1",
          investigation_id: "inv-100",
          proposal_id: "prop-3",
          status: "pending",
          proposal_summary: "High value transaction outlier",
          parameters: { threshold: 50000 },
        },
      ]),
      submitReviewDecision: vi.fn().mockResolvedValue({
        status: "ok",
        review_id: "rev-1",
        decision: "approve",
      }),
      getWatches: vi.fn().mockResolvedValue([]),
      createWatch: vi.fn().mockResolvedValue({}),
      deleteWatch: vi.fn().mockResolvedValue({}),
    },
  };
});

describe("DataMind Frontend Test Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1. Dropzone rejects non-CSV/XLSX files
  it("dropzone rejects non-CSV files before upload", async () => {
    render(
      <BrowserRouter>
        <DatasetsPage />
      </BrowserRouter>
    );

    const fileInput = screen.getByTestId("file-input");
    const badFile = new File(["dummy content"], "manual.pdf", { type: "application/pdf" });

    fireEvent.change(fileInput, { target: { files: [badFile] } });

    await waitFor(() => {
      expect(screen.getByTestId("upload-error")).toBeInTheDocument();
      expect(screen.getByText("Only CSV, XLSX, and XLS files are supported.")).toBeInTheDocument();
    });

    // Verify uploadDataset was NOT called
    expect(api.uploadDataset).not.toHaveBeenCalled();
  });

  // 2. Debate panel renders all three badges from fixtures
  it("debate panel renders all three badges (APPROVE, REJECT, ESCALATE_TO_HUMAN) from fixtures", async () => {
    render(
      <MemoryRouter initialEntries={["/investigations/inv-100"]}>
        <Routes>
          <Route path="/investigations/:id" element={<InvestigationPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Switch to Debate tab
    const debateTab = await screen.findByText("Debate Panel");
    fireEvent.click(debateTab);

    await waitFor(() => {
      expect(screen.getByTestId("verdict-badge-approve")).toHaveTextContent("APPROVE");
      expect(screen.getByTestId("verdict-badge-reject")).toHaveTextContent("REJECT");
      expect(screen.getByTestId("verdict-badge-escalate_to_human")).toHaveTextContent("ESCALATE_TO_HUMAN");
    });
  });

  // 3. Health score ends at the 'after' value
  it("health score ends at the after value", async () => {
    render(
      <MemoryRouter initialEntries={["/investigations/inv-100"]}>
        <Routes>
          <Route path="/investigations/:id" element={<InvestigationPage />} />
        </Routes>
      </MemoryRouter>
    );

    const healthTab = await screen.findByText("Health Score");
    fireEvent.click(healthTab);

    // After animation completes (or immediately with prefers-reduced-motion)
    await waitFor(
      () => {
        const scoreElem = screen.getByTestId("overall-score");
        expect(scoreElem).toHaveTextContent("94.2");
      },
      { timeout: 2000 }
    );
  });

  // 4. Review shortcuts A, E, and R call the decision endpoint with the correct body
  it("review shortcuts A, E, and R call the decision endpoint with the correct body", async () => {
    render(
      <BrowserRouter>
        <ReviewsPage />
      </BrowserRouter>
    );

    await screen.findByText("High value transaction outlier");

    // Press 'A' -> approve
    fireEvent.keyDown(window, { key: "a" });
    await waitFor(() => {
      expect(api.submitReviewDecision).toHaveBeenCalledWith("rev-1", "approve", undefined);
    });

    vi.clearAllMocks();

    // Press 'R' -> reject
    fireEvent.keyDown(window, { key: "r" });
    await waitFor(() => {
      expect(api.submitReviewDecision).toHaveBeenCalledWith("rev-1", "reject", undefined);
    });

    vi.clearAllMocks();

    // Press 'E' -> open edit mode
    fireEvent.keyDown(window, { key: "e" });
    const jsonTextarea = await screen.findByTestId("edit-json-0");
    expect(jsonTextarea).toBeInTheDocument();

    // Modify parameters and click Submit Edit
    fireEvent.change(jsonTextarea, { target: { value: JSON.stringify({ threshold: 60000 }) } });
    const saveButton = screen.getByTestId("btn-save-edit-0");
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(api.submitReviewDecision).toHaveBeenCalledWith("rev-1", "edit", { threshold: 60000 });
    });
  });

  // 5. Pipeline panel shows 'No investigation yet' with no investigation selected
  it("pipeline panel shows 'No investigation yet' with no investigation selected", () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    expect(screen.getByText("No investigation yet")).toBeInTheDocument();
  });

  // 6. Diff viewer renders a removed row
  it("diff viewer renders a removed row", async () => {
    render(
      <MemoryRouter initialEntries={["/investigations/inv-100"]}>
        <Routes>
          <Route path="/investigations/:id" element={<InvestigationPage />} />
        </Routes>
      </MemoryRouter>
    );

    const diffTab = await screen.findByText("Diff Viewer");
    fireEvent.click(diffTab);

    await waitFor(() => {
      const removedRow = screen.getByTestId("diff-row-removed");
      expect(removedRow).toBeInTheDocument();
      expect(removedRow).toHaveTextContent("removed");
      expect(removedRow).toHaveTextContent("C-101");
    });
  });
});
