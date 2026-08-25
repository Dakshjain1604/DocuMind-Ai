"use client";

import React, { useState, useMemo } from "react";
import { Trophy, CheckCircle2, XCircle, RotateCcw, HelpCircle } from "lucide-react";
import { QuizCardType } from "../Dashboard/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface QuizArenaProps {
  cards: QuizCardType[];
}

export const QuizArena: React.FC<QuizArenaProps> = ({ cards }) => {
  const [filterDifficulty, setFilterDifficulty] = useState<string>("all");
  const [userAnswers, setUserAnswers] = useState<Record<number, { selectedId: string; isCorrect: boolean }>>({});
  const [showReviewOnly, setShowReviewOnly] = useState<boolean>(false);

  // Filtered cards based on difficulty tab
  const filteredCards = useMemo(() => {
    let list = cards;
    if (filterDifficulty !== "all") {
      list = list.filter((c) => c.metadata?.difficulty?.toLowerCase() === filterDifficulty);
    }
    if (showReviewOnly) {
      list = list.filter((c) => {
        const ans = userAnswers[c.id];
        return ans && !ans.isCorrect;
      });
    }
    return list;
  }, [cards, filterDifficulty, showReviewOnly, userAnswers]);

  // Statistics calculation
  const totalAnswered = Object.keys(userAnswers).length;
  const correctCount = Object.values(userAnswers).filter((a) => a.isCorrect).length;
  const accuracyPct = totalAnswered > 0 ? Math.round((correctCount / totalAnswered) * 100) : 0;
  const isComplete = cards.length > 0 && totalAnswered === cards.length;

  const handleCardAnswer = (cardId: number, selectedId: string, isCorrect: boolean) => {
    setUserAnswers((prev) => ({
      ...prev,
      [cardId]: { selectedId, isCorrect },
    }));
  };

  const handleReset = () => {
    setUserAnswers({});
    setShowReviewOnly(false);
  };

  return (
    <div className="space-y-6">
      {/* ── ARENA HEADER CONTROL BAR ──────────────────────────── */}
      <div className="glass-panel rounded-2xl border border-white/10 bg-zinc-950/80 p-5 sm:p-6 shadow-xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Left stats */}
          <div className="flex items-center gap-6">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">
                Progress
              </div>
              <div className="font-mono text-base font-bold text-white">
                {totalAnswered} <span className="text-zinc-500">/ {cards.length}</span>
              </div>
            </div>

            <div className="h-8 w-px bg-white/10" />

            <div>
              <div className="font-mono text-[10px] uppercase tracking-wider text-zinc-400 font-semibold">
                Accuracy Score
              </div>
              <div className="flex items-baseline gap-2 font-mono text-base font-bold text-white">
                <span>{correctCount} correct</span>
                {totalAnswered > 0 && (
                  <span
                    className={`text-xs ${
                      accuracyPct >= 80
                        ? "text-emerald-400"
                        : accuracyPct >= 50
                        ? "text-amber-400"
                        : "text-red-400"
                    }`}
                  >
                    ({accuracyPct}%)
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Right difficulty filter tabs & actions */}
          <div className="flex items-center gap-3">
            <div className="flex rounded-xl border border-white/10 bg-zinc-900/80 p-1">
              {["all", "easy", "medium", "hard"].map((diff) => (
                <button
                  key={diff}
                  onClick={() => setFilterDifficulty(diff)}
                  className={`rounded-lg px-3 py-1 font-mono text-[11px] uppercase tracking-wider transition-colors ${
                    filterDifficulty === diff
                      ? "bg-white text-zinc-950 font-bold shadow-md"
                      : "text-zinc-400 hover:text-white"
                  }`}
                >
                  {diff}
                </button>
              ))}
            </div>

            {totalAnswered > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleReset}
                className="gap-1.5"
              >
                <RotateCcw className="h-3.5 w-3.5 text-zinc-400" />
                <span>Reset</span>
              </Button>
            )}
          </div>
        </div>

        {/* Progress bar line */}
        <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-zinc-900">
          <div
            className="h-full bg-white transition-all duration-300"
            style={{ width: `${(totalAnswered / Math.max(cards.length, 1)) * 100}%` }}
          />
        </div>
      </div>

      {/* ── COMPLETION SUMMARY BANNER ─────────────────────────── */}
      {isComplete && (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-6 text-center backdrop-blur-xl shadow-xl space-y-3">
          <div className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-emerald-400 font-bold">
            <Trophy className="h-4 w-4" />
            <span>Arena Complete · Examination Report</span>
          </div>
          <div className="font-display text-3xl font-bold text-white">
            Score: {accuracyPct}% ({correctCount}/{cards.length})
          </div>
          <p className="max-w-[60ch] mx-auto font-sans text-sm text-zinc-300 leading-relaxed">
            {accuracyPct >= 90
              ? "Mastery Level: Exceptional comprehension of document concepts!"
              : accuracyPct >= 70
              ? "Solid Performance: Strong understanding with minor review needed."
              : "Study Recommended: Review the document summary and retake missed questions."}
          </p>

          {cards.length - correctCount > 0 && (
            <div className="pt-2 flex justify-center gap-4">
              <Button
                variant="outline"
                onClick={() => setShowReviewOnly(!showReviewOnly)}
                className="border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/20"
              >
                {showReviewOnly ? "Show All Questions" : `Review ${cards.length - correctCount} Incorrect Answers`}
              </Button>
            </div>
          )}
        </div>
      )}

      {/* ── CARDS GRID ────────────────────────────────────────── */}
      <div className="grid gap-6">
        {filteredCards.length > 0 ? (
          filteredCards.map((card) => (
            <QuizCardWithCallback
              key={card.id}
              card={card}
              onAnswer={(selectedId, isCorrect) => handleCardAnswer(card.id, selectedId, isCorrect)}
              savedAnswer={userAnswers[card.id]}
            />
          ))
        ) : (
          <div className="rounded-2xl border border-white/10 bg-zinc-950/60 p-12 text-center font-mono text-xs text-zinc-500">
            No questions found for difficulty filter: &quot;{filterDifficulty.toUpperCase()}&quot;
          </div>
        )}
      </div>
    </div>
  );
};

