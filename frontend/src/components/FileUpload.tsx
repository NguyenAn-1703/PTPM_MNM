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
    'image/jpg',
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
    if (files.length > 0) handleFile(files[0]);
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) handleFile(files[0]);
  };

  const handleFile = async (file: File) => {
    if (!ALLOWED_TYPES.includes(file.type) && !file.name.match(/\.(pdf|docx?|png|jpe?g)$/i)) {
      alert('Chỉ hỗ trợ file PDF, Word, PNG, JPG');
      return;
    }
    await onUpload(file);
  };

  return (
    <div className="relative group">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative w-full h-48 rounded-2xl border-2 border-dashed transition-all duration-300
          flex flex-col items-center justify-center cursor-pointer overflow-hidden
          ${isDragging
            ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-500/10'
            : 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-slate-800/30 hover:bg-gray-100 dark:hover:bg-slate-800/50 hover:border-indigo-400 dark:hover:border-indigo-500'
          }
          ${isUploading ? 'pointer-events-none opacity-70' : ''}
        `}
      >
        <input
          type="file"
          onChange={handleFileInput}
          accept=".pdf,.docx,.doc,.png,.jpg,.jpeg"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={isUploading}
          title="Upload files"
        />

        {isUploading ? (
          <>
            <div className="mb-3 p-4 rounded-full bg-indigo-500/10 dark:bg-indigo-500/20">
              <div className="w-8 h-8 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin" style={{ borderWidth: '3px' }} />
            </div>
            <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Đang xử lý tài liệu...</p>
          </>
        ) : (
          <>
            <div className="mb-3 p-4 rounded-full bg-indigo-500/10 dark:bg-indigo-500/20 text-indigo-500 dark:text-indigo-400 group-hover:scale-110 transition-transform duration-300">
              <span className="material-icons-round" style={{ fontSize: '30px' }}>cloud_upload</span>
            </div>
            <h3 className="text-base font-medium text-gray-700 dark:text-gray-200">Kéo thả file vào đây</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              hoặc <span className="text-indigo-500 hover:underline font-medium cursor-pointer">nhấn để chọn file</span>
            </p>
            <div className="flex gap-2 mt-4">
              {['PDF', 'DOCX', 'PNG', 'JPG'].map((type) => (
                <span
                  key={type}
                  className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 bg-gray-200 dark:bg-slate-700 rounded"
                >
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
