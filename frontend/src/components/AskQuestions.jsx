// components/AskQuestions.jsx
import React, { useState, useEffect, useCallback, useMemo } from "react";
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

  
  // 🔧 FIXED: Move defaultQuestions to useMemo to prevent recreation
  const defaultQuestions = useMemo(() => [
    "What are the main points of this document?",
    "Can you explain the key findings?",
    "What are the conclusions?",
    "Are there any recommendations mentioned?",
  ], []);

  // 🔧 FIXED: Removed defaultQuestions from dependency array
  const generateSuggestedQuestions = useCallback(async (retryAttempt = 0) => {
    if (!fileInfo || isLoadingQuestions) return;

    // Add small delay to ensure session is established
    if (retryAttempt === 0) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    setIsLoadingQuestions(true);
    try {
      console.log('Generating questions, attempt:', retryAttempt + 1);
      const data = await apiService.getSuggestedQuestions();

      if (data.success) {
        setSuggestedQuestions(data.questions || []);
        setQuestionsGenerated(true);
      } else {
        console.error("Failed to generate questions:", data.error || "Unknown error");
        
        // Retry logic for session issues
        if ((data.error === "No file uploaded" || data.error?.includes("No file uploaded")) && retryAttempt < 2) {
          console.log('Retrying question generation due to session issue...');
          setTimeout(() => {
            generateSuggestedQuestions(retryAttempt + 1);
          }, 2000 * (retryAttempt + 1)); // Exponential backoff
          return;
        }
        
        // Fallback to default questions
        setSuggestedQuestions(defaultQuestions);
        setQuestionsGenerated(true);
      }
    } catch (error) {
      console.error("Error generating questions:", error);
      
      // Retry on network errors
      if (error.message?.includes("No file uploaded") && retryAttempt < 2) {
        console.log('Retrying question generation due to error...');
        setTimeout(() => {
          generateSuggestedQuestions(retryAttempt + 1);
        }, 2000 * (retryAttempt + 1));
        return;
      }
      
      // Fallback to default questions
      setSuggestedQuestions(defaultQuestions);
      setQuestionsGenerated(true);
    } finally {
      setIsLoadingQuestions(false);
    }
  }, [fileInfo, isLoadingQuestions, defaultQuestions]);

  // 🔧 FIXED: Better useEffect with proper cleanup and dependency management
  useEffect(() => {
    let timeoutId;
    
    if (!fileInfo) {
      setQuestion("");
      setAnswer("");
      setIsAsking(false);
      setSuggestedQuestions([]);
      setQuestionsGenerated(false);
    } else if (fileInfo && !questionsGenerated && !isLoadingQuestions) {
      // Add delay before generating questions
      timeoutId = setTimeout(() => {
        generateSuggestedQuestions();
      }, 500);
    }
    
    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [fileInfo, questionsGenerated, isLoadingQuestions]); // 🔧 FIXED: Removed generateSuggestedQuestions from deps

  // 🔧 FIXED: Add proper error handling and validation
  const handleSubmit = async (retryAttempt = 0) => {
    if (!question.trim() || !fileInfo || isAsking) return;

    setIsAsking(true);
    try {
      // 🔧 FIXED: Add validation for onAskQuestion
      if (!onAskQuestion || typeof onAskQuestion !== 'function') {
        throw new Error('Question handler not available');
      }
      
      const response = await onAskQuestion(question);
      
      // 🔧 FIXED: Add response validation
      if (response && response.answer) {
        setAnswer(response.answer);
      } else {
        setAnswer('No answer received');
      }
    } catch (error) {
      console.error("Error asking question:", error);
      
      // Retry logic for session issues
      if (error.message?.includes("No file uploaded") && retryAttempt < 1) {
        console.log('Retrying question submission...');
        setTimeout(() => {
          handleSubmit(retryAttempt + 1);
        }, 1000);
        return;
      }
      
      setAnswer(`Error: ${error.message || 'Failed to get answer'}`);
    } finally {
      setIsAsking(false);
    }
  };

  const handleSuggestedQuestion = async (suggestedQ, retryAttempt = 0) => {
    if (!suggestedQ || !fileInfo) return;
    
    setQuestion(suggestedQ);
    setIsAsking(true);
    
    try {
      // 🔧 FIXED: Add validation for onAskQuestion
      if (!onAskQuestion || typeof onAskQuestion !== 'function') {
        throw new Error('Question handler not available');
      }
      
      const response = await onAskQuestion(suggestedQ);
      
      // 🔧 FIXED: Add response validation
      if (response && response.answer) {
        setAnswer(response.answer);
      } else {
        setAnswer('No answer received');
      }
    } catch (error) {
      console.error("Error with suggested question:", error);
      
      // Retry logic for session issues
      if (error.message?.includes("No file uploaded") && retryAttempt < 1) {
        console.log('Retrying suggested question...');
        setTimeout(() => {
          handleSuggestedQuestion(suggestedQ, retryAttempt + 1);
        }, 1000);
        return;
      }
      
      setAnswer(`Error: ${error.message || 'Failed to get answer'}`);
    } finally {
      setIsAsking(false);
    }
  };

  const clearAnswer = () => {
    setAnswer("");
  };

  const refreshQuestions = () => {
    if (isLoadingQuestions) return; // 🔧 FIXED: Prevent multiple refreshes
    
    setIsRotating(true);
    setQuestionsGenerated(false);
    setSuggestedQuestions([]);
    generateSuggestedQuestions();
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
          onClick={() => handleSubmit()}
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
                  No suggested questions available. Try refreshing.
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