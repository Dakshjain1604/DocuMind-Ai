"use client";
import { UploadIcon } from "../icons/uploadIcon";
import { Homecard } from "../components/HomeCard";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import axios from "axios";
import { QuizCard } from "../components/QuizCard";
import LoadingIcon from "../icons/loadingIcon";
import { ChatInput } from "../components/Chatinput";


export default function Dashboard() {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [quiz, setQuiz] = useState<{
        total_questions: number;
        cards: any[];
    } | null>(null);
    const [summary, setSummary] = useState<string>("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState("");
    const [view, setView] = useState<"quiz" | "summary" | "chat" | "none">(
        "none"
    );
    const [chatMessages, setChatMessages] = useState<
        { type: "user" | "ai"; message: string }[]
    >([]);
    const [currentQuery, setCurrentQuery] = useState("");
    const [isRagMode, setIsRagMode] = useState(false);
    const router = useRouter();

    const scrollToSection = (id: string) => {
        const element = document.getElementById(id);
        if (element) {
            element.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    };

  
    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            setQuiz(null);
            setSummary("");
            setChatMessages([]); // Clear chat history
            setIsRagMode(false);
            setError("");
            setView("none");
        }
    };

    function ClickHandle(location: string) {
        scrollToSection("text-box");
        if (selectedFile) {
            if (location === "/RAG") {
                setIsRagMode(true);
                setView("chat");
                setChatMessages([]);
            }
            else {
                handleApi(location);
            }

        } else {
            alert("Please upload a file first.");
        }
    }

    async function handleChatQuery() {
        if (!currentQuery.trim() || !selectedFile) return;

        setChatMessages(prev => [...prev, { type: 'user', message: currentQuery }]);
        setIsLoading(true);
        const formdata = new FormData();
        formdata.append("file", selectedFile);
        formdata.append("input", currentQuery);

        try {
            const response = await axios.post("http://localhost:8000/RAG", formdata, {
                headers: { 'Content-Type': 'multipart/form-data' },
                timeout: 120000,
            });
            setChatMessages(prev => [...prev, { type: 'ai', message: response.data.answer }]);
            setCurrentQuery("");
        }
        catch (e) {
            setError("failed to get response from AI")
        }
        setIsLoading(false)

    }
   



    async function handleApi(endpoint: string) {
        if (!selectedFile) {
            alert("Please upload a file first.");
            return;
        }
        setIsLoading(true);
        setError("");
        setQuiz(null);
        setSummary("");
        setView("none");
        const formData = new FormData();
        formData.append("file", selectedFile);
        if (endpoint == "/RAG") {
            handleChatQuery();
        } else {
            try {
                // Post file to backend endpoint
                const response = await axios.post(
                    `http://localhost:8000${endpoint}`,
                    formData,
                    {
                        headers: { "Content-Type": "multipart/form-data" },
                        timeout: 120000,
                    }
                );
                console.log("API response:", response.data); // Debug log
                // If quiz endpoint, extract quiz data from response
                if (endpoint === "/getQuiz" && response.data?.summary?.data?.cards) {
                    setQuiz({
                        total_questions: response.data.summary.data.total_questions,
                        cards: response.data.summary.data.cards,
                    });
                    setView("quiz");
                } else {
                    // Otherwise, treat as summary
                    let result = response.data.summary || response.data.result;
                    if (typeof result !== "string") {
                        result = response.data.message || "No summary available.";
                    }
                    setSummary(result);
                    setView("summary");
                }
                setIsLoading(false);
            } catch (e: any) {
                // Log the error for debugging
                console.error("API error:", e);
                // Try to extract a more informative error message
                let errorMsg = "Upload error occurred!";
                if (e.response && e.response.data) {
                    errorMsg = e.response.data.message || JSON.stringify(e.response.data);
                } else if (e.message) {
                    errorMsg = e.message;
                }
                setError(errorMsg);
                setIsLoading(false);
            }
        }
    }


    return (
        <div className="flex flex-col items-center min-h-screen bg-gradient-to-br from-black via-gray-900 to-gray-800">

            <div className="w-full max-w-5xl flex-col flex justify-around font-sans items-center mx-auto py-10 px-4">
                <div className="flex w-full justify-center items-center mb-10">
                    <div className="flex flex-col justify-center items-center bg-white rounded-xl px-10 py-8 shadow-lg border border-gray-200">
                        <div className="text-4xl text-black font-sans font-bold mb-2 tracking-tight">
                            Super Charge Your Learning ⚡️
                        </div>
                        <div className="mb-2 mt-4">
                            <UploadIcon />
                        </div>
                        <div className="text-black text-lg mb-2">
                            Upload document (.pdf, .txt , .docx)
                        </div>
                        <div className="mt-2">
                            <input
                                onChange={handleFileChange}
                                type="file"
                                className="mt-2 block w-full text-sm text-black file:hover:scale-105 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-black file:text-white transition-all duration-200 file:animate-bounce"
                                accept=".pdf,.txt,.doc,.docx"
                            />
                        </div>
                    </div>
                </div>
                
                <div className="flex items-center justify-center gap-8 mb-8 w-full max-w-4xl mx-auto">
                    <Homecard
                        heading="Quiz"
                        mainText="Transform your study materials into engaging quizzes. Test your knowledge and reinforce learning with AI-generated questions."
                        ButtonText="Generate Quiz"
                        onClick={() => handleApi("/getQuiz")}
                    />
                    <Homecard
                        heading="Summary"
                        mainText="Get concise, intelligent summaries of your lengthy documents in seconds. Extract key insights without reading through pages of content."
                        ButtonText="Summarize"
                        onClick={() => handleApi("/getSummary")}
                    />
                    <Homecard
                        heading="Custom Q&A"
                        mainText="Ask any question about your documents and get precise, contextual answers. Your personal AI research assistant"
                        ButtonText="Chat with AI"
                        onClick={() => ClickHandle("/RAG")}
                    />
                </div>
            </div>
            <div className="opacity-50"> The data is fetched from a LLM , might take a few seconds to render </div>
            <div
                className="w-full max-w-3xl border-white border-2 flex justify-center mt-10 rounded-xl min-h-[400px] bg-gray-100/80 shadow-lg mx-auto"
                id="text-box"
            >
   
                {isLoading && (
                    <div className="flex justify-center items-center">
                        <span className="text-black flex text-xl items-center ">
                            Processing your document, please wait <div className="pl-5 "><LoadingIcon /></div>
                        </span>
                    </div>
                )}
                
                {!isLoading && error && (
                    <div className="bg-red-50 p-4 rounded-xl shadow-inner border border-red-200 w-full">
                        <h3 className="text-lg font-semibold mb-2 text-red-900">Error:</h3>
                        <div className="text-red-700">{error}</div>
                    </div>
                )}
                {/* Quiz cards rendering */}
                {!isLoading && view === "quiz" && quiz && quiz.cards.length > 0 && (
                    <div className="w-full grid gap-6">
                        <div className="mb-4 text-xl font-bold text-gray-800 bg-white px-6 py-3 rounded shadow">
                            Total Questions: {quiz.total_questions}
                        </div>
                        {quiz.cards.map((card) => (
                            <QuizCard key={card.id} card={card} />
                        ))}
                    </div>
                )}
                {/* Summary rendering */}
                {!isLoading && view === "summary" && summary && (
                    <div className="bg-blue-50 p-4 rounded-xl shadow-inner max-h-full overflow-y-auto border border-blue-200 px-10 py-2 w-full">
                        <h3 className="text-lg font-semibold mb-2 text-blue-900">
                            Document Summary:
                        </h3>
                        <div className="whitespace-pre-wrap prose max-w-none p-2 text-gray-900 font-bold">
                            {summary}
                        </div>
                    </div>
                )}


                {!isLoading && view === "chat" && isRagMode && (
                    <div className="w-full p-4 text-black">
                        <div className="mb-4 max-h-96 overflow-y-auto space-y-3">
                            {chatMessages.map((msg, idx) => (
                                <div key={idx} className={`p-3 rounded-lg ${msg.type === 'user' ? 'bg-blue-100 ml-auto max-w-xs' : 'bg-gray-100 mr-auto max-w-md'}`}>
                                    <div className="text-sm font-semibold">{msg.type === 'user' ? 'You' : 'AI'}</div>
                                    <div>{msg.message}</div>
                                </div>
                            ))}
                        </div>
                        <ChatInput 
            currentQuery={currentQuery}
            setCurrentQuery={setCurrentQuery}
            handleChatQuery={handleChatQuery}
            isLoading={isLoading}
        />
                    </div>
                )}
            </div>
        </div>
    );
}



