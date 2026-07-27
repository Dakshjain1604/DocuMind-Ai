"use client";

import { Check, Copy, Mic, Presentation, Volume2 } from "lucide-react";

import { Coverage, Slide } from "../types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CoverageNote, ErrorBanner } from "@/components/ui/ErrorBanner";

/** Podcast script and presentation outline, generated on demand. */
export function AudioSlidesPanel({
  audio,
  slides,
}: {
  audio: {
    script: string;
    loading: boolean;
    error?: string;
    coverage?: Coverage;
    copied: boolean;
    onGenerate: () => void;
    onCopy: () => void;
  };
  slides: {
    items: Slide[];
    loading: boolean;
    error?: string;
    coverage?: Coverage;
    onGenerate: () => void;
  };
}) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        {/* Disabled while in flight — these used to stay clickable, so a
            double-click fired concurrent generations. */}
        <Button
          variant={audio.script ? "default" : "outline"}
          size="sm"
          disabled={audio.loading}
          onClick={audio.onGenerate}
          className="gap-2"
        >
          <Mic className="h-4 w-4" />
          <span>Generate Audio Podcast Script</span>
        </Button>
        <Button
          variant={slides.items.length > 0 ? "default" : "outline"}
          size="sm"
          disabled={slides.loading}
          onClick={slides.onGenerate}
          className="gap-2"
        >
          <Presentation className="h-4 w-4" />
          <span>Generate Presentation Deck</span>
        </Button>
      </div>

      {audio.loading && (
        <Card className="p-8 text-center space-y-3">
          <Skeleton className="h-24 w-full" />
          <div className="font-mono text-xs text-zinc-400">
            Synthesizing two-host conversational podcast script…
          </div>
        </Card>
      )}

      {!audio.loading && audio.error && (
        <ErrorBanner message={audio.error} onRetry={audio.onGenerate} />
      )}

      {audio.script && (
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-3 font-mono text-xs text-zinc-400 font-semibold">
            <span className="flex items-center gap-2">
              <Volume2 className="h-4 w-4 text-indigo-400" />
              <span>Executive Podcast Script</span>
            </span>
            <Button variant="ghost" size="sm" onClick={audio.onCopy}>
              {audio.copied ? (
                <Check className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <Copy className="h-3.5 w-3.5 text-zinc-400" />
              )}
              <span>{audio.copied ? "Copied" : "Copy Script"}</span>
            </Button>
          </div>
          <div className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-zinc-200 bg-zinc-900/60 p-5 rounded-xl border border-white/5">
            {audio.script}
          </div>
          <CoverageNote coverage={audio.coverage} />
        </Card>
      )}

      {slides.loading && (
        <Card className="p-8 text-center space-y-3">
          <Skeleton className="h-32 w-full" />
          <div className="font-mono text-xs text-zinc-400">
            Generating executive presentation cards…
          </div>
        </Card>
      )}

      {!slides.loading && slides.error && (
        <ErrorBanner message={slides.error} onRetry={slides.onGenerate} />
      )}

      {slides.items.length > 0 && (
        <div className="space-y-3">
          <div className="grid gap-4 sm:grid-cols-2">
            {slides.items.map((slide) => (
              <Card key={slide.slide} className="p-6 space-y-4 flex flex-col justify-between">
                <div>
                  <Badge variant="default" className="mb-2">
                    Slide {slide.slide}
                  </Badge>
                  <h4 className="font-display text-lg font-bold text-white mb-3">{slide.title}</h4>
                  <ul className="space-y-2 font-sans text-sm text-zinc-300">
                    {slide.bullets?.map((b, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-indigo-400 font-bold">•</span>
                        <span>{b}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                {slide.speaker_notes && (
                  <div className="pt-3 border-t border-white/10 font-mono text-xs text-zinc-400">
                    <span className="text-zinc-500 font-semibold">Speaker Notes:</span>{" "}
                    {slide.speaker_notes}
                  </div>
                )}
              </Card>
            ))}
          </div>
          <CoverageNote coverage={slides.coverage} />
        </div>
      )}
    </div>
  );
}
