import { useState, useEffect, useCallback } from 'react';
import './styles/index';
import { api, type Context, type StatusResponse } from './services/api';
import { Sidebar, FileUpload, ChatInterface } from './components';

function App() {
  const [darkMode, setDarkMode] = useState(true);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [documentCount, setDocumentCount] = useState(0);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Sync dark mode class on <html>
  useEffect(() => {
    const html = document.documentElement;
    if (darkMode) {
      html.classList.add('dark');
    } else {
      html.classList.remove('dark');
    }
  }, [darkMode]);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    setIsLoadingStatus(true);
    try {
      const res = await api.getStatus();
      setStatus(res);
      setDocumentCount(res.document_count || 0);
      if (res.uploaded_files) {
        setUploadedFiles(res.uploaded_files);
      }
    } catch (error) {
      console.error('Error fetching status:', error);
    } finally {
      setIsLoadingStatus(false);
    }
  };

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 5000);
  };

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const res = await api.uploadFile(file);
      if (res.success) {
        showNotification('success', res.message);
        setUploadedFiles((prev) => [...prev, res.filename]);
        setDocumentCount((prev) => prev + res.chunks_added);
        await fetchStatus();
      } else {
        showNotification('error', res.error || 'Upload thất bại');
      }
    } catch {
      showNotification('error', 'Lỗi kết nối server');
    } finally {
      setIsUploading(false);
    }
  };

  const handleChat = useCallback(
    async (message: string): Promise<{ answer: string; contexts: Context[] }> => {
      setIsChatLoading(true);
      try {
        const res = await api.chat(message);
        if (res.success) {
          return { answer: res.answer, contexts: res.contexts };
        }
        return { answer: res.error || 'Đã xảy ra lỗi', contexts: [] };
      } catch {
        return { answer: 'Lỗi kết nối đến server', contexts: [] };
      } finally {
        setIsChatLoading(false);
      }
    },
    []
  );

  const handleClear = async () => {
    if (!confirm('Bạn có chắc muốn xóa toàn bộ dữ liệu?')) return;
    try {
      const res = await api.clearVectorStore();
      if (res.success) {
        showNotification('success', 'Đã xóa toàn bộ dữ liệu');
        setDocumentCount(0);
        setUploadedFiles([]);
        await fetchStatus();
      } else {
        showNotification('error', res.error || 'Xóa thất bại');
      }
    } catch {
      showNotification('error', 'Lỗi khi xóa dữ liệu');
    }
  };

  return (
    <div className={`flex h-screen overflow-hidden bg-gray-100 dark:bg-slate-900 text-gray-800 dark:text-gray-200 transition-colors duration-300`}>
      {/* Sidebar */}
      <Sidebar
        status={status}
        isLoading={isLoadingStatus}
        documentCount={documentCount}
        onClear={handleClear}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full relative overflow-hidden bg-gray-50 dark:bg-slate-900">
        {/* Dark Mode Toggle */}
        <div className="absolute top-4 right-4 z-50">
          <button
            onClick={() => setDarkMode(!darkMode)}
            className=" dark:text-gray-200 hover:scale-105 transition-transform cursor-pointer"
            title="Chuyển đổi giao diện"
          >
            <span className="material-icons-round" style={{ fontSize: '20px' }}>
              {darkMode ? 'light_mode' : 'dark_mode'}
            </span>
          </button>
        </div>

        {/* Notification Toast */}
        {notification && (
          <div
            className={`
              fixed top-4 right-16 z-50 flex items-center gap-2 px-4 py-3 rounded-xl shadow-xl animate-fade-in
              ${notification.type === 'success'
                ? 'bg-emerald-500 text-white'
                : 'bg-red-500 text-white'
              }
            `}
          >
            <span className="material-icons-round" style={{ fontSize: '18px' }}>
              {notification.type === 'success' ? 'check_circle' : 'error'}
            </span>
            <p className="text-sm font-medium">{notification.message}</p>
          </div>
        )}

        {documentCount === 0 ? (
          /* No files yet: centered upload zone */
          <div className="flex-1 flex flex-col items-center justify-center px-4 md:px-8 py-12">
            <div className="w-full max-w-2xl">
              {/* Header */}
              <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-amber-100 dark:bg-amber-500/10 mb-4">
                  <span className="material-icons-round text-amber-500" style={{ fontSize: '32px' }}>folder_open</span>
                </div>
                <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">Upload Tài Liệu</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                  Tải lên tài liệu để bắt đầu đặt câu hỏi với AI
                </p>
              </div>

              <FileUpload onUpload={handleUpload} isUploading={isUploading} />

              {/* Format hints */}
              <div className="mt-6 flex items-center justify-center gap-6 text-xs text-gray-400 dark:text-gray-500">
                <span className="flex items-center gap-1.5">
                  <span className="material-icons-round" style={{ fontSize: '14px' }}>picture_as_pdf</span>PDF
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="material-icons-round" style={{ fontSize: '14px' }}>description</span>Word
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="material-icons-round" style={{ fontSize: '14px' }}>image</span>PNG / JPG
                </span>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Compact file bar */}
            <div className="flex-shrink-0 px-4 md:px-8 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-slate-800/50">
              <div className="max-w-5xl mx-auto flex flex-wrap items-center gap-2">
                <span className="material-icons-round text-amber-500" style={{ fontSize: '18px' }}>folder_open</span>
                {uploadedFiles.map((file, idx) => (
                  <span
                    key={idx}
                    className="flex items-center gap-1 px-3 py-1 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 rounded-full text-xs font-medium"
                  >
                    <span className="material-icons-round" style={{ fontSize: '12px' }}>check_circle</span>
                    {file}
                  </span>
                ))}
                <FileUpload onUpload={handleUpload} isUploading={isUploading} compact />
              </div>
            </div>

            {/* Chat Section */}
            <div className="flex-1 flex flex-col overflow-hidden">
              <div className="flex-shrink-0 px-4 md:px-8 pt-4 bg-white dark:bg-slate-800/30 border-b border-gray-200 dark:border-gray-700/50">
                <div className="max-w-5xl mx-auto flex items-center gap-2 text-gray-700 dark:text-gray-300 pb-3">
                  <span className="material-icons-round" style={{ fontSize: '20px' }}>chat_bubble_outline</span>
                  <h2 className="font-semibold text-lg">Chat với AI</h2>
                </div>
              </div>
              <ChatInterface onSendMessage={handleChat} isLoading={isChatLoading} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
