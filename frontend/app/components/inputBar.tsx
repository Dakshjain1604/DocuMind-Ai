"use client";
import { useState } from "react";

import axios from "axios";

export function InputBar() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [content, setContent] = useState("");

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      // Clear previous summary and error when new file is selected
      setContent("");
      setError("");
    }
  };

  async function getSummary() {
    if (!selectedFile) {
      alert("Please upload a file first.");
      return;
    }

    setIsLoading(true);
    setError("");
    setContent("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    axios.post("http://localhost:8000/getSummary", formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000,
    })
    .then((response) => {
      setContent(response.data.summary);
      setIsLoading(false);
    })
    .catch((error) => {
      console.error("Upload error:", error);
      setError("Upload error occurred! " + (error.response?.data?.detail || error.message));
      setIsLoading(false);
    });
  }

  async function getQuiz() {
    if (!selectedFile) {
      alert("Please upload a file first.");
      return;
    }

    setIsLoading(true);
    setError("");
    setContent("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    axios.post("http://localhost:8000/getQuiz", formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000,
    })
    .then((response) => {
      setContent(response.data.summary);
      setIsLoading(false);
    })
    .catch((error) => {
      console.error("Upload error:", error);
      setError("Upload error occurred! " + (error.response?.data?.detail || error.message));
      setIsLoading(false);
    });
  }



  return (
    <div className="flex flex-col items-center w-screen justify-center">
      <div className="border border-gray-300 shadow-xl h-auto  max-w-md rounded-xl mt-2 flex flex-col justify-center items-center bg-white/80 backdrop-blur-md p-8 transition-all duration-300">
        <div className="flex flex-col justify-center items-center w-full">
          

          <input 
            type="file" 
            onChange={handleFileChange} 
            className="mt-2 block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 transition-all duration-200"
            accept=".pdf,.txt,.doc,.docx"
            disabled={isLoading}
          />
          
          <button
            onClick={getSummary}
            disabled={isLoading || !selectedFile}
            className={`text-md rounded-lg px-4 py-2 w-full mt-4 font-semibold shadow-md transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-50
              ${isLoading || !selectedFile 
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                : 'bg-blue-600 text-white hover:bg-blue-700 hover:scale-105'}
            `}
          >
            {isLoading ? "Processing..." : "Upload & Summarize"}
          </button>

          {selectedFile && (
            <p className="text-gray-700 text-xs mt-2 truncate max-w-full">
              Selected: <span className="font-medium">{selectedFile.name}</span>
            </p>
          )}
        </div>
      </div>

      <div className="flex justify-around items-center gap-4 mt-8 max-w-2xl w-full">
        <div className="text-sm w-full">
          {isLoading && (
            <div className="flex items-center space-x-2 text-blue-500">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
             
            </div>
          )}
          
          {error && (
            <div className="text-red-500 bg-red-100 p-3 rounded-md shadow">
              {error}
            </div>
          )}
          
          {content && !isLoading && (
            <div className="bg-blue-50 p-4 rounded-xl shadow-inner max-h-96 overflow-y-auto border border-blue-200 px-10 py-2">
              <h3 className="text-lg font-semibold mb-2 text-blue-900">Document Summary:</h3>
              <div className="whitespace-pre-wrap prose max-w-none p-2 text-gray-900 font-bold ">{content}</div>
            </div>
          )}
        </div> 
      </div>
    </div>
  );
}