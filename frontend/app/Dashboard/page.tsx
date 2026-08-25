"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";
import Markdown from "react-markdown";
import Link from "next/link";
import {
  FileText,
  Sparkles,
  HelpCircle,
  BookOpen,
  UploadCloud,
  Trash2,
  Terminal,
  Download,
  RefreshCw,
  AlertCircle,
  Copy,
  Check,
  Zap,
  ShieldAlert,
  Presentation,
  Network,
  Plus,
  LogOut,
} from "lucide-react";

import { QuizArena } from "../components/QuizArena";
import { ChatStream } from "../components/ChatStream";
import { GraphView } from "../components/GraphView";
import { MasterclassStudio } from "../components/MasterclassStudio";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AuditFinding,
  Coverage,
  QuizCardType,
  Slide,
  StudioEnvelopeData,
  StudioKey,
  TelemetryStats,
} from "./types";
import { CoverageNote, EmptyState, ErrorBanner } from "@/components/ui/ErrorBanner";
import { readSseStream } from "@/lib/sse";
import { formatSummaryMarkdown } from "@/lib/formatSummary";
import { AuditPanel } from "./components/AuditPanel";
import { AudioSlidesPanel } from "./components/AudioSlidesPanel";

type View = "quiz" | "summary" | "chat" | "graph" | "masterclass" | "audit" | "audio" | "slides" | "none";
type ProgressEvent = { stamp: string; label: string; tone?: "info" | "warn" };

/**
 * Payload shapes emitted by the backend indexing pipeline's SSE stream.
 * Mirrors microService/app/indexing/pipeline.py — keep in sync.
 */
type IndexEventData = {
  n_chunks?: number;
  n_parents?: number;
  status?: string;
  total?: number;
  sampled_from?: number;
  skipped?: number;
  done?: number;
  stage?: string;
  message?: string;
  chunk_id?: number;
  error?: string;
  doc_hash?: string;
  cached?: boolean;
};
type StoredDocument = {
  doc_hash: string;
  filename: string;
  n_chunks: number;
  created_at: number;
};

const MAX_FILE_MB = 100;
const ACCEPTED_EXTS = [".pdf", ".txt", ".md", ".doc", ".docx"];

function shortHash(h: string | null): string {
  if (!h) return "—";
  return `${h.slice(0, 6)}…${h.slice(-4)}`;
}

function hasAcceptedExt(name: string): boolean {
  const lower = name.toLowerCase();
  return ACCEPTED_EXTS.some((ext) => lower.endsWith(ext));
}

