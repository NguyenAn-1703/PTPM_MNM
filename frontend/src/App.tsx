import { useState, useEffect, useCallback } from 'react';
import './styles/index';
import { api, type Context, type StatusResponse } from './services/api';
import { Sidebar, FileUpload, ChatInterface } from './components';


function App() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [documentCount, setDocumentCount] = useState(0);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Fetch status on mount
  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    setIsLoadingStatus(true);
    try {
      const res = await api.getStatus();
      setStatus(res);
      setDocumentCount(res.document_count || 0);
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
        showNotification('success', `✅ ${res.message}`);
        setUploadedFiles(prev => [...prev, res.filename]);
        setDocumentCount(prev => prev + res.chunks_added);
        await fetchStatus();
      } else {
        showNotification('error', `❌ ${res.error}`);
      }
    } catch (error) {
      showNotification('error', '❌ Lỗi kết nối server');
    } finally {
      setIsUploading(false);
    }
  };

  const handleChat = useCallback(async (message: string): Promise<{ answer: string; contexts: Context[] }> => {
    setIsChatLoading(true);
    try {
      const res = await api.chat(message);
      if (res.success) {
        return { answer: res.answer, contexts: res.contexts };
      } else {
        return { answer: res.error || 'Đã xảy ra lỗi', contexts: [] };
      }
    } catch (error) {
      return { answer: 'Lỗi kết nối đến server', contexts: [] };
    } finally {
      setIsChatLoading(false);
    }
  }, []);

  const handleClear = async () => {
    if (!confirm('Bạn có chắc muốn xóa toàn bộ dữ liệu?')) return;
    
    try {
      const res = await api.clearVectorStore();
      if (res.success) {
        showNotification('success', '✅ Đã xóa toàn bộ dữ liệu');
        setDocumentCount(0);
        setUploadedFiles([]);
        await fetchStatus();
      } else {
        showNotification('error', `❌ ${res.error}`);
      }
    } catch (error) {
      showNotification('error', '❌ Lỗi khi xóa dữ liệu');
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <Sidebar 
        status={status}
        isLoading={isLoadingStatus}
        documentCount={documentCount}
        onClear={handleClear}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Notification */}
        {notification && (
          <div className={`
            fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg animate-fade-in
            ${notification.type === 'success' ? 'bg-emerald-500/90' : 'bg-red-500/90'}
          `}>
            <p className="text-white font-medium">{notification.message}</p>
          </div>
        )}

        {/* Upload Section */}
        <div className="p-6 border-b border-slate-700/50">
          <h2 className="text-lg font-semibold text-white mb-4">📁 Upload Tài Liệu</h2>
          <FileUpload onUpload={handleUpload} isUploading={isUploading} />
          
          {/* Uploaded files list */}
          {uploadedFiles.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {uploadedFiles.map((file, idx) => (
                <span key={idx} className="px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded-full text-sm">
                  ✓ {file}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Chat Section */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <h2 className="text-lg font-semibold text-white px-6 pt-4">💬 Chat với AI</h2>
          <ChatInterface onSendMessage={handleChat} isLoading={isChatLoading} />
        </div>
      </main>
    </div>
  );
}

export default App;
