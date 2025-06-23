// components/DocumentInput.jsx
import React, { useState } from 'react';
import { Upload, Link, FileText, X, File, Loader2 } from 'lucide-react';
import FileStatus from './FileStatus';

const DocumentInput = ({ onFileUploaded, onUrlAnalyzed, fileInfo, onRemoveFile, isLoading }) => {
  const [activeTab, setActiveTab] = useState('upload');
  const [dragOver, setDragOver] = useState(false);
  const [url, setUrl] = useState('');

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleFileUpload = async (file) => {
    if (file.type !== 'application/pdf') {
      alert('Please upload a PDF file');
      return;
    }
    
    try {
      await onFileUploaded(file);
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };

  const handleUrlSubmit = async () => {
    if (!url.trim()) return;
    
    try {
      await onUrlAnalyzed(url);
      setUrl('');
    } catch (error) {
      console.error('URL analysis failed:', error);
    }
  };



  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center gap-2 mb-4">
        <FileText className="w-5 h-5 text-blue-600" />
        <h2 className="text-lg font-semibold text-gray-800">Document Input</h2>
      </div>
      <p className="text-sm text-gray-600 mb-4">Upload a PDF file or provide a URL to analyze</p>
      
      {/* File Status Display */}
      <FileStatus fileInfo={fileInfo} onRemove={onRemoveFile}/>
      {/* {fileInfo && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <File className="w-4 h-4 text-green-600" />
              <div>
                <p className="text-sm font-medium text-green-800">
                  {fileInfo.file_name || fileInfo.url || 'Document loaded'}
                </p>
                {fileInfo.file_size && !isNaN(fileInfo.file_size) && (
                  <p className="text-xs text-green-600">
                    {(fileInfo.file_size)} MB
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={onRemoveFile}
              className="p-1 text-green-600 hover:text-green-800 transition-colors"
              title="Remove file"
              disabled={isLoading}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )} */}
      
      {/* Only show upload/URL interface when no file is loaded */}
      {!fileInfo && (
        <div className="relative">
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setActiveTab('upload')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors hover:cursor-pointer ${
                activeTab === 'upload'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
              disabled={isLoading}
            >
              <Upload className="w-4 h-4 inline mr-2" />
              Upload PDF
            </button>
            <button
              onClick={() => setActiveTab('url')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors hover:cursor-pointer ${
                activeTab === 'url'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
              disabled={isLoading}
            >
              <Link className="w-4 h-4 inline mr-2" />
              From URL
            </button>
          </div>

          {activeTab === 'upload' && (
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                dragOver
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-400'
              } ${isLoading ? 'pointer-events-none opacity-50' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 mb-2">Drop your PDF file here</p>
              <p className="text-sm text-gray-500 mb-4">or click to browse</p>
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => e.target.files[0] && handleFileUpload(e.target.files[0])}
                className="hidden"
                id="file-upload"
                disabled={isLoading}
              />
              <label
                htmlFor="file-upload"
                className={`px-4 py-2 rounded-md transition-colors cursor-pointer inline-flex items-center gap-2 ${
                  isLoading
                    ? 'bg-blue-600 text-white cursor-not-allowed'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Extracting PDF...
                  </>
                ) : (
                  'Choose PDF File'
                )}
              </label>
            </div>
          )}

          {activeTab === 'url' && (
            <div className="space-y-4">
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Enter URL to analyze..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isLoading}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && url.trim() && !isLoading) {
                    handleUrlSubmit();
                  }
                }}
              />
              <button
                onClick={handleUrlSubmit}
                disabled={!url.trim() || isLoading}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed hover:cursor-pointer flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Analyzing URL...
                  </>
                ) : (
                  <>
                    <Link className="w-4 h-4" />
                    Analyze URL
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DocumentInput;