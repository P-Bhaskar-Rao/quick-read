// components/FileStatus.jsx
import React from 'react';
import { FileText, X } from 'lucide-react';

const FileStatus = ({ fileInfo, onRemove }) => {
  if (!fileInfo) return null;

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="w-5 h-5 text-blue-600" />
          <div>
            <p className="font-medium text-blue-900">{fileInfo.file_name}</p>
            <p className="text-sm text-blue-700">
              {fileInfo.content_type === 'pdf' ? fileInfo.file_size : 'Web Content'}
            </p>
          </div>
        </div>
        <button
          onClick={onRemove}
          className="p-2 text-blue-600 hover:text-blue-800 transition-colors hover:cursor-pointer"
          title="Remove file"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default FileStatus;