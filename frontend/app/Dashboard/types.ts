/** Envelope every studio endpoint returns. Mirrors microService/app/routes/schemas.py. */
export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  error?: { code: string; message: string };
}

/** How much of the document a generated artifact was actually derived from. */
export interface Coverage {
  sampled_chunks: number;
  total_chunks: number;
  unit: "parent_chunks" | "child_chunks";
  strategy: string;
  is_partial: boolean;
}

export type StudioKey = "summary" | "quiz" | "audit" | "audio" | "slides";

/** Loose bag for the varying `data` payloads across studio endpoints. */
export type StudioEnvelopeData = Record<string, unknown> & { coverage?: Coverage };

export interface AuditFinding {
  id: number;
  severity: "high" | "medium" | "low" | string;
  category: string;
  finding: string;
  mitigation: string;
}

export interface Slide {
  slide: number;
  title: string;
  bullets: string[];
  speaker_notes?: string;
}

export interface TelemetryStats {
  total_requests?: number;
  avg_latency_ms?: number;
  total_tokens_in?: number;
  total_tokens_out?: number;
}

export interface QuizOptionType {
  id: string;
  text: string;
  correct: boolean;
}

export interface QuizCardType {
  id: number;
  type: string;
  title: string;
  question: string;
  options: QuizOptionType[];
  correctAnswer: string;
  explanation?: string;
  metadata?: {
    difficulty?: string;
    category?: string;
  };
}
