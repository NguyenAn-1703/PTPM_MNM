import React from 'react';
import type { StatusResponse } from '../services/api';

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
  onClear,
}) => {
  const isActive = !isLoading && status?.success;

  return (
    <aside className="w-80 flex-shrink-0 flex flex-col border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-slate-800 transition-colors duration-300 relative z-20">
      {/* Logo & Title */}
      <div className="p-6 flex items-center gap-3 border-b border-gray-100 dark:border-gray-700/50">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
          <span className="material-icons-round text-white" style={{ fontSize: '20px' }}>smart_toy</span>
        </div>
        <div>
          <h1 className="font-bold text-lg text-gray-900 dark:text-white leading-tight">RAG Assistant</h1>
          <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">AI Document Q&A</p>
        </div>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Status Indicator */}
        <div className="flex items-center gap-2 px-2">
          <span className="relative flex h-3 w-3">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isActive ? 'bg-emerald-400' : 'bg-red-400'}`}></span>
            <span className={`relative inline-flex rounded-full h-3 w-3 ${isActive ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
          </span>
          <span className={`text-sm font-medium ${isActive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
            {isLoading ? 'Đang kết nối...' : isActive ? 'Đang hoạt động' : 'Lỗi kết nối'}
          </span>
        </div>

        {/* System Info */}
        <div className="space-y-3">
          <h3 className="px-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">Thông số hệ thống</h3>

          <InfoCard
            iconName="psychology"
            iconBg="bg-pink-100 dark:bg-pink-900/30"
            iconColor="text-pink-600 dark:text-pink-400"
            label="LLM Model"
            value={status?.llm_model || 'qwen2.5:7b'}
          />
          <InfoCard
            iconName="hub"
            iconBg="bg-orange-100 dark:bg-orange-900/30"
            iconColor="text-orange-600 dark:text-orange-400"
            label="Embedding"
            value={status?.embedding_model || 'nomic-embed-text'}
          />
          <InfoCard
            iconName="storage"
            iconBg="bg-blue-100 dark:bg-blue-900/30"
            iconColor="text-blue-600 dark:text-blue-400"
            label="Vector DB"
            value={status?.vector_db || 'FAISS'}
          />
          <InfoCard
            iconName="description"
            iconBg="bg-emerald-100 dark:bg-emerald-900/30"
            iconColor="text-emerald-600 dark:text-emerald-400"
            label="Documents"
            value={`${documentCount} chunks`}
          />
        </div>
      </div>

      {/* Bottom Actions */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-slate-900/50">
        <button
          onClick={onClear}
          disabled={documentCount === 0}
          className="w-full mb-3 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg border border-red-200 dark:border-red-900/50 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <span className="material-icons-round" style={{ fontSize: '18px' }}>delete_outline</span>
          Xóa dữ liệu
        </button>
        <p className="text-[10px] text-center text-gray-400 dark:text-gray-500">
          Powered by Ollama + LangChain
        </p>
      </div>
    </aside>
  );
};

interface InfoCardProps {
  iconName: string;
  iconBg: string;
  iconColor: string;
  label: string;
  value: string;
}

const InfoCard: React.FC<InfoCardProps> = ({ iconName, iconBg, iconColor, label, value }) => (
  <div className="group p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-slate-800/50 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-all duration-200 hover:shadow-md hover:border-indigo-300 dark:hover:border-indigo-500/30">
    <div className="flex items-start gap-3">
      <div className={`p-2 rounded-lg ${iconBg} ${iconColor}`}>
        <span className="material-icons-round" style={{ fontSize: '18px' }}>{iconName}</span>
      </div>
      <div>
        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-0.5">{label}</p>
        <p className="text-sm font-bold text-gray-800 dark:text-gray-100 truncate">{value}</p>
      </div>
    </div>
  </div>
);