// Internal wrapper passing user answers up to Arena
const QuizCardWithCallback: React.FC<{
  card: QuizCardType;
  onAnswer: (selectedId: string, isCorrect: boolean) => void;
  savedAnswer?: { selectedId: string; isCorrect: boolean };
}> = ({ card, onAnswer, savedAnswer }) => {
  // Derived, not local state. This used to be a useState seeded from
  // savedAnswer in its initializer only, so Reset (which clears the arena's
  // answer map) never propagated down: cards kept showing their answers and
  // kept pointerEvents:"none", making them permanently unanswerable.
  const selected = savedAnswer?.selectedId ?? null;

  const handleSelect = (optionId: string) => {
    if (selected !== null) return;
    const chosenOpt = card.options.find((o) => o.id === optionId);
    onAnswer(optionId, chosenOpt ? chosenOpt.correct : false);
  };

  const labels = ["A", "B", "C", "D"];

  return (
    <div className="glass-panel rounded-2xl border border-white/10 bg-zinc-950/70 p-6 shadow-xl space-y-5">
      <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-zinc-400">
        <span>Q · {String(card.id).padStart(2, "0")}</span>
        <div className="flex items-center gap-2">
          {card.metadata?.difficulty && (
            <Badge variant="outline">{card.metadata.difficulty}</Badge>
          )}
          <span className="text-zinc-300 font-semibold">{card.title}</span>
        </div>
      </div>

      <div className="font-display text-xl font-bold leading-snug text-white">
        {card.question}
      </div>

      {/* radiogroup: these were <li onClick> with no role, tabIndex or key
          handler, so the quiz was unusable without a mouse. */}
      <ul className="space-y-2.5" role="radiogroup" aria-label={card.question}>
        {card.options.map((opt, i) => {
          const label = labels[i] ?? String(i);
          const isPicked = selected === opt.id;
          const showResult = selected !== null;
          const isCorrect = opt.correct;

          let cls =
            "flex items-center gap-3 rounded-xl border px-4 py-3.5 font-sans text-sm transition-all cursor-pointer ";
          let chipCls = "font-mono text-xs uppercase font-bold tracking-wider ";

          if (!showResult) {
            cls += "border-white/10 bg-zinc-900/60 text-zinc-200 hover:border-white/30 hover:bg-zinc-800/80";
            chipCls += "text-zinc-500";
          } else if (isPicked && isCorrect) {
            cls += "border-emerald-500/50 bg-emerald-500/15 text-white font-medium";
            chipCls += "text-emerald-400";
          } else if (isPicked && !isCorrect) {
            cls += "border-red-500/50 bg-red-500/15 text-white font-medium";
            chipCls += "text-red-400";
          } else if (isCorrect) {
            cls += "border-emerald-500/40 bg-emerald-500/5 text-zinc-300";
            chipCls += "text-emerald-400";
          } else {
            cls += "border-white/5 bg-transparent text-zinc-500 opacity-60";
            chipCls += "text-zinc-600";
          }

          return (
            <li key={opt.id} role="none">
              <div
                role="radio"
                aria-checked={isPicked}
                aria-disabled={showResult}
                tabIndex={showResult ? -1 : 0}
                className={cls}
                onClick={() => handleSelect(opt.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleSelect(opt.id);
                  }
                }}
                style={{ pointerEvents: selected ? "none" : "auto" }}
              >
              <span className={chipCls}>{label}</span>
              <span className="flex-1">{opt.text}</span>
              {showResult && isCorrect && (
                <span className="inline-flex items-center gap-1 text-emerald-400 text-xs font-mono font-semibold">
                  <CheckCircle2 className="h-4 w-4" /> Correct
                </span>
              )}
              {showResult && isPicked && !isCorrect && (
                <span className="inline-flex items-center gap-1 text-red-400 text-xs font-mono font-semibold">
                  <XCircle className="h-4 w-4" /> Incorrect
                </span>
              )}
              </div>
            </li>
          );
        })}
      </ul>

      {selected && card.explanation && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 space-y-1">
          <div className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-amber-400 font-semibold">
            <HelpCircle className="h-3.5 w-3.5" />
            <span>Explanation &amp; Document Evidence</span>
          </div>
          <div className="font-sans text-sm leading-relaxed text-zinc-300">
            {card.explanation}
          </div>
        </div>
      )}
    </div>
  );
};
