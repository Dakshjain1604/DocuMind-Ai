import React, { useState } from "react";

// Option type for each answer choice
// id: unique identifier for the option
// text: the display text for the option
// correct: whether this option is the correct answer
//
type Option = {
  id: string;
  text: string;
  correct: boolean;
};

// Props for the QuizCard component
// card: the quiz question object, including title, question, options, and explanation
//
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
    if (selected === null) {
      setSelected(optionId);
    }
  };

  // Render the quiz card
  return (
    // Card container with dark background and padding
    <div className="bg-gray-600 rounded-lg shadow-md p-6">
    
      <div className="text-lg font-semibold mb-2 text-white">{card.title}</div>
    
      <div className="mb-3 text-base text-white-200">{card.question}</div>
      
      <ul className="mb-3">
        {card.options.map((opt) => {
         
          let optionStyle =
            "px-4 py-2 mb-2 rounded border cursor-pointer transition-all select-none ";
          if (selected === null) {
            
            optionStyle += "bg-gray-200 border-gray-200 hover:bg-gray-400 text-black";
          } else if (opt.id === selected) {
          
            optionStyle += opt.correct
              ? "bg-green-200 border-green-500 text-green-900 font-semibold"
              : "bg-red-200 border-red-500 text-red-900 font-semibold";
          } else if (opt.correct) {
            
            optionStyle += "bg-green-100 border-green-400 text-green-800";
          } else {
           
            optionStyle += "bg-gray-100 border-gray-200 text-gray-400";
          }
          return (
            <li
              key={opt.id}
              className={optionStyle}
              onClick={() => handleSelect(opt.id)}
              style={{ pointerEvents: selected ? "none" : "auto" }}
            >
              {opt.text}
            </li>
          );
        })}
      </ul>
      {/* Show explanation only after an option is selected */}
      {selected && card.explanation && (
        <div className="mt-2 text-md font-semibold text-blue-800 bg-blue-50 p-2 rounded">
          <b>Explanation:</b> {card.explanation}
        </div>
      )}
    </div>
  );
}; 