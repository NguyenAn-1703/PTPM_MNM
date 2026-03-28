import React, { useState, useCallback } from 'react';

interface FileUploadProps {
  onUpload: (file: File) => Promise<void>;
  isUploading: boolean;
  compact?: boolean;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onUpload, isUploading, compact = false }) => {
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
    e.target.value = '';
  };

  const handleFile = async (file: File) => {
    if (!ALLOWED_TYPES.includes(file.type) && !file.name.match(/\.(pdf|docx?|png|jpe?g)$/i)) {
      alert('Chỉ hỗ trợ file PDF, Word, PNG, JPG');
      return;
    }
    await onUpload(file);
  };

  // Compact mode: small button only
  if (compact) {
    return (
      <label className={`relative inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition-all duration-200
        border-sky-300/70 bg-white text-sky-700 shadow-sm hover:-translate-y-0.5 hover:bg-sky-50
        dark:border-sky-500/40 dark:bg-slate-900 dark:text-sky-300 dark:hover:bg-slate-800
        ${isUploading ? 'opacity-60 pointer-events-none' : ''}
      `}>
        <input
          type="file"
          onChange={handleFileInput}
          accept=".pdf,.docx,.doc,.png,.jpg,.jpeg"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={isUploading}
          title="Upload thêm file"
        />
        {isUploading ? (
          <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-sky-500 border-t-transparent" />
        ) : (
          <span className="material-icons-round" style={{ fontSize: '14px' }}>add</span>
        )}
        <span>Thêm tài liệu</span>
      </label>
    );
  }

  // Full upload zone
  return (
    <div className="group relative">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative flex h-64 w-full cursor-pointer flex-col items-center justify-center overflow-hidden rounded-3xl border-2 border-dashed transition-all duration-300
          before:absolute before:inset-0 before:bg-[radial-gradient(circle_at_30%_20%,rgba(14,165,233,0.14),transparent_50%),radial-gradient(circle_at_80%_70%,rgba(34,197,94,0.16),transparent_55%)] before:opacity-0 before:transition-opacity before:duration-300
          flex flex-col items-center justify-center cursor-pointer overflow-hidden
          ${isDragging
            ? 'border-sky-500 bg-sky-50/90 dark:bg-sky-500/10 before:opacity-100'
            : 'border-slate-300/80 bg-white/80 hover:border-sky-400 hover:bg-white dark:border-slate-600/70 dark:bg-slate-900/60 dark:hover:border-sky-500 dark:hover:bg-slate-900/85 group-hover:before:opacity-100'
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
            <div className="mb-4 rounded-full border border-sky-200 bg-sky-50 p-4 dark:border-sky-500/30 dark:bg-sky-500/10">
              <div className="h-8 w-8 animate-spin rounded-full border-t-transparent" style={{ borderWidth: '3px', borderStyle: 'solid', borderColor: 'rgb(14 165 233)' }} />
            </div>
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">Đang xử lý tài liệu...</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Hệ thống đang tách văn bản và tạo embeddings.</p>
          </>
        ) : (
          <>
            <div className="mb-4 rounded-2xl border border-sky-200/80 bg-white p-4 text-sky-600 shadow-lg shadow-sky-500/10 transition-transform duration-300 group-hover:scale-105 dark:border-sky-500/30 dark:bg-slate-900 dark:text-sky-300">
              <span className="material-icons-round" style={{ fontSize: '30px' }}>upload_file</span>
            </div>
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">Kéo thả tài liệu vào đây</h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              hoặc <span className="font-semibold text-sky-600 dark:text-sky-300">nhấn để chọn file từ máy</span>
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {['PDF', 'DOCX', 'PNG', 'JPG'].map((type) => (
                <span
                  key={type}
                  className="rounded-full border border-slate-300/80 bg-white px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300"
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
