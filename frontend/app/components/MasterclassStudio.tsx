"use client";

import React, { useState, useEffect, useCallback } from "react";
import Markdown from "react-markdown";
import { BookOpen, Layers, HelpCircle, Check, Copy } from "lucide-react";
import { MermaidDiagram } from "./MermaidDiagram";
import { QuizArena } from "./QuizArena";
import { QuizCardType } from "../Dashboard/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { readSseStream } from "@/lib/sse";

interface Chapter {
  id: number;
  title: string;
  summary: string;
}

interface MasterclassStudioProps {
  docHash: string;
}

export const MasterclassStudio: React.FC<MasterclassStudioProps> = ({ docHash }) => {
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null);
  const [activeTab, setActiveTab] = useState<"draft" | "quiz">("draft");

  const [draftText, setDraftText] = useState<string>("");
  const [isDraftLoading, setIsDraftLoading] = useState<boolean>(false);

  const [quizCards, setQuizCards] = useState<QuizCardType[]>([]);
  const [isQuizLoading, setIsQuizLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [chaptersLoading, setChaptersLoading] = useState<boolean>(true);
  const [chaptersError, setChaptersError] = useState<string | null>(null);
  const [draftError, setDraftError] = useState<string | null>(null);

  // Load chapters list
  const loadChapters = useCallback(async () => {
    setChaptersLoading(true);
    setChaptersError(null);
    try {
      const r = await fetch("/api/rag/chapters", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ doc_hash: docHash }),
      });
      const data = await r.json();
      if (!data.success) {
        setChaptersError(data.error?.message ?? "Chapter extraction failed.");
        return;
      }
      const list = data.data?.chapters ?? [];
      if (list.length === 0) {
        setChaptersError("No chapters could be identified in this document.");
        return;
      }
      setChapters(list);
      setSelectedChapter(list[0]);
    } catch {
      setChaptersError("Could not reach the masterclass service. Is the backend running?");
    } finally {
      setChaptersLoading(false);
    }
  }, [docHash]);

  useEffect(() => {
    loadChapters();
  }, [loadChapters]);

  // Load Learning Draft for selected chapter
  const fetchLearningDraft = useCallback(async (ch: Chapter, signal: AbortSignal) => {
    setIsDraftLoading(true);
    setDraftText("");
    setDraftError(null);
    try {
      const r = await fetch("/api/rag/learning-draft", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ doc_hash: docHash, chapter_id: ch.id, chapter_title: ch.title }),
        signal,
      });
      let acc = "";
      await readSseStream(r, {
        signal,
        onError: (message) => setDraftError(message),
        onEvent: (evt, data: { text?: string; message?: string }) => {
          if (evt === "token") {
            acc += data.text ?? "";
            setDraftText(acc);
          } else if (evt === "error") {
            setDraftError(data.message ?? "Draft generation failed.");
          }
        },
      });
    } catch (err) {
      // An abort is the expected outcome when the user switches chapters
      // mid-stream, not a failure worth reporting.
      if ((err as Error)?.name !== "AbortError") {
        console.error("Draft stream error:", err);
      }
    } finally {
      setIsDraftLoading(false);
    }
  }, [docHash]);

  // Load Chapter Quiz
  const fetchChapterQuiz = useCallback(async (ch: Chapter, signal: AbortSignal) => {
    setIsQuizLoading(true);
    setQuizCards([]);
    try {
      const r = await fetch("/api/rag/chapter-quiz", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ doc_hash: docHash, chapter_id: ch.id, chapter_title: ch.title }),
        signal,
      });
      const data = await r.json();
      if (data.success && data.data?.cards) {
        setQuizCards(data.data.cards);
      }
    } catch (err) {
      if ((err as Error)?.name !== "AbortError") {
        console.error("Failed to load chapter quiz:", err);
      }
    } finally {
      setIsQuizLoading(false);
    }
  }, [docHash]);

  // Sole trigger for chapter content. handleSelectChapter used to ALSO call
  // the fetchers directly, which raced this effect and interleaved two SSE
  // streams into one accumulator. Aborting on cleanup means a rapid chapter
  // switch cancels the in-flight stream instead of merging into the next one.
  useEffect(() => {
    if (!selectedChapter) return;
    const controller = new AbortController();
    if (activeTab === "draft") {
      fetchLearningDraft(selectedChapter, controller.signal);
    } else {
      fetchChapterQuiz(selectedChapter, controller.signal);
    }
    return () => controller.abort();
  }, [selectedChapter, activeTab, fetchLearningDraft, fetchChapterQuiz]);

  const handleSelectChapter = (ch: Chapter) => {
    setSelectedChapter(ch);
  };

  const copyDraft = () => {
    if (!draftText) return;
    navigator.clipboard.writeText(draftText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Renders the draft, turning ```mermaid fences into diagrams.
  // Note: when the model does not emit a diagram, none is shown. This used to
  // synthesise a four-node flowchart out of the chapter title and present it
  // as if it had been derived from the document.
  const renderMarkdownWithDiagrams = (text: string) => {
    return (
      <div className="space-y-6">
        <article className="prose prose-invert max-w-none text-zinc-300 leading-relaxed prose-h1:text-2xl prose-h1:font-bold prose-h1:text-white prose-h2:text-lg prose-h2:font-semibold prose-h2:text-indigo-300 prose-h2:mt-6 prose-p:text-sm prose-p:leading-relaxed prose-strong:text-white prose-blockquote:border-l-2 prose-blockquote:border-indigo-500 prose-blockquote:bg-zinc-950/60 prose-blockquote:p-4 prose-blockquote:rounded-r-xl">
          <Markdown
            components={{
              code({ inline, className, children, ...props }: any) {
                const match = /language-mermaid/.exec(className || "");
                if (!inline && match) {
                  return <MermaidDiagram chart={String(children).replace(/\n$/, "")} />;
                }
                return (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {text}
          </Markdown>
        </article>
      </div>
    );
  };

  if (chaptersError) {
    return (
      <ErrorBanner message={chaptersError} onRetry={loadChapters} />
    );
  }

  return (
    <div className="space-y-6">
      {/* Chapter Selection Bar */}
      <div className="glass-panel rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border border-indigo-500/20 bg-zinc-950/80 shadow-xl backdrop-blur-xl">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <BookOpen className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase text-zinc-400 font-semibold tracking-wider">
              <span>Module Navigator</span>
              <Badge variant="default">{chapters.length} Modules</Badge>
            </div>
            <div className="font-display text-base font-bold text-white mt-0.5">
              {selectedChapter
                ? selectedChapter.title
                : chaptersLoading
                  ? "Loading Chapters…"
                  : "No chapters available"}
            </div>
          </div>
        </div>

        {chapters.length > 0 && (
          <select
            value={selectedChapter?.id || 1}
            onChange={(e) => {
              const ch = chapters.find((c) => c.id === Number(e.target.value));
              if (ch) handleSelectChapter(ch);
            }}
            aria-label="Select chapter"
            className="bg-zinc-900 border border-white/10 text-white font-mono text-xs rounded-xl px-4 py-2.5 focus:outline-none focus:border-indigo-500 cursor-pointer shadow-inner"
          >
            {chapters.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Dual Tab Switcher (Visual Draft vs Mastery Quiz) */}
      <div className="flex items-center justify-between border-b border-white/10 pb-3">
        <div className="flex items-center gap-2">
          <Button
            variant={activeTab === "draft" ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveTab("draft")}
            className="gap-2"
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Visual Learning Draft &amp; Diagrams</span>
          </Button>
          <Button
            variant={activeTab === "quiz" ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveTab("quiz")}
            className="gap-2"
          >
            <HelpCircle className="h-3.5 w-3.5" />
            <span>Chapter Mastery Quiz</span>
          </Button>
        </div>

        {activeTab === "draft" && draftText && (
          <Button
            variant="outline"
            size="sm"
            onClick={copyDraft}
            className="gap-1.5"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                <span>Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5 text-zinc-400" />
                <span>Copy Draft</span>
              </>
            )}
          </Button>
        )}
      </div>

      {/* Tab 1: Visual Learning Draft */}
      {activeTab === "draft" && (
        <div className="space-y-4">
          {isDraftLoading && !draftText && (
            <div className="py-20 space-y-4">
              <Skeleton className="h-8 w-2/3" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-48 w-full" />
              <div className="text-center font-mono text-xs text-zinc-400 pt-2">
                Architecting visual learning draft &amp; system diagrams…
              </div>
            </div>
          )}

          {draftError && (
            <ErrorBanner
              message={draftError}
              onRetry={() => selectedChapter && setSelectedChapter({ ...selectedChapter })}
            />
          )}

          {draftText && renderMarkdownWithDiagrams(draftText)}
        </div>
      )}

      {/* Tab 2: Chapter Mastery Quiz */}
      {activeTab === "quiz" && (
        <div className="space-y-4">
          {isQuizLoading && (
            <div className="py-20 space-y-4">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-40 w-full" />
              <Skeleton className="h-40 w-full" />
              <div className="text-center font-mono text-xs text-zinc-400 pt-2">
                Generating targeted chapter mastery quiz…
              </div>
            </div>
          )}

          {!isQuizLoading && quizCards.length > 0 && (
            <QuizArena cards={quizCards} />
          )}
        </div>
      )}
    </div>
  );
};
