import React from 'react';
import { StatusResponse } from '../services/api';

interface SidebarProps {
  status: StatusResponse | null;
  isLoading: boolean;
  documentCount: number;
  onClear: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  status, 
  isLoading, 
  documentCount,
  onClear 
}) => {
  return (
    <aside className="w-80 h-screen glass p-6 flex flex-col gap-6 overflow-y-auto">
      {/* Logo & Title */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">RAG Assistant</h1>
          <p className="text-xs text-slate-400">AI Document Q&A</p>
        </div>
      </div>

      {/* Status Indicator */}
      <div className="flex items-center gap-2 text-sm">
        <span className={`w-2 h-2 rounded-full ${status?.success ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
        <span className="text-slate-300">
          {isLoading ? 'Đang kết nối...' : status?.success ? 'Đang hoạt động' : 'Lỗi kết nối'}
        </span>
      </div>

      {/* System Info */}
      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Thông số hệ thống</h2>
        
        <InfoCard 
          icon="🤖"
          label="LLM Model" 
          value={status?.llm_model || 'deepseek-r1:7b'} 
        />
        
        <InfoCard 
          icon="🧠"
          label="Embedding" 
          value={status?.embedding_model || 'nomic-embed-text'} 
        />
        
        <InfoCard 
          icon="💾"
          label="Vector DB" 
          value={status?.vector_db || 'FAISS'} 
        />
        
        <InfoCard 
          icon="📄"
          label="Documents" 
          value={`${documentCount} chunks`} 
        />
      </div>

      {/* Actions */}
      <div className="mt-auto space-y-3">
        <button 
          onClick={onClear}
          disabled={documentCount === 0}
          className="w-full py-2.5 px-4 rounded-lg bg-red-500/10 text-red-400 border border-red-500/30 
                     hover:bg-red-500/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          🗑️ Xóa dữ liệu
        </button>
        
        <div className="text-center text-xs text-slate-500">
          Powered by Ollama + LangChain
        </div>
      </div>
    </aside>
  );
};

interface InfoCardProps {
  icon: string;
  label: string;
  value: string;
}

const InfoCard: React.FC<InfoCardProps> = ({ icon, label, value }) => (
  <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
    <div className="flex items-center gap-2 mb-1">
      <span>{icon}</span>
      <span className="text-xs text-slate-400">{label}</span>
    </div>
    <div className="text-sm font-medium text-white truncate">{value}</div>
  </div>
);
