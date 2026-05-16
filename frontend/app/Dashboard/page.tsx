"use client";
import { UploadIcon } from "../icons/uploadIcon";
import { Homecard } from "../components/HomeCard";
import { ChatStream } from "../components/ChatStream";
import { GraphView } from "../components/GraphView";

import { useState } from "react";
import axios from "axios";
import { QuizCard } from "../components/QuizCard";
import Markdown from "react-markdown";

type View = "quiz" | "summary" | "chat" | "graph" | "none";

export default function Dashboard() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docHash, setDocHash] = useState<string | null>(null);
  const [indexProgress, setIndexProgress] = useState<string>("");
  const [quiz, setQuiz] = useState<{ total_questions: number; cards: any[] } | null>(null);
  const [summary, setSummary] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [view, setView] = useState<View>("none");
  const [highlightChunk, setHighlightChunk] = useState<string | null>(null);

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  async function indexFile(file: File) {
    setIndexProgress("uploading…");
    setError("");
    setDocHash(null);
    setQuiz(null);
    setSummary("");
    setView("none");

    const fd = new FormData();
    fd.append("file", file);

    try {
      const r = await fetch("/api/rag/index", { method: "POST", body: fd });
      if (!r.ok || !r.body) {
        setError(`Upload failed: ${r.status}`);
        setIndexProgress("");
        return;
      }
      const reader = r.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const evs = buf.split("\n\n");
        buf = evs.pop() ?? "";
        for (const block of evs) {
          const lines = block.split("\n");
          const evtLine = lines.find((l) => l.startsWith("event:"));
          const dataLine = lines.find((l) => l.startsWith("data:"));
          if (!evtLine || !dataLine) continue;
          const evt = evtLine.replace("event:", "").trim();
          const data = JSON.parse(dataLine.replace("data:", "").trim());
          if (evt === "done") {
            setDocHash(data.doc_hash);
            setIndexProgress(data.cached ? "cached ✓" : "indexed ✓");
          } else if (evt === "error") {
            setError(data.message ?? "indexing error");
            setIndexProgress("");
          } else {
            const label = evt.replace(/_/g, " ");
            const extra = data?.n_chunks ? ` (${data.n_chunks} chunks)` : data?.total ? ` (0/${data.total})` : "";
            setIndexProgress(`${label}${extra}…`);
          }
        }
      }
    } catch (e) {
      setError(String(e));
      setIndexProgress("");
    }
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    indexFile(file);
  };

  async function fetchQuiz() {
    if (!docHash) return alert("Index a document first.");
    scrollToSection("text-box");
    setIsLoading(true);
    setError("");
    setView("none");
    try {
      const r = await axios.post("/api/rag/quiz", { doc_hash: docHash });
      const cards = r.data?.data?.cards ?? [];
      setQuiz({ total_questions: r.data?.data?.total_questions ?? cards.length, cards });
      setView("quiz");
    } catch (e: any) {
      setError(e?.message ?? "quiz failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function fetchSummary() {
    if (!docHash) return alert("Index a document first.");
    scrollToSection("text-box");
    setIsLoading(true);
    setError("");
    setView("none");
    try {
      const r = await axios.post("/api/rag/summary", { doc_hash: docHash });
      setSummary(r.data?.summary ?? "");
      setView("summary");
    } catch (e: any) {
      setError(e?.message ?? "summary failed");
    } finally {
      setIsLoading(false);
    }
  }

  function openChat() {
    if (!docHash) return alert("Index a document first.");
    scrollToSection("text-box");
    setView("chat");
  }

  function openGraph() {
    if (!docHash) return alert("Index a document first.");
    scrollToSection("text-box");
    setView("graph");
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
              Upload document (.pdf, .txt, .md, .docx)
            </div>
            <div className="mt-2 w-full">
              <input
                onChange={handleFileChange}
                type="file"
                className="mt-2 block w-full text-xs sm:text-sm text-black file:hover:scale-105 file:mr-2 sm:file:mr-4 file:py-1.5 sm:file:py-2 file:px-2 sm:file:px-4 file:rounded-full file:border-0 file:text-xs sm:file:text-sm file:font-semibold file:bg-black file:text-white transition-all duration-200 file:animate-bounce"
                accept=".pdf,.txt,.md,.doc,.docx"
              />
            </div>
            {selectedFile && (
              <div className="mt-3 text-xs text-gray-700">
                {selectedFile.name} — <span className="font-mono">{indexProgress || "ready"}</span>
              </div>
            )}
          </div>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8 w-full max-w-6xl mx-auto">
          <Homecard
            heading="Quiz"
            mainText="Generate a multiple-choice quiz from the document."
            ButtonText="Generate Quiz"
            onClick={fetchQuiz}
          />
          <Homecard
            heading="Summary"
            mainText="Concise summary of the document's key ideas."
            ButtonText="Summarize"
            onClick={fetchSummary}
          />
          <Homecard
            heading="Custom Q&A"
            mainText="Ask anything — streamed answers with citations."
            ButtonText="Chat with AI"
            onClick={openChat}
          />
          <Homecard
            heading="Knowledge Graph"
            mainText="Explore entities and relationships extracted from the document."
            ButtonText="View Graph"
            onClick={openGraph}
          />
        </div>
      </div>

      <div className="opacity-50 text-center text-xs sm:text-sm px-4 mb-4">
        Hybrid GraphRAG — answers come from vector + BM25 + knowledge graph fused via RRF.
      </div>

      {/* Results panel */}
      <div
        className="w-full max-w-6xl border-white border-2 flex justify-center mt-4 sm:mt-6 md:mt-10 rounded-xl min-h-[300px] sm:min-h-[400px] bg-gray-100/80 shadow-lg mx-2 sm:mx-4 lg:mx-auto"
        id="text-box"
      >
        {isLoading && (
          <div className="flex justify-center items-center p-4">
            <span className="text-black flex flex-col sm:flex-row text-base sm:text-xl items-center text-center">
              <span className="mb-2 sm:mb-0 text-lg text-black">Loading …</span>
              <div className=" text-x2l bg-transparent py-10 animate-bounce"> 📚 📝 📘 📙 📑 💻 🖥️ </div>
            </span>
          </div>
        )}

        {!isLoading && error && (
          <div className="bg-red-50 p-4 m-2 sm:m-4 rounded-xl shadow-inner border border-red-200 w-full">
            <h3 className="text-base sm:text-lg font-semibold mb-2 text-red-900">Error</h3>
            <div className="text-red-700 text-sm sm:text-base break-words">{error}</div>
          </div>
        )}

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

        {!isLoading && view === "summary" && summary && (
          <div className="bg-blue-50 p-2 sm:p-4 m-2 sm:m-4 rounded-xl shadow-inner max-h-full overflow-y-auto border border-blue-200 w-full">
            <h3 className="text-base sm:text-lg font-semibold mb-2 text-blue-900">Document Summary</h3>
            <div className="whitespace-pre-wrap prose max-w-none p-2 text-gray-900 text-sm sm:text-base">
              <Markdown>{summary}</Markdown>
            </div>
          </div>
        )}

        {!isLoading && view === "chat" && docHash && (
          <div className="w-full p-2 sm:p-4 bg-zinc-950 rounded">
            <ChatStream docHash={docHash} onCiteClick={(cid) => setHighlightChunk(String(cid))} />
            {highlightChunk && (
              <div className="mt-2 text-xs text-purple-300">Citation clicked → chunk {highlightChunk}</div>
            )}
          </div>
        )}

        {!isLoading && view === "graph" && docHash && (
          <div className="w-full p-2 sm:p-4">
            <GraphView docHash={docHash} />
          </div>
        )}
      </div>
    </div>
  );
}
