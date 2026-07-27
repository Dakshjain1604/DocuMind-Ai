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
  CheckCircle2,
  Trash2,
  Terminal,
  Download,
  RefreshCw,
  AlertCircle,
  Copy,
  Check,
  Zap,
  ShieldAlert,
  Mic,
  Presentation,
  Volume2,
} from "lucide-react";

import { QuizArena } from "../components/QuizArena";
import { ChatStream } from "../components/ChatStream";
import { GraphView } from "../components/GraphView";
import { MasterclassStudio } from "../components/MasterclassStudio";
import { Homecard } from "../components/HomeCard";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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

  return (
    <div className="relative min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans selection:bg-indigo-500/30">
      {/* ── TOP NAVIGATION BAR ────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-zinc-950/80 backdrop-blur-xl px-6 py-3.5">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="h-3 w-3 rounded-full bg-indigo-500 animate-pulse" />
              <span className="font-display text-xl font-bold tracking-tight text-white">
                Docu<span className="gradient-accent-text">Mind</span>
              </span>
            </Link>
            <Badge variant="default" className="hidden sm:inline-flex">
              Enterprise Studio Workspace
            </Badge>
          </div>

          <div className="flex items-center gap-3">
            {docHash && (
              <div className="hidden md:flex items-center gap-2 rounded-full border border-white/10 bg-zinc-900/60 px-3 py-1 font-mono text-xs text-zinc-400">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                <span>Active Batch: {shortHash(docHash)}</span>
              </div>
            )}
            <Button variant="ghost" size="sm" onClick={handleSignOut}>
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      {/* ── MAIN DASHBOARD LAYOUT ─────────────────────────────────── */}
      <main className="mx-auto max-w-7xl flex-1 px-6 py-8 w-full space-y-8">
        {/* ── PERSISTENT DOCUMENT LIBRARY & TELEMETRY ───────────────── */}
        {libraryDocs.length > 0 && (
          <Card className="border-indigo-500/20 bg-zinc-950/80 p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3 font-mono text-xs uppercase tracking-wider text-indigo-400 font-semibold">
              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4" />
                <span>Persistent Document Store Library ({libraryDocs.length} Indexed Documents)</span>
              </div>
              {telemetryStats && (
                <div className="hidden sm:flex items-center gap-4 text-[10px] text-zinc-400">
                  <span>Requests: {telemetryStats.total_requests ?? 0}</span>
                  <span>Avg Latency: {telemetryStats.avg_latency_ms ?? 0}ms</span>
                  <span>
                    Tokens:{" "}
                    {(telemetryStats.total_tokens_in ?? 0) + (telemetryStats.total_tokens_out ?? 0)}
                  </span>
                </div>
              )}
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {libraryDocs.map((doc) => {
                const isActive = docHash === doc.doc_hash;
                return (
                  <div
                    key={doc.doc_hash}
                    onClick={() => selectActiveDocument(doc.doc_hash)}
                    className={`group cursor-pointer flex items-center justify-between rounded-xl border p-3.5 transition-all ${
                      isActive
                        ? "border-indigo-500/60 bg-indigo-500/10 shadow-lg shadow-indigo-500/10"
                        : "border-white/10 bg-zinc-900/40 hover:border-white/20 hover:bg-zinc-900/80"
                    }`}
                  >
                    <div className="flex items-center gap-3 overflow-hidden pr-2">
                      <FileText className={`h-4 w-4 shrink-0 ${isActive ? "text-indigo-400" : "text-zinc-500"}`} />
                      <div className="overflow-hidden">
                        <div className="font-mono text-xs font-semibold text-white truncate">{doc.filename}</div>
                        <div className="font-mono text-[10px] text-zinc-500">
                          {shortHash(doc.doc_hash)} · {doc.n_chunks} chunks
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {isActive && <Badge variant="success">ACTIVE</Badge>}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteLibraryDoc(doc.doc_hash);
                        }}
                        className="text-zinc-500 hover:text-red-400 transition-colors p-1"
                        title="Delete document"
                          aria-label="Delete document"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        {/* ── FILE INTAKE & TELEMETRY SECTION ──────────────────────── */}
        <Card className="border-indigo-500/20 bg-zinc-950/70 relative overflow-hidden">
          <div className="absolute -top-24 -right-24 h-48 w-48 rounded-full bg-indigo-500/10 blur-3xl" />
          <CardHeader className="border-b border-white/10 pb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-indigo-400 font-semibold">
                <UploadCloud className="h-4 w-4" />
                <span>Multi-File Intake Engine (Max 5 Files · PDF, TXT, MD, DOCX)</span>
              </div>
              {docHash && (
                <Badge variant="success">
                  Active Hash: {shortHash(docHash)}
                </Badge>
              )}
            </div>
          </CardHeader>

          <CardContent className="pt-6 space-y-6">
            {/* Dropzone. A real <button> rather than a <div onClick>: as a div
                it had no role, no tabIndex and no key handler, so keyboard
                users could not upload at all. */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
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
              className={`group w-full cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-all hover:border-indigo-500/50 hover:bg-zinc-900/80 ${
                isDragging
                  ? "border-indigo-500 bg-zinc-900/80"
                  : "border-white/15 bg-zinc-900/40"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept={ACCEPTED_EXTS.join(",")}
                onChange={handleFileChange}
                className="hidden"
              />
              <UploadCloud className="mx-auto h-10 w-10 text-indigo-400 group-hover:scale-110 transition-transform mb-3" />
              <p className="font-display text-base font-semibold text-white">
                Drag &amp; drop document files here or click to browse
              </p>
              <p className="mt-1 font-mono text-xs text-zinc-400">
                Supports PDF (with OCR), TXT, Markdown, and Word Documents up to {MAX_FILE_MB}MB
              </p>
            </button>

            {/* Queue Files List */}
            {intakeFiles.length > 0 && (
              <div className="space-y-3">
                <div className="font-mono text-xs uppercase tracking-wider text-zinc-400 font-semibold flex items-center justify-between">
                  <span>Queued Documents ({intakeFiles.length}/5)</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setIntakeFiles([]);
                    }}
                    className="h-6 px-2 text-[10px] text-zinc-500 hover:text-red-400"
                  >
                    Clear Queue
                  </Button>
                </div>

                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {intakeFiles.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center justify-between rounded-xl border border-white/10 bg-zinc-900/60 px-3.5 py-2.5 font-mono text-xs"
                    >
                      <div className="flex items-center gap-2 overflow-hidden pr-2">
                        <FileText className="h-4 w-4 text-indigo-400 shrink-0" />
                        <span className="truncate text-zinc-200">{item.name}</span>
                        <span className="text-[10px] text-zinc-500 shrink-0">({formatSize(item.size)})</span>
                      </div>
                      <button
                        type="button"
                        aria-label={`Remove ${item.name} from queue`}
                        title={`Remove ${item.name}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          removeFileFromQueue(item.id);
                        }}
                        className="text-zinc-500 hover:text-red-400 transition-colors p-1"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>

                <div className="pt-2 flex justify-end">
                  <Button
                    onClick={triggerUpload}
                    disabled={indexing || intakeFiles.length === 0}
                    className="gap-2"
                  >
                    {indexing ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        <span>Indexing Batch…</span>
                      </>
                    ) : (
                      <>
                        <Zap className="h-4 w-4" />
                        <span>Process &amp; Index Documents</span>
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {intakeError && (
              <div role="alert" aria-live="polite" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 font-mono text-xs text-red-400">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{intakeError}</span>
              </div>
            )}

            {/* Indexing Telemetry Log */}
            {progressLog.length > 0 && (
              <div className="rounded-xl border border-white/10 bg-zinc-950 p-4 space-y-2 font-mono text-xs">
                <div className="flex items-center justify-between text-zinc-400 border-b border-white/10 pb-2">
                  <span className="flex items-center gap-1.5 font-semibold">
                    <Terminal className="h-3.5 w-3.5 text-indigo-400" />
                    <span>Real-time Telemetry Pipeline</span>
                  </span>
                  <span className="text-[10px] text-zinc-500">{progressLog.length} events</span>
                </div>
                <div
                  className="max-h-36 overflow-y-auto space-y-1.5 pr-1 text-zinc-300"
                  aria-live="polite"
                >
                  {progressLog.map((ev, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-zinc-500 shrink-0">[{ev.stamp}]</span>
                      <span className={ev.tone === "warn" ? "text-amber-300" : "text-indigo-300"}>
                        {ev.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── BENTO NAVIGATION CARDS ────────────────────────────────── */}
        <section className="space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="font-mono text-xs uppercase tracking-wider text-zinc-400 font-semibold">
              Studio Instruments &amp; Enterprise Action Modules
            </div>
            {docHash ? (
              <Badge variant="success">Document Batch Active</Badge>
            ) : (
              <Badge variant="secondary">Select or Upload Document</Badge>
            )}
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <Homecard
              numeral="I"
              heading="Summary Studio"
              mainText="Executive synthesis, topical takeaways, and structured section breakdowns with Markdown export."
              ButtonText="Open Studio"
              disabled={!docHash}
              onClick={() => handleCardClick("summary")}
              glyph={<FileText className="h-6 w-6" />}
            />
            <Homecard
              numeral="II"
              heading="Query Console"
              mainText="Ask anything. Live SSE streaming answers with passage-level citation chips linked to source document."
              ButtonText="Open Console"
              disabled={!docHash}
              onClick={() => handleCardClick("chat")}
              glyph={<Sparkles className="h-6 w-6" />}
            />
            <Homecard
              numeral="III"
              heading="Quiz Arena"
              mainText="Volume-adaptive multiple-choice examination with evidence explanations and difficulty filters."
              ButtonText="Launch Arena"
              disabled={!docHash}
              onClick={() => handleCardClick("quiz")}
              glyph={<HelpCircle className="h-6 w-6" />}
            />
            <Homecard
              numeral="IV"
              heading="Masterclass Studio"
              mainText="Book module navigator, visual system architecture diagrams, and targeted chapter mastery quizzes."
              ButtonText="Open Masterclass"
              disabled={!docHash}
              onClick={() => handleCardClick("masterclass")}
              glyph={<BookOpen className="h-6 w-6" />}
            />
            <Homecard
              numeral="V"
              heading="Compliance &amp; Risk Audit"
              mainText="Automated security, policy, and data governance risk scanner with severity classification."
              ButtonText="Run Audit"
              disabled={!docHash}
              onClick={() => handleCardClick("audit")}
              glyph={<ShieldAlert className="h-6 w-6 text-amber-400" />}
            />
            <Homecard
              numeral="VI"
              heading="Audio &amp; Slide Deck Studio"
              mainText="Generate 2-host conversational audio briefing scripts or 5-slide executive presentation decks."
              ButtonText="Open Studio"
              disabled={!docHash}
              onClick={() => handleCardClick("slides")}
              glyph={<Presentation className="h-6 w-6 text-indigo-400" />}
            />
          </div>
        </section>

        {/* ── ACTIVE INSTRUMENT VIEW ───────────────────────────────── */}
        {activeView !== "none" && docHash && (
          <section className="space-y-6 pt-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div className="flex items-center gap-3">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setActiveView("none")}
                  className="h-8 text-xs text-zinc-400 hover:text-white"
                >
                  ← Close Instrument
                </Button>
                <div className="h-4 w-px bg-white/10" />
                <h2 className="font-display text-xl font-bold text-white uppercase tracking-tight">
                  {activeView === "summary" && "Summary Studio"}
                  {activeView === "chat" && "Query Console"}
                  {activeView === "quiz" && "Quiz Arena"}
                  {activeView === "graph" && "Knowledge Cartography Atlas"}
                  {activeView === "masterclass" && "Masterclass Learning Studio"}
                  {activeView === "audit" && "Compliance & Risk Audit Engine"}
                  {activeView === "audio" && "Audio Briefing Studio"}
                  {activeView === "slides" && "Executive Slide Deck Exporter"}
                </h2>
              </div>

              {activeView === "summary" && summary && (
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={copySummaryToClipboard} className="gap-1.5">
                    {copiedSummary ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5 text-zinc-400" />}
                    <span>{copiedSummary ? "Copied" : "Copy Markdown"}</span>
                  </Button>
                  <Button variant="secondary" size="sm" onClick={downloadSummaryMarkdown} className="gap-1.5">
                    <Download className="h-3.5 w-3.5 text-indigo-400" />
                    <span>Export .MD</span>
                  </Button>
                </div>
              )}
            </div>

            {/* View 1: Summary */}
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
                  <article className="prose prose-invert max-w-none text-zinc-300 leading-relaxed prose-h1:text-2xl prose-h1:font-bold prose-h1:text-white prose-h2:text-lg prose-h2:font-semibold prose-h2:text-indigo-300 prose-h2:mt-6 prose-p:text-sm prose-p:leading-relaxed prose-strong:text-white prose-blockquote:border-l-2 prose-blockquote:border-indigo-500 prose-blockquote:bg-zinc-900/60 prose-blockquote:p-4 prose-blockquote:rounded-r-xl">
                    <Markdown>{formatSummaryMarkdown(summary)}</Markdown>
                  </article>
                )}
              </Card>
            )}

            {/* View 2: Query Console */}
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

            {/* View 3: Quiz Arena */}
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

            {/* View 4: Knowledge Atlas Graph */}
            {activeView === "graph" && (
              <GraphView docHash={docHash} highlightNode={focusChunk ? String(focusChunk) : null} />
            )}

            {/* View 5: Masterclass Studio */}
            {activeView === "masterclass" && (
              <MasterclassStudio docHash={docHash} />
            )}

            {/* View 6: Compliance & Risk Audit */}
            {activeView === "audit" && (
              <div className="space-y-4">
                {isAuditLoading && (
                  <Card className="p-12 text-center space-y-4">
                    <Skeleton className="h-16 w-full" />
                    <Skeleton className="h-32 w-full" />
                    <Skeleton className="h-32 w-full" />
                    <div className="font-mono text-xs text-zinc-400">
                      Auditing document batch for compliance &amp; security risks…
                    </div>
                  </Card>
                )}

                {!isAuditLoading && auditItems.length > 0 && (
                  <div className="grid gap-4">
                    {auditItems.map((item) => (
                      <Card key={item.id} className="p-6 space-y-3 border-l-4 border-l-amber-500">
                        <div className="flex items-center justify-between">
                          <Badge variant={item.severity === "high" ? "destructive" : item.severity === "medium" ? "warning" : "secondary"}>
                            {(item.severity ?? "unknown").toUpperCase()} SEVERITY
                          </Badge>
                          <span className="font-mono text-xs text-zinc-400">{item.category}</span>
                        </div>
                        <h4 className="font-display text-lg font-bold text-white">
                          Finding: {item.finding}
                        </h4>
                        <div className="rounded-xl border border-white/5 bg-zinc-900/60 p-3 font-mono text-xs text-zinc-300 space-y-1">
                          <span className="text-emerald-400 font-semibold">Recommended Mitigation:</span>
                          <p>{item.mitigation}</p>
                        </div>
                      </Card>
                    ))}
                    <CoverageNote coverage={studioCoverage.audit} />
                  </div>
                )}

                {!isAuditLoading && studioErrors.audit && (
                  <ErrorBanner
                    message={studioErrors.audit}
                    onRetry={() => docHash && fetchComplianceAudit(docHash)}
                  />
                )}

                {!isAuditLoading && !studioErrors.audit && auditItems.length === 0 && (
                  <EmptyState message="No compliance findings were identified in the sampled sections." />
                )}
              </div>
            )}

            {/* View 7: Audio & Slide Deck Studio */}
            {activeView === "slides" && (
              <div className="space-y-6">
                <div className="flex items-center gap-3">
                  <Button variant={audioScript ? "default" : "outline"} size="sm" disabled={isAudioLoading} onClick={() => fetchAudioBriefing(docHash)} className="gap-2">
                    <Mic className="h-4 w-4" />
                    <span>Generate Audio Podcast Script</span>
                  </Button>
                  <Button variant={slides.length > 0 ? "default" : "outline"} size="sm" disabled={isSlidesLoading} onClick={() => fetchSlideDeck(docHash)} className="gap-2">
                    <Presentation className="h-4 w-4" />
                    <span>Generate 5-Slide Presentation Deck</span>
                  </Button>
                </div>

                {isAudioLoading && (
                  <Card className="p-8 text-center space-y-3">
                    <Skeleton className="h-24 w-full" />
                    <div className="font-mono text-xs text-zinc-400">Synthesizing 2-host conversational podcast script…</div>
                  </Card>
                )}

                {!isAudioLoading && studioErrors.audio && (
                  <ErrorBanner
                    message={studioErrors.audio}
                    onRetry={() => docHash && fetchAudioBriefing(docHash)}
                  />
                )}

                {audioScript && (
                  <Card className="p-6 space-y-4">
                    <div className="flex items-center justify-between border-b border-white/10 pb-3 font-mono text-xs text-zinc-400 font-semibold">
                      <span className="flex items-center gap-2">
                        <Volume2 className="h-4 w-4 text-indigo-400" />
                        <span>Executive Podcast Script (Alex &amp; Morgan)</span>
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          navigator.clipboard.writeText(audioScript);
                          setCopiedAudio(true);
                          setTimeout(() => setCopiedAudio(false), 2000);
                        }}
                      >
                        {copiedAudio ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5 text-zinc-400" />}
                        <span>{copiedAudio ? "Copied" : "Copy Script"}</span>
                      </Button>
                    </div>
                    <div className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-zinc-200 bg-zinc-900/60 p-5 rounded-xl border border-white/5">
                      {audioScript}
                    </div>
                    <CoverageNote coverage={studioCoverage.audio} />
                  </Card>
                )}

                {isSlidesLoading && (
                  <Card className="p-8 text-center space-y-3">
                    <Skeleton className="h-32 w-full" />
                    <div className="font-mono text-xs text-zinc-400">Generating 5-slide executive presentation cards…</div>
                  </Card>
                )}

                {!isSlidesLoading && studioErrors.slides && (
                  <ErrorBanner
                    message={studioErrors.slides}
                    onRetry={() => docHash && fetchSlideDeck(docHash)}
                  />
                )}

                {slides.length > 0 && (
                  <div className="grid gap-4 sm:grid-cols-2">
                    {slides.map((s: Slide) => (
                      <Card key={s.slide} className="p-6 space-y-4 flex flex-col justify-between">
                        <div>
                          <Badge variant="default" className="mb-2">Slide {s.slide}</Badge>
                          <h4 className="font-display text-lg font-bold text-white mb-3">{s.title}</h4>
                          <ul className="space-y-2 font-sans text-sm text-zinc-300">
                            {s.bullets?.map((b: string, i: number) => (
                              <li key={i} className="flex items-start gap-2">
                                <span className="text-indigo-400 font-bold">•</span>
                                <span>{b}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        {s.speaker_notes && (
                          <div className="pt-3 border-t border-white/10 font-mono text-xs text-zinc-400">
                            <span className="text-zinc-500 font-semibold">Speaker Notes:</span> {s.speaker_notes}
                          </div>
                        )}
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </main>

      {/* ── FOOTER ────────────────────────────────────────────────── */}
      <footer className="border-t border-white/10 bg-zinc-950 py-6 px-6 font-mono text-xs text-zinc-500 mt-auto">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <span>DocuMind AI · Enterprise GraphRAG Platform</span>
          <span>© MMXXVI · All rights reserved</span>
        </div>
      </footer>
    </div>
  );
}
