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
