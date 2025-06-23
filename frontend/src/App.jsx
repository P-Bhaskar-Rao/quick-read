// QuickReadWizard.jsx
import React, { useState, useEffect } from 'react';
import { apiService } from './services/apiService';
import DocumentInput from './components/DocumentInput';
import Summary from './components/Summary';
import AskQuestions from './components/AskQuestions';

import ErrorMessage from './components/ErrorMessage';

const App = () => {
  const [fileInfo, setFileInfo] = useState(null);
  const [summary, setSummary] = useState('');
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [isAskingQuestion, setIsAskingQuestion] = useState(false);
  const [error, setError] = useState('');

  // Load initial status
  useEffect(() => {
    const loadStatus = async () => {
      try {
        const status = await apiService.getStatus();
        setFileInfo(status.file_info);
        setSummary(status.summary || '');
      } catch (error) {
        console.error('Failed to load status:', error);
      }
    };
    
    loadStatus();
  }, []);

  const handleFileUpload = async (file) => {
    setIsUploadingFile(true);
    setError('');
    try {
      const response = await apiService.uploadFile(file);
      setFileInfo(response.file_info);
      setSummary('');
    } catch (error) {
      setError(error.message);
    } finally {
      setIsUploadingFile(false);
    }
  };

  const handleUrlAnalysis = async (url) => {
    setIsUploadingFile(true);
    setError('');
    try {
      const response = await apiService.analyzeUrl(url);
      setFileInfo(response.file_info);
      setSummary('');
    } catch (error) {
      setError(error.message);
    } finally {
      setIsUploadingFile(false);
    }
  };

  const handleSummarize = async () => {
    setIsSummarizing(true);
    setError('');
    try {
      const response = await apiService.summarize();
      setSummary(response.summary);
    } catch (error) {
      setError(error.message);
      setSummary('');
    } finally {
      setIsSummarizing(false);
    }
  };

  const handleAskQuestion = async (question) => {
    setIsAskingQuestion(true);
    try {
      const response = await apiService.askQuestion(question);
      return response;
    } catch (error) {
      throw error;
    } finally {
      setIsAskingQuestion(false);
    }
  };

  const handleDownloadSummary = async () => {
    try {
      const blob = await apiService.downloadSummary();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `summary_${fileInfo?.file_name || 'document'}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      setError(error.message);
    }
  };

  const handleClearSummary = () => {
    setSummary('');
  };

  const handleRemoveFile = async () => {
    try {
      await apiService.removeFile();
      setFileInfo(null);
      setSummary('');
    } catch (error) {
      setError(error.message);
    }
  };

  const handleClearError = () => {
    setError('');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header Section - Fixed height with proper spacing */}
      <div className="px-3 sm:px-4 lg:px-6 pt-4 sm:pt-6 pb-3 sm:pb-4">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900 mb-1 sm:mb-2">
            Quick Read Wizard
          </h1>
          <p className="text-xs sm:text-sm lg:text-base text-gray-600 px-4">
            Upload PDFs or analyze web content with AI-powered summarization and intelligent Q&A
          </p>
        </div>
        
        {/* Error Message */}
        <div className="mt-3 sm:mt-4">
          <ErrorMessage message={error} onClose={handleClearError} />
        </div>
      </div>

      {/* Main Content - Scrollable container */}
      <div className="px-3 sm:px-4 lg:px-6 pb-4 sm:pb-6">
        <div className="max-w-7xl mx-auto">
          
          {/* Mobile Layout - Stacked Vertically with natural scrolling */}
          <div className="lg:hidden space-y-4">
            {/* Mobile: Document Input */}
            <div className="min-h-[200px]">
              <DocumentInput
                onFileUploaded={handleFileUpload}
                onUrlAnalyzed={handleUrlAnalysis}
                fileInfo={fileInfo}
                onRemoveFile={handleRemoveFile}
                isLoading={isUploadingFile}
              />
            </div>
            
            {/* Mobile: Summary */}
            <div className="min-h-[300px]">
              <Summary
                fileInfo={fileInfo}
                summary={summary}
                onSummarize={handleSummarize}
                onDownload={handleDownloadSummary}
                onClear={handleClearSummary}
                isLoading={isUploadingFile}
                isSummarizing={isSummarizing}
              />
            </div>
            
            {/* Mobile: Ask Questions */}
            <div className="min-h-[200px]">
              <AskQuestions
                fileInfo={fileInfo}
                onAskQuestion={handleAskQuestion}
                isLoading={isUploadingFile}
                isAskingQuestion={isAskingQuestion}
              />
            </div>
          </div>

          {/* Desktop Layout - Two Columns with fixed viewport height */}
          <div className="hidden lg:grid lg:grid-cols-2 gap-6 h-[calc(100vh-12rem)]">
            {/* Left Column - Independent scrolling container */}
            <div className="h-full overflow-hidden">
              <div className="h-full flex flex-col gap-6 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-400 scrollbar-track-gray-100 hover:scrollbar-thumb-gray-500">
                {/* Document Input - Flexible height */}
                <div className="flex-shrink-0">
                  <DocumentInput
                    onFileUploaded={handleFileUpload}
                    onUrlAnalyzed={handleUrlAnalysis}
                    fileInfo={fileInfo}
                    onRemoveFile={handleRemoveFile}
                    isLoading={isUploadingFile}
                  />
                </div>
                
                {/* Ask Questions - Flexible height */}
                <div className="flex-shrink-0">
                  <AskQuestions
                    fileInfo={fileInfo}
                    onAskQuestion={handleAskQuestion}
                    isLoading={isUploadingFile}
                    isAskingQuestion={isAskingQuestion}
                  />
                </div>
              </div>
            </div>

            {/* Right Column - Independent scrolling container */}
            <div className="h-full overflow-hidden">
              <div className="h-full">
                <Summary
                  fileInfo={fileInfo}
                  summary={summary}
                  onSummarize={handleSummarize}
                  onDownload={handleDownloadSummary}
                  onClear={handleClearSummary}
                  isLoading={isUploadingFile}
                  isSummarizing={isSummarizing}
                />
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default App;