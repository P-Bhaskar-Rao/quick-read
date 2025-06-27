// components/FileStatus.jsx
import React from 'react';
import { FileText, X, Loader2 } from 'lucide-react';

const FileStatus = ({ fileInfo, onRemove, isRemoving }) => {
  if (!fileInfo) return null;

  // Function to truncate long URLs or file names
  const truncateText = (text, maxLength = 60) => {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  const isTextTruncated = fileInfo.file_name && fileInfo.file_name.length > 60;

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          {/* Fixed size icon container */}
          <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center mt-0.5">
            <FileText className="w-6 h-6 text-blue-600" />
          </div>
          {/* Text content with proper constraints */}
          <div className="min-w-0 flex-1 overflow-hidden">
            <p 
              className="font-medium text-blue-900 break-words overflow-wrap-anywhere leading-tight"
              title={isTextTruncated ? fileInfo.file_name : undefined}
            >
              {truncateText(fileInfo.file_name)}
            </p>
            <p className="text-sm text-blue-700 mt-1">
              {fileInfo.content_type === 'pdf' ? fileInfo.file_size : 'Web Content'}
            </p>
          </div>
        </div>
        {/* Fixed size button container */}
        <div className="flex-shrink-0 w-9 h-9 flex items-center justify-center">
          <button
            onClick={onRemove}
            disabled={isRemoving}
            className={`p-2 transition-colors rounded-md ${
              isRemoving 
                ? 'text-gray-400 cursor-not-allowed' 
                : 'text-blue-600 hover:text-blue-800 hover:cursor-pointer hover:bg-blue-100'
            }`}
            title={isRemoving ? "Removing file..." : "Remove file"}
          >
            {isRemoving ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <X className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FileStatus;