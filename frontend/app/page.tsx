import { Button } from "./components/Button"

import Link from 'next/link'
export default function Home() {

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold">DocuMind AI</h1>
          <div className="space-x-4">
            <Link href="/signin"><Button variant="outline" >Sign In</Button></Link>
            <Link href="/signup"><Button variant="primary">Sign Up</Button></Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-16">
        {/* Hero Section */}
        <div className="text-center max-w-4xl mx-auto mb-16">
          <h2 className="text-5xl md:text-6xl font-bold mb-6 leading-tight bg-gradient-to-r from-purple-600 via-pink-500 to-pink-400 text-transparent bg-clip-text">
            Transform Your Documents with{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400">
              AI Intelligence
            </span>
          </h2>
          <p className="text-xl md:text-2xl text-gray-300 mb-8 leading-relaxed">
            Upload your PDFs and notes, then let our AI create instant summaries, generate quizzes, or provide custom
            answers to any question about your documents.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/signup"><Button variant="primary" size="lg">
              Let's Get Started 
            </Button></Link>
            <Link href="/signin"><Button variant="outline" size="lg">
              Sign In
            </Button></Link>
          </div>
        </div>

        {/* Features Section */}
        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto mb-16">
          <div className="text-center p-6 border-white border-1 rounded-md">
            <h3 className="text-2xl font-semibold mb-4">Smart Summaries</h3>
            <p className="text-gray-400 text-lg">
              Get concise, intelligent summaries of your lengthy documents in seconds. Extract key insights without
              reading through pages of content.
            </p>
          </div>
          <div className="text-center p-6  border-white border-1 rounded-md">
            <h3 className="text-2xl font-semibold mb-4">Interactive Quizzes</h3>
            <p className="text-gray-400 text-lg">
              Transform your study materials into engaging quizzes. Test your knowledge and reinforce learning with
              AI-generated questions.
            </p>
          </div>
          <div className="text-center p-6  border-white border-1 rounded-md">
            <h3 className="text-2xl font-semibold mb-4">Custom Q&A</h3>
            <p className="text-gray-400 text-lg">
              Ask any question about your documents and get precise, contextual answers. Your personal AI research
              assistant.
            </p>
          </div>
        </div>

        {/* How It Works */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h3 className="text-3xl font-bold mb-8">How It Works</h3>
          <div className="space-y-6 text-left">
            <div className="flex items-start space-x-4">
              <div className="bg-white text-black rounded-full w-8 h-8 flex items-center justify-center font-bold flex-shrink-0 mt-1">
                1
              </div>
              <div>
                <h4 className="text-xl font-semibold mb-2">Upload Your Documents</h4>
                <p className="text-gray-400">
                  Simply drag and drop your PDFs, notes, or documents into our secure platform.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <div className="bg-white text-black rounded-full w-8 h-8 flex items-center justify-center font-bold flex-shrink-0 mt-1">
                2
              </div>
              <div>
                <h4 className="text-xl font-semibold mb-2">Choose Your Tool</h4>
                <p className="text-gray-400">
                  Select whether you want summaries, quizzes, or custom Q&A for your documents.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <div className="bg-white text-black rounded-full w-8 h-8 flex items-center justify-center font-bold flex-shrink-0 mt-1">
                3
              </div>
              <div>
                <h4 className="text-xl font-semibold mb-2">Get Instant Results</h4>
                <p className="text-gray-400">
                  Our AI processes your content and delivers exactly what you need in moments.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="text-center max-w-2xl mx-auto">
          <h3 className="text-3xl font-bold mb-4">Ready to Supercharge Your Learning?</h3>
          <p className="text-gray-400 text-lg mb-8">
            unlock the power of your documents and 10x your learning in half the time .
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="container mx-auto px-4 py-8 border-t border-gray-800">
        <div className="text-center text-gray-500">
          <p>&copy; 2024 DocuMind AI. </p>
        </div>
      </footer>
    </div>
  )
}
