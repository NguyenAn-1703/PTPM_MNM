import React, { useState, useCallback } from 'react';

interface FileUploadProps {
  onUpload: (file: File) => Promise<void>;
  isUploading: boolean;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onUpload, isUploading }) => {
  const [isDragging, setIsDragging] = useState(false);
  
  const ALLOWED_TYPES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'image/png',
    'image/jpeg',
    'image/jpg'
  ];

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFile = async (file: File) => {
    if (!ALLOWED_TYPES.includes(file.type) && !file.name.match(/\.(pdf|docx?|png|jpe?g)$/i)) {
      alert('Chỉ hỗ trợ file PDF, Word, PNG, JPG');
      return;
    }
    await onUpload(file);
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`
        relative p-8 rounded-2xl border-2 border-dashed transition-all duration-300
        ${isDragging 
          ? 'border-indigo-500 bg-indigo-500/10' 
          : 'border-slate-600 hover:border-slate-500 bg-slate-800/30'
        }
        ${isUploading ? 'pointer-events-none opacity-60' : 'cursor-pointer'}
      `}
    >
      <input
        type="file"
        onChange={handleFileInput}
        accept=".pdf,.docx,.doc,.png,.jpg,.jpeg"
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        disabled={isUploading}
      />
      
      <div className="flex flex-col items-center gap-4 text-center">
        {isUploading ? (
          <>
            <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-slate-300">Đang xử lý tài liệu...</p>
          </>
        ) : (
          <>
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center">
              <svg className="w-8 h-8 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <p className="text-white font-medium mb-1">
                Kéo thả file vào đây
              </p>
              <p className="text-sm text-slate-400">
                hoặc <span className="text-indigo-400">nhấn để chọn file</span>
              </p>
            </div>
            <div className="flex gap-2 flex-wrap justify-center">
              {['PDF', 'DOCX', 'PNG', 'JPG'].map(type => (
                <span key={type} className="px-2 py-1 text-xs bg-slate-700/50 text-slate-300 rounded">
                  {type}
                </span>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
