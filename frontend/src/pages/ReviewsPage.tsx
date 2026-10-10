import React, { useState, useEffect, useCallback } from "react";
import { CheckCircle2, XCircle, Edit3, AlertCircle, ShieldAlert, CornerDownLeft } from "lucide-react";
import { api, ReviewItem } from "../api/client";

export const ReviewsPage: React.FC = () => {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Inline editing state
  const [editingReviewId, setEditingReviewId] = useState<string | null>(null);
  const [editJson, setEditJson] = useState<string>("{}");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchReviews = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getReviews("pending");
      setReviews(data);
      if (selectedIndex >= data.length) {
        setSelectedIndex(Math.max(0, data.length - 1));
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load pending reviews");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReviews();
  }, []);

  const handleDecision = async (
    review: ReviewItem,
    decision: "approve" | "edit" | "reject",
    parameters?: Record<string, unknown>
  ) => {
    setError(null);
    setActionSuccess(null);
    try {
      await api.submitReviewDecision(review.review_id, decision, parameters);
      setActionSuccess(`Review ${review.review_id.substring(0, 8)}: ${decision} succeeded.`);
      setEditingReviewId(null);
      fetchReviews();
    } catch (err: any) {
      setError(err?.message || `Failed to submit ${decision}`);
    }
  };

  // Keyboard navigation and shortcuts (A, E, R, Arrow keys)
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Don't trigger shortcuts if user is typing inside textarea or input
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
        if (e.key === "Escape") {
          setEditingReviewId(null);
        }
        return;
      }

      if (reviews.length === 0) return;
      const currentReview = reviews[selectedIndex];
      if (!currentReview) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(reviews.length - 1, prev + 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(0, prev - 1));
      } else if (e.key === "a" || e.key === "A") {
        e.preventDefault();
        handleDecision(currentReview, "approve");
      } else if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        handleDecision(currentReview, "reject");
      } else if (e.key === "e" || e.key === "E") {
        e.preventDefault();
        setEditingReviewId(currentReview.review_id);
        setEditJson(JSON.stringify(currentReview.parameters || {}, null, 2));
      }
    },
    [reviews, selectedIndex]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const handleSaveEdit = (review: ReviewItem) => {
    try {
      const parsed = JSON.parse(editJson);
      handleDecision(review, "edit", parsed);
    } catch (err: any) {
      setJsonError(`Invalid JSON: ${err?.message}`);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center space-x-3">
            <ShieldAlert className="w-8 h-8 text-amber-400" />
            <span>Human Review Inbox</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Review escalated cleaning proposals. All decisions update the state machine directly.
          </p>
        </div>
      </div>

      {/* Visible Keyboard Shortcuts Hint Bar */}
      <div
        data-testid="shortcuts-hint"
        className="p-4 mb-8 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-wrap items-center justify-between gap-4 text-xs font-mono backdrop-blur"
      >
        <span className="text-slate-400 font-semibold uppercase tracking-wider font-sans">
          Keyboard Shortcuts:
        </span>
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 border border-slate-700">
            <kbd className="font-bold text-emerald-400">A</kbd>
            <span className="text-slate-400">Approve</span>
          </span>
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 border border-slate-700">
            <kbd className="font-bold text-cyan-400">E</kbd>
            <span className="text-slate-400">Edit JSON</span>
          </span>
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 border border-slate-700">
            <kbd className="font-bold text-rose-400">R</kbd>
            <span className="text-slate-400">Reject</span>
          </span>
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 border border-slate-700">
            <kbd className="font-bold text-violet-400">&uarr; &darr;</kbd>
            <span className="text-slate-400">Navigate</span>
          </span>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-4 mb-6 rounded-xl bg-emerald-950/50 border border-emerald-500/30 text-emerald-300 text-sm">
          {actionSuccess}
        </div>
      )}

      {error && (
        <div className="p-4 mb-6 rounded-xl bg-rose-950/50 border border-rose-500/30 text-rose-300 text-sm flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-slate-400">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm">Loading pending reviews...</p>
        </div>
      ) : reviews.length === 0 ? (
        <div className="p-12 rounded-2xl border border-slate-800 bg-slate-900/30 text-center">
          <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">No pending reviews</h3>
          <p className="text-xs text-slate-500 mt-1">All escalated proposals have been reviewed.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {reviews.map((review, idx) => {
            const isSelected = selectedIndex === idx;
            const isEditing = editingReviewId === review.review_id;

            return (
              <div
                key={review.review_id}
                onClick={() => setSelectedIndex(idx)}
                data-testid={`review-card-${idx}`}
                className={`p-6 rounded-2xl border transition-all cursor-pointer ${
                  isSelected
                    ? "bg-slate-900/90 border-cyan-500/60 shadow-lg shadow-cyan-500/10 ring-1 ring-cyan-500/40"
                    : "bg-slate-900/40 border-slate-800/80 hover:border-slate-700"
                }`}
              >
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-950 text-amber-400 border border-amber-500/30">
                        {review.status}
                      </span>
                      <span className="text-xs font-mono text-slate-400">
                        Proposal: {review.proposal_id}
                      </span>
                    </div>
                    <h3 className="text-base font-semibold text-white mt-2">
                      {review.proposal_summary || "Escalated proposal awaiting human inspection"}
                    </h3>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDecision(review, "approve");
                      }}
                      data-testid={`btn-approve-${idx}`}
                      className="px-3 py-1.5 rounded-lg bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-500/40 text-emerald-300 text-xs font-semibold flex items-center space-x-1 transition-colors"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Approve (A)</span>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingReviewId(review.review_id);
                        setEditJson(JSON.stringify(review.parameters || {}, null, 2));
                      }}
                      data-testid={`btn-edit-${idx}`}
                      className="px-3 py-1.5 rounded-lg bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-500/40 text-cyan-300 text-xs font-semibold flex items-center space-x-1 transition-colors"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>Edit (E)</span>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDecision(review, "reject");
                      }}
                      data-testid={`btn-reject-${idx}`}
                      className="px-3 py-1.5 rounded-lg bg-rose-950/80 hover:bg-rose-900 border border-rose-500/40 text-rose-300 text-xs font-semibold flex items-center space-x-1 transition-colors"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Reject (R)</span>
                    </button>
                  </div>
                </div>

                {/* Inline JSON Editor when in edit mode */}
                {isEditing ? (
                  <div
                    onClick={(e) => e.stopPropagation()}
                    className="mt-4 p-4 rounded-xl bg-slate-950 border border-cyan-500/40 space-y-3"
                  >
                    <label className="block text-xs font-mono text-cyan-300">
                      Edit Parameters JSON:
                    </label>
                    <textarea
                      value={editJson}
                      onChange={(e) => {
                        setEditJson(e.target.value);
                        setJsonError(null);
                      }}
                      rows={6}
                      data-testid={`edit-json-${idx}`}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-400"
                    />
                    {jsonError && (
                      <p className="text-xs text-rose-400 font-mono">{jsonError}</p>
                    )}
                    <div className="flex items-center justify-end space-x-2">
                      <button
                        onClick={() => setEditingReviewId(null)}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-medium hover:bg-slate-700"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleSaveEdit(review)}
                        data-testid={`btn-save-edit-${idx}`}
                        className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold transition-colors"
                      >
                        Submit Edit
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-3 p-3 rounded-xl bg-slate-950/50 border border-slate-800/80">
                    <span className="text-[11px] font-semibold text-slate-500 block mb-1">
                      Current Parameters:
                    </span>
                    <pre className="text-xs font-mono text-slate-300 overflow-x-auto">
                      {JSON.stringify(review.parameters || {}, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
