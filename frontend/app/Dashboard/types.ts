export interface QuizCardType {
  id: string | number;
  question: string;
  options: string[];
  answer: string;
}

export interface QuizType {
  total_questions: number;
  cards: QuizCardType[];
}

export type ChatMessageType = {
  type: "user" | "ai";
  message: string;
};

export interface ErrorResponse {
  response?: {
    data?: {
      message?: string;
    };
  };
}
