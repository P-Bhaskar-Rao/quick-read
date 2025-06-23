import React, { useState } from 'react';
import { FileText, Download, X, RotateCcw, Copy, Loader2, ChevronDown } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const Summary = ({ fileInfo, summary, onSummarize, onDownload, onClear, isSummarizing }) => {
  const [copySuccess, setCopySuccess] = useState(false);
  const [showCopyOptions, setShowCopyOptions] = useState(false);

  // Function to convert markdown to plain text
  const markdownToPlainText = (markdown) => {
    return markdown
      // Remove headers (## Header -> Header)
      .replace(/^#{1,6}\s+/gm, '')
      // Remove bold/italic (**text** -> text, *text* -> text)
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1')
      // Remove links [text](url) -> text
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      // Remove inline code `code` -> code
      .replace(/`([^`]+)`/g, '$1')
      // Remove code blocks
      .replace(/```[\s\S]*?```/g, '')
      // Convert tables to readable format
      .replace(/\|([^|\n]+)\|/g, (match, content) => {
        return content.trim().replace(/\s*\|\s*/g, ' | ');
      })
      // Remove table separators
      .replace(/^\s*\|?\s*[-:]+\s*\|?\s*$/gm, '')
      // Remove list markers (- item -> item, * item -> item)
      .replace(/^\s*[-*+]\s+/gm, '• ')
      // Remove numbered list markers (1. item -> item)
      .replace(/^\s*\d+\.\s+/gm, '• ')
      // Clean up multiple newlines
      .replace(/\n{3,}/g, '\n\n')
      // Remove leading/trailing whitespace
      .trim();
  };

  // Function to convert markdown to formatted text (preserving some structure)
  const markdownToFormattedText = (markdown) => {
    return markdown
      // Convert headers to uppercase
      .replace(/^#{1,2}\s+(.+)$/gm, (match, title) => title.toUpperCase())
      .replace(/^#{3,6}\s+(.+)$/gm, '$1')
      // Remove bold/italic markers but keep the text
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1')
      // Convert links to "text (url)" format
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1 ($2)')
      // Remove inline code markers
      .replace(/`([^`]+)`/g, '$1')
      // Remove code blocks
      .replace(/```[\s\S]*?```/g, '')
      // Convert tables to better formatted text
      .replace(/\|([^|\n]+)\|/g, (match, content) => {
        return content.trim().replace(/\s*\|\s*/g, ' | ');
      })
      // Remove table separators
      .replace(/^\s*\|?\s*[-:]+\s*\|?\s*$/gm, '')
      // Convert list markers
      .replace(/^\s*[-*+]\s+/gm, '• ')
      .replace(/^\s*\d+\.\s+/gm, '• ')
      // Clean up
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  };

  const handleCopy = async (format = 'markdown') => {
    try {
      let textToCopy;
      
      switch (format) {
        case 'plain':
          textToCopy = markdownToPlainText(summary);
          break;
        case 'formatted':
          textToCopy = markdownToFormattedText(summary);
          break;
        case 'markdown':
        default:
          textToCopy = summary;
          break;
      }
      
      await navigator.clipboard.writeText(textToCopy);
      setCopySuccess(format);
      setShowCopyOptions(false);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  // Custom components for markdown rendering
  const markdownComponents = {
    // Headings with proper styling
    h1: ({ children }) => (
      <h1 className="text-xl font-bold text-gray-900 mb-4 mt-6 first:mt-0 border-b border-gray-200 pb-2">
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-lg font-semibold text-gray-800 mb-3 mt-5 first:mt-0">
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-base font-medium text-gray-800 mb-2 mt-4 first:mt-0">
        {children}
      </h3>
    ),
    h4: ({ children }) => (
      <h4 className="text-sm font-medium text-gray-700 mb-2 mt-3 first:mt-0">
        {children}
      </h4>
    ),
    
    // Paragraphs with proper spacing
    p: ({ children }) => (
      <p className="text-sm text-gray-700 mb-3 leading-relaxed">
        {children}
      </p>
    ),
    
    // Lists with proper styling
    ul: ({ children }) => (
      <ul className="list-disc list-inside mb-3 space-y-1 text-sm text-gray-700 ml-2">
        {children}
      </ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal list-inside mb-3 space-y-1 text-sm text-gray-700 ml-2">
        {children}
      </ol>
    ),
    li: ({ children }) => (
      <li className="leading-relaxed">{children}</li>
    ),
    
    // Code blocks with background
    code: ({ inline, children, className }) => {
      if (inline) {
        return (
          <code className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-xs font-mono">
            {children}
          </code>
        );
      }
      return (
        <div className="mb-4">
          <pre className="bg-gray-100 rounded-lg p-3 overflow-x-auto">
            <code className="text-sm font-mono text-gray-800 whitespace-pre">
              {children}
            </code>
          </pre>
        </div>
      );
    },
    
    // Tables with styling
    table: ({ children }) => (
      <div className="mb-4 overflow-x-auto">
        <table className="min-w-full border border-gray-200 rounded-lg text-sm">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="bg-gray-50">{children}</thead>
    ),
    tbody: ({ children }) => (
      <tbody className="divide-y divide-gray-200">{children}</tbody>
    ),
    tr: ({ children }) => (
      <tr className="hover:bg-gray-50">{children}</tr>
    ),
    th: ({ children }) => (
      <th className="px-3 py-2 text-left font-medium text-gray-700 border-b border-gray-200">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="px-3 py-2 text-gray-700 border-b border-gray-200">
        {children}
      </td>
    ),
    
    // Blockquotes for important notes
    blockquote: ({ children }) => (
      <blockquote className="border-l-4 border-blue-500 pl-4 py-2 mb-4 bg-blue-50 text-gray-700 italic">
        {children}
      </blockquote>
    ),
    
    // Horizontal rules
    hr: () => (
      <hr className="my-6 border-gray-300" />
    ),
    
    // Strong and emphasis
    strong: ({ children }) => (
      <strong className="font-semibold text-gray-900">{children}</strong>
    ),
    em: ({ children }) => (
      <em className="italic text-gray-800">{children}</em>
    ),
    
    // Links with proper styling
    a: ({ href, children }) => (
      <a 
        href={href} 
        target="_blank" 
        rel="noopener noreferrer" 
        className="text-blue-600 hover:text-blue-800 underline"
      >
        {children}
      </a>
    )
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 h-full flex flex-col relative">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-600" />
          <h2 className="text-lg font-semibold text-gray-800">Summary</h2>
        </div>
        {summary && (
          <div className="flex gap-2">
            {/* Enhanced Copy Button with Dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowCopyOptions(!showCopyOptions)}
                disabled={isSummarizing}
                className="p-2 text-gray-600 hover:text-gray-800 transition-colors hover:cursor-pointer relative disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                title="Copy options"
              >
                <Copy className="w-4 h-4" />
                <ChevronDown className="w-3 h-3" />
                {copySuccess && (
                  <span className="absolute -top-5 -left-2 bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                    Copied as {copySuccess}!
                  </span>
                )}
              </button>
              
              {showCopyOptions && (
                <div className="absolute top-full right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 min-w-40">
                  <button
                    onClick={() => handleCopy('plain')}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 rounded-t-lg"
                  >
                    Copy as Plain Text
                  </button>
                  <button
                    onClick={() => handleCopy('formatted')}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50"
                  >
                    Copy as Formatted Text
                  </button>
                  <button
                    onClick={() => handleCopy('markdown')}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 rounded-b-lg"
                  >
                    Copy as Markdown
                  </button>
                </div>
              )}
            </div>
            
            <button
              onClick={onSummarize}
              disabled={isSummarizing}
              className="p-2 text-gray-600 hover:text-gray-800 transition-colors hover:cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              title={isSummarizing ? "Regenerating..." : "Regenerate summary"}
            >
              {isSummarizing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RotateCcw className="w-4 h-4" />
              )}
            </button>
            <button
              onClick={onDownload}
              disabled={isSummarizing}
              className="p-2 text-gray-600 hover:text-gray-800 transition-colors hover:cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              title="Download as PDF"
            >
              <Download className="w-4 h-4" />
            </button>
            <button
              onClick={onClear}
              disabled={isSummarizing}
              className="p-2 text-gray-600 hover:text-gray-800 transition-colors hover:cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              title="Clear summary"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
      
      {/* Click outside to close dropdown */}
      {showCopyOptions && (
        <div 
          className="fixed inset-0 z-10" 
          onClick={() => setShowCopyOptions(false)}
        />
      )}
      
      <p className="text-sm text-gray-600 mb-4">AI-generated summary of your content</p>

      <div className="flex-1 flex flex-col min-h-0">
        {!fileInfo ? (
          <div className="flex-1 flex flex-col justify-center items-center">
            <FileText className="w-12 h-12 text-blue-300 mb-4" />
            <p className="text-gray-500">No document uploaded</p>
            <p className="text-sm text-gray-400">Upload a document or provide a URL to get started</p>
          </div>
        ) : !summary ? (
          <div className="flex-1 flex flex-col justify-center items-center">
            <FileText className="w-12 h-12 text-blue-300 mb-4" />
            <p className="text-gray-500">No summary yet</p>
            <p className="text-sm text-gray-400 mb-4">Upload a document or provide a URL, then click "Generate Summary"</p>
            <button
              onClick={onSummarize}
              disabled={isSummarizing}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed hover:cursor-pointer flex items-center gap-2"
            >
              {isSummarizing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating Summary...
                </>
              ) : (
                'Generate Summary'
              )}
            </button>
          </div>
        ) : (
          <div className="flex-1 min-h-0">
            <div className="bg-gray-50 rounded-lg p-4 h-full overflow-y-auto scrollbar-thumb-gray-400 scrollbar-track-gray-100 scrollbar-thin hover:scrollbar-thumb-gray-500">
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={markdownComponents}
                >
                  {summary}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Summary;