function nowStamp() {
  const d = new Date();
  return `${d.getHours().toString().padStart(2, "0")}:${d
    .getMinutes()
    .toString()
    .padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
}

/**
 * Turns one indexing SSE frame into a log line, or null for frames not worth
 * showing. The backend emits nine distinct event names (chunking, embedding,
 * extracting_graph, graph_progress, warning, detecting_communities,
 * summarizing_communities, community_progress, done) — never a generic
 * "progress" event.
 */
function describeIndexEvent(evt: string, data: IndexEventData): string | null {
  switch (evt) {
    case "chunking":
      return data.n_chunks === undefined
        ? "CHUNKING: splitting document into hierarchical chunks"
        : `CHUNKING: ${data.n_chunks} child chunks across ${data.n_parents} parent chunks`;
    case "embedding":
      return data.status === "waiting"
        ? "EMBEDDING: waiting for the vector index to finish"
        : "EMBEDDING: building vector index";
    case "extracting_graph":
      return data.sampled_from === undefined
        ? `EXTRACTING GRAPH: ${data.total} chunks queued`
        : `EXTRACTING GRAPH: ${data.total} chunks queued (sampled from ${data.sampled_from})`;
    case "graph_progress":
      return `EXTRACTING GRAPH: ${data.done}/${data.total} chunks`;
    case "detecting_communities":
      return "DETECTING COMMUNITIES: running Louvain over the entity graph";
    case "summarizing_communities":
      return data.skipped
        ? `SUMMARIZING COMMUNITIES: ${data.total} queued (${data.skipped} over the cap, skipped)`
        : `SUMMARIZING COMMUNITIES: ${data.total} queued`;
    case "community_progress":
      return `SUMMARIZING COMMUNITIES: ${data.done}/${data.total}`;
    case "warning":
      return `WARNING${data.stage ? ` (${data.stage})` : ""}: ${
        data.message ?? data.error ?? "unspecified"
      }${data.chunk_id === undefined ? "" : ` · chunk ${data.chunk_id}`}`;
    default:
      return null;
  }
}

export default function Dashboard() {
  const [docHash, setDocHash] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<View>("none");

  // Persistent Document Library
  const [libraryDocs, setLibraryDocs] = useState<StoredDocument[]>([]);

  // System Telemetry Stats
  const [telemetryStats, setTelemetryStats] = useState<TelemetryStats | null>(null);

  // Signed-in identity (the dashboard chrome never showed this before, despite
  // the JWT carrying it since signin).
  const [currentUser, setCurrentUser] = useState<{ name?: string; email?: string } | null>(null);

  // Multi-file Intake Queue Management
  const [intakeFiles, setIntakeFiles] = useState<
    Array<{ id: string; name: string; size: number; file: File; status: "queued" | "indexing" | "ready" | "error" }>
  >([]);

  // State for Summary
  const [summary, setSummary] = useState<string>("");
  const [isSummarizing, setIsSummarizing] = useState<boolean>(false);
  const [copiedSummary, setCopiedSummary] = useState<boolean>(false);

  // State for Quiz
  const [quizCards, setQuizCards] = useState<QuizCardType[]>([]);
  const [isQuizLoading, setIsQuizLoading] = useState<boolean>(false);

  // State for Compliance Audit
  const [auditItems, setAuditItems] = useState<AuditFinding[]>([]);
  const [isAuditLoading, setIsAuditLoading] = useState<boolean>(false);

  // State for Audio Briefing
  const [audioScript, setAudioScript] = useState<string>("");
  const [isAudioLoading, setIsAudioLoading] = useState<boolean>(false);
  const [copiedAudio, setCopiedAudio] = useState<boolean>(false);

  // State for Slide Deck
  const [slides, setSlides] = useState<Slide[]>([]);
  const [isSlidesLoading, setIsSlidesLoading] = useState<boolean>(false);

  // Indexing Progress Telemetry
  const [indexing, setIndexing] = useState<boolean>(false);
  const [progressLog, setProgressLog] = useState<ProgressEvent[]>([]);
  const [intakeError, setIntakeError] = useState<string | null>(null);

  // Per-panel failure + sampling disclosure for the four studio artifacts.
  const [studioErrors, setStudioErrors] = useState<Partial<Record<StudioKey, string>>>({});
  const [studioCoverage, setStudioCoverage] = useState<Partial<Record<StudioKey, Coverage>>>({});

  // Focus citation target from chat
  const [focusChunk, setFocusChunk] = useState<number | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Load Library Documents & Telemetry on mount
  const loadLibrary = useCallback(async () => {
    try {
      const res = await axios.get("/api/rag/documents");
      if (res.data.success && res.data.data?.documents) {
        const docs = res.data.data.documents;
        setLibraryDocs(docs);
        if (docs.length > 0 && !docHash) {
          setDocHash(docs[0].doc_hash);
        }
      }
    } catch (err) {
      console.error("Failed to load document library:", err);
    }
  }, [docHash]);

  const loadTelemetry = useCallback(async () => {
    try {
      const res = await axios.get("/api/rag/telemetry");
      if (res.data.success) {
        setTelemetryStats(res.data.data);
      }
    } catch (err) {
      console.error("Failed to load telemetry:", err);
    }
  }, []);

  useEffect(() => {
    loadLibrary();
    loadTelemetry();
    axios
      .get("/api/auth/me")
      .then((res) => setCurrentUser({ name: res.data.name, email: res.data.email }))
      .catch(() => setCurrentUser(null));
  }, [loadLibrary, loadTelemetry]);

  const selectActiveDocument = (hash: string) => {
    setDocHash(hash);
    setSummary("");
    setQuizCards([]);
    setAuditItems([]);
    setAudioScript("");
    setSlides([]);
    setActiveView("summary");
    fetchSummary(hash);
  };

  const deleteLibraryDoc = async (hash: string) => {
    try {
      await axios.delete(`/api/rag/documents/${hash}`);
      setLibraryDocs((prev) => prev.filter((d) => d.doc_hash !== hash));
      if (docHash === hash) {
        setDocHash(null);
        setActiveView("none");
      }
    } catch (err) {
      console.error("Failed to delete document:", err);
    }
  };

  const addFilesToQueue = (filesToAdd: File[]) => {
    setIntakeError(null);
    const valid = filesToAdd.filter((f) => {
      if (!hasAcceptedExt(f.name)) {
        setIntakeError(`Skipped ${f.name} — unsupported file format.`);
        return false;
      }
      if (f.size > MAX_FILE_MB * 1024 * 1024) {
        setIntakeError(`Skipped ${f.name} — exceeds ${MAX_FILE_MB}MB limit.`);
        return false;
      }
      return true;
    });

    if (valid.length === 0) return;

    setIntakeFiles((prev) => {
      const existingNames = new Set(prev.map((p) => p.name));
      const newItems = valid
        .filter((f) => !existingNames.has(f.name))
        .slice(0, 5 - prev.length)
        .map((f) => ({
          id: `file_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          name: f.name,
          size: f.size,
          file: f,
          status: "queued" as const,
        }));
      return [...prev, ...newItems];
    });

  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFilesToQueue(Array.from(e.target.files));
    }
    // Reset so choosing the same file again after removing it still fires.
    e.target.value = "";
  };

  const removeFileFromQueue = (id: string) => {
    setIntakeFiles((prev) => prev.filter((p) => p.id !== id));
  };

  // Must clear the cookie server-side. This used to be a <Link href="/signin">,
  // which navigated away but left the session valid.
  const handleSignOut = async () => {
    try {
      await fetch("/api/auth/signout", { method: "POST" });
    } finally {
      // Full reload so the middleware re-evaluates from a clean state.
      window.location.href = "/signin";
    }
  };

  const triggerUpload = async () => {
    if (intakeFiles.length === 0) return;
    setIndexing(true);
    setIntakeError(null);
    setProgressLog([{ stamp: nowStamp(), label: `Initiating multi-file intake batch (${intakeFiles.length} file(s))` }]);

    const formData = new FormData();
    intakeFiles.forEach((item) => {
      formData.append("files", item.file);
    });

    try {
      const res = await fetch("/api/rag/index", {
        method: "POST",
        body: formData,
      });

      await readSseStream(res, {
        onError: (message) => {
          throw new Error(message);
        },
        onEvent: (evt, data: IndexEventData) => {
          if (evt === "done") {
            const hash = data.doc_hash as string;
            setDocHash(hash);
            setSummary("");
            setQuizCards([]);
            setAuditItems([]);
            setAudioScript("");
            setSlides([]);
            setActiveView("summary");
            fetchSummary(hash);
            loadLibrary();
            loadTelemetry();
            setProgressLog((prev) => [
              ...prev,
              {
                stamp: nowStamp(),
                label: data.cached
                  ? `Already indexed \u00b7 reused cached artifacts \u00b7 Hash ${shortHash(hash)}`
                  : `Indexing complete \u00b7 Hash ${shortHash(hash)}`,
              },
            ]);
            setIntakeFiles((prev) => prev.map((item) => ({ ...item, status: "ready" })));
          } else if (evt === "error") {
            throw new Error(data.message || "Indexing pipeline failure");
          } else {
            const label = describeIndexEvent(evt, data);
            if (label) {
              setProgressLog((prev) => [
                ...prev,
                { stamp: nowStamp(), label, tone: evt === "warning" ? "warn" : "info" },
              ]);
            }
          }
        },
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Pipeline processing failed.";
      setIntakeError(message);
      setProgressLog((prev) => [...prev, { stamp: nowStamp(), label: `ERROR: ${message}` }]);
    } finally {
      setIndexing(false);
    }
  };

  const fetchSummary = async (hash: string) => {
    setIsSummarizing(true);
    setSummary("");
    setStudioErrors((prev) => ({ ...prev, summary: undefined }));
    try {
      const res = await fetch("/api/rag/summary", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ doc_hash: hash }),
      });

      let acc = "";
      await readSseStream(res, {
        onError: (message) =>
          setStudioErrors((prev) => ({ ...prev, summary: message })),
        onEvent: (evt, data: { text?: string; coverage?: Coverage; message?: string }) => {
          if (evt === "token") {
            acc += data.text ?? "";
            setSummary(acc);
          } else if (evt === "done") {
            setStudioCoverage((prev) => ({ ...prev, summary: data.coverage }));
          } else if (evt === "error") {
            setStudioErrors((prev) => ({
              ...prev,
              summary: data.message ?? "Summary generation failed.",
            }));
          }
        },
      });
    } finally {
      setIsSummarizing(false);
    }
  };

  /**
   * One request path for the four studio artifacts, which were previously four
   * byte-identical fetchers that swallowed every failure into console.error.
   * Now that the backend no longer substitutes invented content on error, a
   * failure has to be surfaced or the panel would just sit blank.
   */
  const runStudioFetch = async <T,>(
    key: StudioKey,
    url: string,
    hash: string,
    pick: (data: StudioEnvelopeData) => T,
    apply: (value: T) => void,
    empty: T,
    setLoading: (v: boolean) => void
  ) => {
    setLoading(true);
    apply(empty);
    setStudioErrors((prev) => ({ ...prev, [key]: undefined }));
    setStudioCoverage((prev) => ({ ...prev, [key]: undefined }));
    try {
      const res = await axios.post(url, { doc_hash: hash });
      const body = res.data;
      if (!body?.success) {
        setStudioErrors((prev) => ({
          ...prev,
          [key]: body?.error?.message ?? "The service could not complete this request.",
        }));
        return;
      }
      apply(pick(body.data ?? {}));
      setStudioCoverage((prev) => ({ ...prev, [key]: body.data?.coverage }));
    } catch (err) {
      setStudioErrors((prev) => ({
        ...prev,
        [key]: axios.isAxiosError(err)
          ? `Request failed (${err.response?.status ?? "no response"}). Is the backend running?`
          : "Unexpected error while contacting the service.",
      }));
    } finally {
      setLoading(false);
    }
  };

  const fetchQuiz = (hash: string) =>
    runStudioFetch<QuizCardType[]>(
      "quiz", "/api/rag/quiz", hash,
      (d) => (d.cards as QuizCardType[]) ?? [], setQuizCards, [], setIsQuizLoading
    );

  const fetchComplianceAudit = (hash: string) =>
    runStudioFetch<AuditFinding[]>(
      "audit", "/api/rag/compliance-audit", hash,
      (d) => (d.audit as AuditFinding[]) ?? [], setAuditItems, [], setIsAuditLoading
    );

  const fetchAudioBriefing = (hash: string) =>
    runStudioFetch<string>(
      "audio", "/api/rag/audio-briefing", hash,
      (d) => (d.script as string) ?? "", setAudioScript, "", setIsAudioLoading
    );

  const fetchSlideDeck = (hash: string) =>
    runStudioFetch<Slide[]>(
      "slides", "/api/rag/slide-deck", hash,
      (d) => (d.slides as Slide[]) ?? [], setSlides, [], setIsSlidesLoading
    );

  const handleCardClick = (view: View) => {
    if (!docHash) return;
    setActiveView(view);
    if (view === "summary" && !summary) fetchSummary(docHash);
    if (view === "quiz" && quizCards.length === 0) fetchQuiz(docHash);
    if (view === "audit" && auditItems.length === 0) fetchComplianceAudit(docHash);
    if (view === "audio" && !audioScript) fetchAudioBriefing(docHash);
    if (view === "slides" && slides.length === 0) fetchSlideDeck(docHash);
  };

  const copySummaryToClipboard = () => {
    if (!summary) return;
    navigator.clipboard.writeText(summary);
    setCopiedSummary(true);
    setTimeout(() => setCopiedSummary(false), 2000);
  };

  const downloadSummaryMarkdown = () => {
    if (!summary) return;
    const blob = new Blob([summary], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `DocuMind_Summary_${shortHash(docHash)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const TOOLS: { view: View; label: string; icon: React.ReactNode }[] = [
    { view: "chat", label: "Query Console", icon: <Sparkles className="h-4 w-4" /> },
    { view: "summary", label: "Summary", icon: <FileText className="h-4 w-4" /> },
    { view: "quiz", label: "Quiz Arena", icon: <HelpCircle className="h-4 w-4" /> },
    { view: "masterclass", label: "Masterclass", icon: <BookOpen className="h-4 w-4" /> },
    { view: "graph", label: "Knowledge Atlas", icon: <Network className="h-4 w-4" /> },
    { view: "audit", label: "Compliance Audit", icon: <ShieldAlert className="h-4 w-4" /> },
    { view: "slides", label: "Audio & Slides", icon: <Presentation className="h-4 w-4" /> },
  ];

  const VIEW_TITLES: Record<View, string> = {
    none: "",
    summary: "Summary",
    chat: "Query Console",
    quiz: "Quiz Arena",
    graph: "Knowledge Atlas",
    masterclass: "Masterclass",
    audit: "Compliance Audit",
    audio: "Audio Briefing",
    slides: "Audio & Slide Deck",
  };

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950 text-zinc-100 font-sans selection:bg-white/20">
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={ACCEPTED_EXTS.join(",")}
        onChange={handleFileChange}
        className="hidden"
      />

      {/* ── LEFT SIDEBAR ──────────────────────────────────────────── */}
      <aside className="flex w-72 shrink-0 flex-col border-r border-white/10 bg-zinc-950">
        <Link href="/" className="flex items-center gap-2.5 px-4 py-4">
          <span className="h-2.5 w-2.5 rounded-full bg-white animate-pulse" />
          <span className="font-display text-base font-bold tracking-tight text-white">
            DocuMind
          </span>
        </Link>

        {/* Upload */}
        <div
          className="px-3"
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files?.length) {
              addFilesToQueue(Array.from(e.dataTransfer.files));
            }
          }}
        >
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className={`flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
              isDragging
                ? "border-white/40 bg-white/10 text-white"
                : "border-white/10 bg-white/5 text-zinc-200 hover:bg-white/10"
            }`}
          >
            <Plus className="h-4 w-4" />
            <span>Upload document</span>
          </button>

          {intakeFiles.length > 0 && (
            <div className="mt-2 space-y-1.5 rounded-lg border border-white/10 bg-zinc-900/60 p-2">
              {intakeFiles.map((item) => (
                <div key={item.id} className="flex items-center justify-between gap-2 text-xs">
                  <span className="truncate text-zinc-300">{item.name}</span>
                  <button
                    type="button"
                    aria-label={`Remove ${item.name} from queue`}
                    onClick={() => removeFileFromQueue(item.id)}
                    className="shrink-0 text-zinc-500 hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              ))}
              <Button
                onClick={triggerUpload}
                disabled={indexing}
                size="sm"
                className="mt-1 w-full gap-1.5 bg-white text-zinc-950 hover:bg-zinc-200"
              >
                {indexing ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    <span>Indexing…</span>
                  </>
                ) : (
                  <>
                    <Zap className="h-3.5 w-3.5" />
                    <span>Index {intakeFiles.length} file{intakeFiles.length > 1 ? "s" : ""}</span>
                  </>
                )}
              </Button>
            </div>
          )}

          {intakeError && (
            <div role="alert" aria-live="polite" className="mt-2 flex items-start gap-1.5 rounded-lg border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-400">
              <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              <span>{intakeError}</span>
            </div>
          )}

          {progressLog.length > 0 && (
            <div className="mt-2 max-h-28 overflow-y-auto space-y-1 rounded-lg border border-white/10 bg-zinc-950 p-2 font-mono text-[10px]">
              <div className="flex items-center gap-1.5 text-zinc-500 pb-1">
                <Terminal className="h-3 w-3" />
                <span>{progressLog.length} events</span>
              </div>
              {progressLog.map((ev, i) => (
                <div key={i} className={ev.tone === "warn" ? "text-amber-300" : "text-zinc-400"}>
                  {ev.label}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Document list */}
        {libraryDocs.length > 0 && (
          <div className="mt-4 flex-1 overflow-y-auto px-3 space-y-0.5">
            <div className="px-1 pb-1.5 font-mono text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
              Documents
            </div>
            {libraryDocs.map((doc) => {
              const isActive = docHash === doc.doc_hash;
              return (
                <div
                  key={doc.doc_hash}
                  data-testid="doc-library-item"
                  onClick={() => selectActiveDocument(doc.doc_hash)}
                  className={`group flex cursor-pointer items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-sm transition-colors ${
                    isActive ? "bg-white/10 text-white" : "text-zinc-300 hover:bg-white/5"
                  }`}
                >
                  <span className="truncate">{doc.filename}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteLibraryDoc(doc.doc_hash);
                    }}
                    aria-label="Delete document"
                    title="Delete document"
                    className="shrink-0 text-zinc-500 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Tools nav */}
        <nav className={`px-3 py-3 space-y-0.5 border-t border-white/10 ${libraryDocs.length === 0 ? "mt-4" : ""}`}>
          <div className="px-1 pb-1.5 font-mono text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
            Tools
          </div>
          {TOOLS.map((t) => (
            <button
              key={t.view}
              type="button"
              disabled={!docHash}
              onClick={() => handleCardClick(t.view)}
              className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                activeView === t.view ? "bg-white/10 text-white font-medium" : "text-zinc-300 hover:bg-white/5"
              }`}
            >
              {t.icon}
              <span>{t.label}</span>
            </button>
          ))}
        </nav>

        {/* Account */}
        <div className="border-t border-white/10 px-3 py-3">
          {telemetryStats && (
            <div className="px-1 pb-2 font-mono text-[10px] text-zinc-600">
              {telemetryStats.total_requests ?? 0} requests · {telemetryStats.avg_latency_ms ?? 0}ms avg
            </div>
          )}
          <div className="flex items-center justify-between gap-2 px-1">
            <span className="truncate text-xs text-zinc-500">
              {currentUser?.name || currentUser?.email || ""}
            </span>
            <button
              onClick={handleSignOut}
              aria-label="Sign out"
              title="Sign out"
              className="shrink-0 text-zinc-500 hover:text-white transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* ── MAIN CONTENT ──────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        {!docHash ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center px-6">
            <UploadCloud className="h-10 w-10 text-zinc-600" />
            <p className="text-lg font-semibold text-white">Upload a document to get started</p>
            <p className="max-w-sm text-sm text-zinc-500">
              PDF (with OCR), TXT, Markdown, or Word - up to {MAX_FILE_MB}MB. Use the sidebar to add one.
            </p>
          </div>
        ) : activeView === "none" ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center px-6">
            <Sparkles className="h-10 w-10 text-zinc-600" />
            <p className="text-lg font-semibold text-white">Choose a tool from the sidebar</p>
            <p className="max-w-sm text-sm text-zinc-500">
              Ask questions, generate a summary, or explore the knowledge atlas for this document.
            </p>
          </div>
        ) : (
          <div className="mx-auto max-w-4xl px-8 py-6 space-y-6">
            <div className="flex items-center justify-between">
              <h1 className="text-lg font-semibold text-white">{VIEW_TITLES[activeView]}</h1>

              {activeView === "summary" && summary && (
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={copySummaryToClipboard} className="gap-1.5">
                    {copiedSummary ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5 text-zinc-400" />}
                    <span>{copiedSummary ? "Copied" : "Copy"}</span>
                  </Button>
                  <Button variant="secondary" size="sm" onClick={downloadSummaryMarkdown} className="gap-1.5">
                    <Download className="h-3.5 w-3.5 text-zinc-400" />
                    <span>Export .MD</span>
                  </Button>
                </div>
              )}
            </div>

            {/* View: Summary */}
            {activeView === "summary" && (
              <Card className="p-8">
                {isSummarizing && !summary && (
                  <div className="py-20 space-y-4">
                    <Skeleton className="h-8 w-2/3" />
                    <Skeleton className="h-24 w-full" />
                    <Skeleton className="h-40 w-full" />
                    <div className="text-center font-mono text-xs text-zinc-400 pt-2">
                      Synthesizing executive summary &amp; topical takeaways…
                    </div>
                  </div>
                )}

                {!isSummarizing && studioErrors.summary && (
                  <ErrorBanner
                    message={studioErrors.summary}
                    onRetry={() => docHash && fetchSummary(docHash)}
                  />
                )}

                {summary && (
                  // Bounded + internally scrollable so a long streaming summary
                  // grows this panel, not the whole page - the panel stays put
                  // and new tokens scroll inside it instead.
                  <div className="max-h-[70vh] overflow-y-auto pr-2">
                    <article className="prose prose-invert max-w-none text-zinc-300 leading-relaxed prose-h1:text-2xl prose-h1:font-bold prose-h1:text-white prose-h2:text-lg prose-h2:font-semibold prose-h2:text-white prose-h2:mt-6 prose-p:text-sm prose-p:leading-relaxed prose-strong:text-white prose-blockquote:border-l-2 prose-blockquote:border-white/30 prose-blockquote:bg-zinc-900/60 prose-blockquote:p-4 prose-blockquote:rounded-r-xl">
                      <Markdown>{formatSummaryMarkdown(summary)}</Markdown>
                    </article>
                  </div>
                )}
              </Card>
            )}

            {/* View: Query Console */}
            {activeView === "chat" && (
              <Card className="p-6">
                <ChatStream
                  docHash={docHash}
                  onCiteClick={(cid) => {
                    setFocusChunk(cid);
                    setActiveView("graph");
                  }}
                />
              </Card>
            )}

            {/* View: Quiz Arena */}
            {activeView === "quiz" && (
              <div>
                {isQuizLoading && (
                  <Card className="p-12 text-center space-y-4">
                    <Skeleton className="h-16 w-full" />
                    <Skeleton className="h-40 w-full" />
                    <Skeleton className="h-40 w-full" />
                    <div className="font-mono text-xs text-zinc-400">
                      Generating volume-adaptive examination questions…
                    </div>
                  </Card>
                )}

                {!isQuizLoading && studioErrors.quiz && (
                  <ErrorBanner
                    message={studioErrors.quiz}
                    onRetry={() => docHash && fetchQuiz(docHash)}
                  />
                )}

                {!isQuizLoading && !studioErrors.quiz && quizCards.length === 0 && (
                  <EmptyState message="No usable questions could be generated from this document." />
                )}

                {!isQuizLoading && quizCards.length > 0 && (
                  <div className="space-y-3">
                    <QuizArena cards={quizCards} />
                    <CoverageNote coverage={studioCoverage.quiz} />
                  </div>
                )}
              </div>
            )}

            {/* View: Knowledge Atlas Graph */}
            {activeView === "graph" && (
              <GraphView docHash={docHash} highlightNode={focusChunk ? String(focusChunk) : null} />
            )}

            {/* View: Masterclass Studio */}
            {activeView === "masterclass" && (
              <MasterclassStudio docHash={docHash} />
            )}

            {/* View: Compliance & Risk Audit */}
            {activeView === "audit" && (
              <AuditPanel
                loading={isAuditLoading}
                items={auditItems}
                error={studioErrors.audit}
                coverage={studioCoverage.audit}
                onRetry={() => docHash && fetchComplianceAudit(docHash)}
              />
            )}

            {/* View: Audio & Slide Deck Studio */}
            {activeView === "slides" && (
              <AudioSlidesPanel
                audio={{
                  script: audioScript,
                  loading: isAudioLoading,
                  error: studioErrors.audio,
                  coverage: studioCoverage.audio,
                  copied: copiedAudio,
                  onGenerate: () => docHash && fetchAudioBriefing(docHash),
                  onCopy: () => {
                    navigator.clipboard?.writeText(audioScript);
                    setCopiedAudio(true);
                    setTimeout(() => setCopiedAudio(false), 2000);
                  },
                }}
                slides={{
                  items: slides,
                  loading: isSlidesLoading,
                  error: studioErrors.slides,
                  coverage: studioCoverage.slides,
                  onGenerate: () => docHash && fetchSlideDeck(docHash),
                }}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
