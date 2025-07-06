'use client'
import { UploadIcon } from "../icons/uploadIcon"
import { Homecard } from "../components/HomeCard"
import { useRouter } from 'next/navigation'
import { useState } from "react"
import axios from "axios"

export default function Dashboard() {
    const [upload, setUpload] = useState(true);
    const [render, setRender] = useState(false);
    
    const router = useRouter();
    
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [content, setContent] = useState("");
    const [quiz,SetQuiz]=useState([[]]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState("");
    
    const scrollToSection = (id: string) => {
        const element = document.getElementById(id);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };
    
    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            
            // Clear previous summary and error when new file is selected
            setContent("");
            setError("");
        }
    };
    function ClickHandle(location: string) {
        scrollToSection('text-box');
        if (selectedFile) {
            getApi(location);
        } else {
            alert("Please upload a file first.");
        }
    }


    async function getApi(endPoint: string) {

        if (!selectedFile) {
            alert("Please upload a file first.");
            return;
        }

        setIsLoading(true);
        setError("");
        setContent("");

        const formData = new FormData();
        formData.append("file", selectedFile);

        // Debug: Log the endpoint being called
        const fullUrl = `http://localhost:8000${endPoint}`;
        console.log("Making API call to:", fullUrl);

        try {
            const response = await axios.post(fullUrl, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
                timeout: 120000,
            });

          
          setContent(response.data.summary || response.data.result || response.data);
            
            console.log("API Response:", response.data);
            setRender(true);
            setIsLoading(false);
        } catch  {
            console.error("Upload error:", error);
            console.error("Full error details:", error);
            
            let errorMessage = "Upload error occurred! ";
        
                errorMessage += (error);
            
            setError(errorMessage);
            setIsLoading(false);
        }
    }

    return (
        <div className="flex flex-col items-center bg-black">
            <div className="h-screen w-screen flex-col flex justify-around font-sans items-center">
                <div className="flex w-screen justify-center items-center mt-10">
                    <div className="flex flex-col justify-center items-center bg-white rounded-md px-10 py-8">
                        <div className="text-4xl text-black font-sans font-bold">
                            Super Charge Your Learning ⚡️   
                        </div>
                        <div className="mb-2 mt-4">
                            <UploadIcon />
                        </div>

                        <div className="text-black text-lg">Upload document (.pdf, .txt , .docx)</div>
                        <div className="mt-5">
                            <input
                                onChange={handleFileChange} 
                                type="file"
                                className="mt-2 block w-full text-sm text-black file:hover:scale-105 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-black file:text-white transition-all duration-200 file:animate-bounce"
                                accept=".pdf,.txt,.doc,.docx"
                                
                            />
                        </div>
                    </div>
                </div>

                <div className="flex items-center justify-center gap-10">
                    <Homecard 
                    
                        heading="Quiz" 
                        mainText="Transform your study materials into engaging quizzes. Test your knowledge and reinforce learning with AI-generated questions."
                        ButtonText="Generate Quiz" 

                        onClick={() => ClickHandle("/getQuiz")}
                    />
                    <Homecard 
                        heading="Summary" 
                        mainText="Get concise, intelligent summaries of your lengthy documents in seconds. Extract key insights without reading through pages of content." 
                        ButtonText="Summarize" 
                        onClick={() => ClickHandle("/getSummary")}
                    />  
                    <Homecard 
                        heading="Custom Q&A" 
                        mainText="Ask any question about your documents and get precise, contextual answers. Your personal AI research assistant" 
                        ButtonText="Chat with AI"
                        onClick={() => ClickHandle("/getChat")}
                    />
                </div>
            </div>
            
            {render && (
                <div className="w-[80%] border-white border-2 flex justify-center mt-20 rounded-md h-screen bg-gray-100/80" id="text-box">
                    {isLoading && (
                        <div className="flex justify-center items-center">
                            <span className="text-black">Processing your document, please wait...</span>
                        </div>
                    )}
                    
                    {content && !isLoading && (
                        <div className="bg-blue-50 p-4 rounded-xl shadow-inner max-h-full overflow-y-auto border border-blue-200 px-10 py-2">
                            <h3 className="text-lg font-semibold mb-2 text-blue-900">Document Summary:</h3>
                            <div className="whitespace-pre-wrap prose max-w-none p-2 text-gray-900 font-bold">{content}</div>
                        </div>
                    )}
                
                    {error && (
                        <div className="bg-red-50 p-4 rounded-xl shadow-inner border border-red-200">
                            <h3 className="text-lg font-semibold mb-2 text-red-900">Error:</h3>
                            <div className="text-red-700">{error}</div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}