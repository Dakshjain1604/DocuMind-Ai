"use client";

import React, { useState } from "react";

type Option = {
  id: string;
  text: string;
  correct: boolean;
};

type QuizCardProps = {
  card: {
    id: number;
    title: string;
    question: string;
    options: Option[];
    explanation?: string;
  };
};

export const QuizCard: React.FC<QuizCardProps> = ({ card }) => {
  const [selected, setSelected] = useState<string | null>(null);
  const handleSelect = (optionId: string) => {
    if (selected === null) setSelected(optionId);
  };

  const labels = ["A", "B", "C", "D"];

  return (
    <div className="regmark border border-[var(--rule)] bg-[var(--ink-2)] p-6">
      <span className="rm-tr" />
      <span className="rm-bl" />

      <div className="mb-3 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--paper-3)]/55">
        <span>Q · {String(card.id).padStart(2, "0")}</span>
        <span className="text-[var(--vermillion)]">{card.title}</span>
      </div>

      <div className="mb-5 font-display text-[24px] leading-[1.25] text-[var(--paper)]">
        {card.question}
      </div>

      <ul className="space-y-2">
        {card.options.map((opt, i) => {
          const label = labels[i] ?? String(i);
          const isPicked = selected === opt.id;
          const showResult = selected !== null;
          const isCorrect = opt.correct;

          let cls =
            "flex items-center gap-3 border px-4 py-3 font-sans text-[15px] transition-colors cursor-pointer ";
          let chipCls = "font-mono text-[11px] uppercase tracking-[0.15em] ";

          if (!showResult) {
            cls += "border-[var(--rule)] bg-[var(--ink)] text-[var(--paper)] hover:border-[var(--vermillion)]/60";
            chipCls += "text-[var(--paper-3)]/50";
          } else if (isPicked && isCorrect) {
            cls += "border-[#10b981] bg-[#10b981]/15 text-[var(--paper)]";
            chipCls += "text-[#10b981]";
          } else if (isPicked && !isCorrect) {
            cls += "border-[var(--vermillion)] bg-[var(--vermillion)]/15 text-[var(--paper)]";
            chipCls += "text-[var(--vermillion-hot)]";
          } else if (isCorrect) {
            cls += "border-[#10b981]/60 bg-transparent text-[var(--paper-3)]/80";
            chipCls += "text-[#10b981]";
          } else {
            cls += "border-[var(--rule)] bg-transparent text-[var(--paper-3)]/40";
            chipCls += "text-[var(--paper-3)]/30";
          }

          return (
            <li
              key={opt.id}
              className={cls}
              onClick={() => handleSelect(opt.id)}
              style={{ pointerEvents: selected ? "none" : "auto" }}
            >
              <span className={chipCls}>{label}</span>
              <span>{opt.text}</span>
            </li>
          );
        })}
      </ul>

      {selected && card.explanation && (
        <div className="mt-5 border-l-2 border-[var(--ochre)] bg-[var(--ochre)]/10 px-4 py-3">
          <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--ochre)]">
            note · explanation
          </div>
          <div className="font-sans text-[14px] leading-[1.55] text-[var(--paper-3)]/90">
            {card.explanation}
          </div>
        </div>
      )}
    </div>
  );
};
