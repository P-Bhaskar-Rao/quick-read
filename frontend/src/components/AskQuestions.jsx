// components/AskQuestions.jsx
import React, { useState, useEffect } from "react";
import {
  MessageCircle,
  AlertCircle,
  X,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import { apiService } from "../services/apiService";

const AskQuestions = ({ fileInfo, onAskQuestion, isLoading }) => {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(false);
  const [questionsGenerated, setQuestionsGenerated] = useState(false);
  const [isRotating, setIsRotating] = useState(false);
  // Clear question and answer when fileInfo changes (document removed/changed)
  useEffect(() => {
    if (!fileInfo) {
      setQuestion("");
      setAnswer("");
      setIsAsking(false);
      setSuggestedQuestions([]);
      setQuestionsGenerated(false);
    } else if (fileInfo && !questionsGenerated) {
      // Auto-generate questions when a new file is uploaded
      generateSuggestedQuestions();
    }
  }, [fileInfo]);

  const generateSuggestedQuestions = async () => {
    if (!fileInfo || isLoadingQuestions) return;

    setIsLoadingQuestions(true);
    try {
      const data = await apiService.getSuggestedQuestions();

      if (data.success) {
        setSuggestedQuestions(data.questions || []);
        setQuestionsGenerated(true);
      } else {
        console.error(
          "Failed to generate questions:",
          data.error || "Unknown error"
        );
        // Fallback to default questions
        setSuggestedQuestions([
          "What are the main points of this document?",
          "Can you explain the key findings?",
          "What are the conclusions?",
          "Are there any recommendations mentioned?",
        ]);
        setQuestionsGenerated(true);
      }
    } catch (error) {
      console.error("Error generating questions:", error);
      // Fallback to default questions
      setSuggestedQuestions([
        "What are the main points of this document?",
        "Can you explain the key findings?",
        "What are the conclusions?",
        "Are there any recommendations mentioned?",
      ]);
      setQuestionsGenerated(true);
    } finally {
      setIsLoadingQuestions(false);
    }
  };

  const handleSubmit = async () => {
    if (!question.trim() || !fileInfo) return;

    setIsAsking(true);
    try {
      const response = await onAskQuestion(question);
      setAnswer(response.answer);
    } catch (error) {
      setAnswer(`Error: ${error.message}`);
    } finally {
      setIsAsking(false);
    }
  };

  const handleSuggestedQuestion = async (suggestedQ) => {
    setQuestion(suggestedQ);
    if (!fileInfo) return;

    setIsAsking(true);
    try {
      const response = await onAskQuestion(suggestedQ);
      setAnswer(response.answer);
    } catch (error) {
      setAnswer(`Error: ${error.message}`);
    } finally {
      setIsAsking(false);
    }
  };

  const clearAnswer = () => {
    setAnswer("");
  };

  const refreshQuestions = () => {
    setIsRotating(true);
    setQuestionsGenerated(false);
    setSuggestedQuestions([]);
    generateSuggestedQuestions();
    // Reset rotation after animation
    setTimeout(() => setIsRotating(false), 500);
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center gap-2 mb-4">
        <MessageCircle className="w-5 h-5 text-blue-600" />
        <h2 className="text-lg font-semibold text-gray-800">Ask Questions</h2>
      </div>
      <p className="text-sm text-gray-600 mb-4">
        Get answers based on your uploaded content
      </p>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Ask a question about the content
          </label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Type your question here..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            rows={3}
            disabled={!fileInfo || isAsking || isLoading}
            onKeyPress={(e) => {
              if (
                e.key === "Enter" &&
                !e.shiftKey &&
                question.trim() &&
                fileInfo &&
                !isAsking &&
                !isLoading
              ) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />
        </div>

        {answer && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-700">Answer:</h3>
              <button
                onClick={clearAnswer}
                className="text-gray-400 hover:text-gray-600 transition-colors hover:cursor-pointer"
                title="Clear answer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 max-h-64 overflow-y-auto">
              <p className="text-sm text-gray-700 whitespace-pre-wrap">
                {answer}
              </p>
            </div>
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={!question.trim() || !fileInfo || isAsking || isLoading}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 hover:cursor-pointer"
        >
          <MessageCircle className="w-4 h-4" />
          {isAsking ? "Getting Answer..." : "Ask Question"}
        </button>
      </div>

      {!fileInfo && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-yellow-600" />
            <p className="text-sm text-yellow-800">
              Please upload a document first
            </p>
          </div>
        </div>
      )}

      {fileInfo && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-600" />
              <h3 className="text-sm font-medium text-gray-700">
                AI-Suggested Questions
              </h3>
            </div>
            {/* Always show refresh button when fileInfo exists */}
            <button
              onClick={refreshQuestions}
              disabled={isLoadingQuestions}
              className="text-gray-500 hover:text-gray-700 transition-colors p-1 rounded-md hover:bg-gray-100 disabled:opacity-50"
              title="Generate new questions"
            >
              <RefreshCw
                className={`w-4 h-4 transition-transform duration-500 ${
                  isLoadingQuestions
                    ? "animate-spin"
                    : isRotating
                    ? "rotate-180"
                    : "hover:rotate-180"
                }`}
              />
            </button>
          </div>

          {isLoadingQuestions ? (
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-10 bg-gray-100 rounded-md animate-pulse"
                ></div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {suggestedQuestions.map((q, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestedQuestion(q)}
                  disabled={!fileInfo || isAsking || isLoading}
                  className="block w-full text-left px-3 py-2 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-transparent hover:border-blue-200"
                >
                  {q}
                </button>
              ))}
              {suggestedQuestions.length === 0 && questionsGenerated && (
                <p className="text-sm text-gray-500 italic">
                  No suggested questions available.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AskQuestions;
