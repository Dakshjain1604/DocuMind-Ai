import React from 'react';

interface ChatInputProps {
    currentQuery: string | undefined;
    setCurrentQuery: (query: string) => void;
    handleChatQuery: () => void;
    isLoading: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ 
    currentQuery, 
    setCurrentQuery, 
    handleChatQuery, 
    isLoading 
}) => {
    const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && !isLoading && currentQuery && currentQuery.trim()) {
            handleChatQuery();
        }
    };

    return (
        <div className="flex gap-2 p-4 bg-white rounded-lg shadow">
            <input
                value={currentQuery || ""}
                onChange={(e) => setCurrentQuery(e.target.value)}
                placeholder="Ask a question about your document..."
                className="flex-1 p-2 border rounded focus:outline-none focus:border-blue-500"
                onKeyPress={handleKeyPress}
                disabled={isLoading}
                type="text"
            />
            <button 
                onClick={handleChatQuery} 
                disabled={isLoading || !currentQuery || !currentQuery.trim()} 
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400 transition-colors"
            >
                {isLoading ? "..." : "Send"}
            </button>
        </div>
    );
};