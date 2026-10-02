"use client";

import React, { useState } from "react";
import { Brain, CheckCircle2, RefreshCw } from "lucide-react";
import { API_BASE, getToken } from "@/lib/api";

interface PublishModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
}

export default function PublishModal({
  isOpen,
  onClose,
  projectId,
}: PublishModalProps) {
  const [hfPublishing, setHfPublishing] = useState(false);
  const [hfRepoUrl, setHfRepoUrl] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  if (!isOpen) return null;

  const handlePublish = async () => {
    setHfPublishing(true);
    setErrorMsg("");
    try {
      const token = getToken();
      const response = await fetch(`${API_BASE}/projects/${projectId}/publish/hf`, {
        method: "POST",
        credentials: "include",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || "Hugging Face upload failed");
      }
      const data = await response.json();
      setHfRepoUrl(data.repository_url);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to publish research outputs";
      setErrorMsg(msg);
    } finally {
      setHfPublishing(false);
    }
  };

  const handleClose = () => {
    setHfRepoUrl("");
    setErrorMsg("");
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="hf-modal-title"
      className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"
    >
      <div className="bg-card border border-card-border/85 w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-4 animate-scale-up">
        <div className="flex items-center justify-between border-b border-card-border/50 pb-3">
          <h3 id="hf-modal-title" className="text-sm font-bold text-slate-200 flex items-center gap-2">
            <Brain className="w-5 h-5 text-indigo-400" />
            <span>Publish to Hugging Face Hub</span>
          </h3>
          <button
            type="button"
            onClick={handleClose}
            className="text-slate-500 hover:text-slate-300 text-sm font-bold font-mono p-1 rounded hover:bg-slate-800"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {errorMsg && (
          <div className="p-3 bg-error/15 border border-error/30 rounded-lg text-xs text-error font-medium">
            {errorMsg}
          </div>
        )}

        {!hfRepoUrl ? (
          <>
            <p className="text-xs text-slate-400 leading-relaxed">
              Export and publish this project's research outputs to the Hugging Face Hub.
              This packages the following artifacts:
            </p>
            <ul className="list-disc pl-4 space-y-1 text-[11px] text-slate-300 font-mono">
              <li>Model Card (README.md) with abstract & evaluations</li>
              <li>Hyperparameter configs (config.yaml)</li>
              <li>Training metrics histories and logs</li>
              <li>Trained PyTorch Model Weights & Checkpoints</li>
            </ul>
            <div className="bg-indigo-950/20 border border-indigo-500/20 rounded-lg p-3 text-[10px] text-indigo-300 leading-normal">
              Note: Research models will be published under the <strong>arsa-ai</strong> community organization.
            </div>
            <div className="flex gap-3 justify-end pt-2">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 rounded-lg border border-card-border hover:bg-slate-800 text-xs font-semibold text-slate-400 min-h-[38px]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePublish}
                disabled={hfPublishing}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold disabled:opacity-50 flex items-center gap-1.5 min-h-[38px]"
              >
                {hfPublishing ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Uploading...</span>
                  </>
                ) : (
                  <span>Publish Now</span>
                )}
              </button>
            </div>
          </>
        ) : (
          <div className="space-y-4 text-center py-4">
            <div className="w-12 h-12 bg-success/15 rounded-full flex items-center justify-center mx-auto border border-success/30">
              <CheckCircle2 className="w-6 h-6 text-success" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-200">Upload Complete!</h4>
              <p className="text-xs text-slate-400 mt-1">Your research project has been successfully published.</p>
            </div>
            <a
              href={hfRepoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition-colors shadow-lg shadow-indigo-600/25"
            >
              View Repository on Hugging Face
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
