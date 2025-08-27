"use client";
import { UploadIcon } from "../icons/uploadIcon";
import { Homecard } from "../components/HomeCard";

import { useState} from "react";
import axios from "axios";
import { QuizCard } from "../components/QuizCard";
import { ChatInput } from "../components/Chatinput";
import Markdown from "react-markdown";
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL;

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
    
    // scroll properties 

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
            const response = await axios.post(`${BACKEND_URL}/RAG`, formdata, {
                headers: { 'Content-Type': 'multipart/form-data' },
                timeout: 120000,
            });
          
            setChatMessages(prev => [...prev, { type: 'ai', message: response.data.answer }]);
            
            setCurrentQuery("");
        }
        catch  {
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
        scrollToSection("text-box");
        if (endpoint == "/RAG") {
            handleChatQuery();
        } else {
            try {
                // Post file to backend endpoint
                const response = await axios.post(
                    `${BACKEND_URL}`+`${endpoint}`,
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
            } catch (e: unknown) {
                console.error("API error:", e);
            
                let errorMsg = "Upload error occurred!";
            
                if (e && typeof e === "object" && "response" in e && e.response && typeof e.response === "object") {
                    const response = e.response as { data?: { message?: string } };
                    if (response.data) {
                        errorMsg = response.data.message || JSON.stringify(response.data);
                    }
                } else if (e instanceof Error) {
                    errorMsg = e.message;
                }
            
                setError(errorMsg);
                setIsLoading(false);
            }
            
        }
    }


    return (
        <div className="flex flex-col items-center min-h-screen bg-gradient-to-br from-black via-gray-900 to-gray-800">

            <div className="w-full max-w-7xl flex-col flex justify-around font-sans items-center mx-auto py-4 sm:py-6 md:py-10 px-2 sm:px-4">
                {/* Upload Section */}
                <div className="flex w-full justify-center items-center mb-6 sm:mb-8 md:mb-10">
                    <div className="flex flex-col justify-center items-center bg-white rounded-xl px-4 sm:px-6 md:px-10 py-6 md:py-8 shadow-lg border border-gray-200 w-full max-w-md sm:max-w-lg">
                        <div className="text-xl sm:text-2xl md:text-3xl lg:text-4xl text-black font-sans font-bold mb-2 tracking-tight text-center">
                            Super Charge Your Learning ⚡️
                        </div>
                        <div className="mb-2 mt-4">
                            <UploadIcon />
                        </div>
                        <div className="text-black text-sm sm:text-base md:text-lg mb-2 text-center">
                            Upload document (.pdf, .txt , .docx)
                        </div>
                        <div className="mt-2 w-full">
                            <input
                                onChange={handleFileChange}
                                type="file"
                                className="mt-2 block w-full text-xs sm:text-sm text-black file:hover:scale-105 file:mr-2 sm:file:mr-4 file:py-1.5 sm:file:py-2 file:px-2 sm:file:px-4 file:rounded-full file:border-0 file:text-xs sm:file:text-sm file:font-semibold file:bg-black file:text-white transition-all duration-200 file:animate-bounce"
                                accept=".pdf,.txt,.doc,.docx"
                            />
                        </div>
                    </div>
                </div>
                
                {/* Feature Cards Section */}
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-6 lg:gap-8 mb-6 sm:mb-8 w-full max-w-4xl mx-auto">
                    <div className="w-full sm:w-1/3 max-w-xs">
                        <Homecard
                            heading="Quiz"
                            mainText="Transform your study materials into engaging quizzes. Test your knowledge and reinforce learning with AI-generated questions."
                            ButtonText="Generate Quiz"
                            onClick={() => handleApi("/getQuiz")}
                        />
                    </div>
                    <div className="w-full sm:w-1/3 max-w-xs">
                        <Homecard
                            heading="Summary"
                            mainText="Get concise, intelligent summaries of your lengthy documents in seconds. Extract key insights without reading through pages of content."
                            ButtonText="Summarize"
                            onClick={() => handleApi("/getSummary")}
                        />
                    </div>
                    <div className="w-full sm:w-1/3 max-w-xs">
                        <Homecard
                            heading="Custom Q&A"
                            mainText="Ask any question about your documents and get precise, contextual answers. Your personal AI research assistant"
                            ButtonText="Chat with AI"
                            onClick={() => ClickHandle("/RAG")}
                        />
                    </div>
                </div>
            </div>
            
            {/* Disclaimer */}
            <div className="opacity-50 text-center text-xs sm:text-sm px-4 mb-4"> 
                The data is fetched from render(free version), so it might take a few seconds to respond due to inactivity! 
            </div>
            
            {/* Results Section */}
            <div
                className="w-full max-w-6xl border-white border-2 flex justify-center mt-4 sm:mt-6 md:mt-10 rounded-xl min-h-[300px] sm:min-h-[400px] bg-gray-100/80 shadow-lg mx-2 sm:mx-4 lg:mx-auto"
                id="text-box"
            >
                {/* Loading State */}
                {isLoading && (
                    <div className="flex justify-center items-center p-4">
                        <span className="text-black flex flex-col sm:flex-row text-base sm:text-xl items-center text-center">
                            <span className="mb-2 sm:mb-0 text-lg text-black">Loading ...</span>
                            {/* <div className="sm:pl-5">
                                <LoadingIcon />
                            </div> */}
                            <div className=" text-x2l bg-transparent py-10 animate-bounce"> 📚 📝 📘 📙 📑 💻 🖥️ </div>
                        </span>
                    </div>
                )}
                
                {/* Error State */}
                {!isLoading && error && (
                    <div className="bg-red-50 p-4 m-2 sm:m-4 rounded-xl shadow-inner border border-red-200 w-full">
                        <h3 className="text-base sm:text-lg font-semibold mb-2 text-red-900">Error:</h3>
                        <div className="text-red-700 text-sm sm:text-base break-words">{error}</div>
                    </div>
                )}
                
                {/* Quiz cards rendering */}
                {!isLoading && view === "quiz" && quiz && quiz.cards.length > 0 && (
                    <div className="w-full grid gap-4 sm:gap-6 p-2 sm:p-4">
                        <div className="mb-2 sm:mb-4 text-lg sm:text-xl font-bold text-gray-800 bg-white px-4 sm:px-6 py-2 sm:py-3 rounded shadow">
                            Total Questions: {quiz.total_questions}
                        </div>
                        {quiz.cards.map((card) => (
                            <QuizCard key={card.id} card={card} />
                        ))}
                    </div>
                )}
                
                {/* Summary rendering */}
                {!isLoading && view === "summary" && summary && (
                    <div className="bg-blue-50 p-2 sm:p-4 m-2 sm:m-4 rounded-xl shadow-inner max-h-full overflow-y-auto border border-blue-200 w-full">
                        <h3 className="text-base sm:text-lg font-semibold mb-2 text-blue-900">
                            Document Summary:
                        </h3>
                        <div className="whitespace-pre-wrap prose max-w-none p-2 text-gray-900 font-bold text-sm sm:text-base">
                            <Markdown>{summary}</Markdown>
                        </div>
                    </div>
                )}

                {/* Chat rendering */}
                {!isLoading && view === "chat" && isRagMode && (
                    <div className="w-full p-2 sm:p-4 text-black">
                        <div className="mb-4 max-h-64 sm:max-h-96 overflow-y-bottom space-y-3" >
                            {chatMessages.map((msg, idx) => (
                                <div key={idx} className={`p-2 sm:p-3 rounded-lg text-sm sm:text-base ${
                                    msg.type === 'user' 
                                        ? 'bg-blue-100 ml-auto max-w-[85%] sm:max-w-xs' 
                                        : 'bg-gray-100 mr-auto max-w-[90%] sm:max-w-md'
                                }`}>
                                    <div className="text-xs sm:text-sm font-semibold mb-1">
                                        {msg.type === 'user' ? 'You' : 'AI'}
                                    </div>
                                    <div className="break-words bottom-0"  >{msg.message}</div>
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