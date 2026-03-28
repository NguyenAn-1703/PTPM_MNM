import React from 'react';
import type { StatusResponse } from '../services/api';
import type { Message } from './ChatInterface';

interface ChatSession {
  id: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
}

interface SidebarProps {
  status: StatusResponse | null;
  isLoading: boolean;
  documentCount: number;
  messages: Message[];
  chatSessions: ChatSession[];
  activeSessionId: string;
  onClearVectorStore: () => void;
  onClearHistory: () => void;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  status,
  isLoading,
  documentCount,
  messages,
  chatSessions,
  activeSessionId,
  onClearVectorStore,
  onClearHistory,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  isMobileOpen,
  onCloseMobile,
}) => {
  const isActive = !isLoading && status?.success;
  const orderedSessions = [...chatSessions].sort((a, b) => b.updatedAt - a.updatedAt);

  const getSessionTitle = (session: ChatSession) => {
    const firstUserMessage = session.messages.find((item) => item.role === 'user');
    if (firstUserMessage) {
      return firstUserMessage.content;
    }
    return 'Đoạn chat mới';
  };

  return (
    <aside
      className={
        `fixed inset-y-0 left-0 z-40 flex w-[290px] flex-col border-r border-slate-200/60 bg-white/92 shadow-2xl shadow-slate-900/10 backdrop-blur-xl transition-transform duration-300 dark:border-slate-700/70 dark:bg-slate-950/88 lg:static lg:z-20 lg:w-[300px] lg:translate-x-0 ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`
      }
    >
      <div className="flex items-center justify-between border-b border-slate-200/70 px-5 py-5 dark:border-slate-700/70">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 to-emerald-500 shadow-lg shadow-sky-500/25">
            <span className="material-icons-round text-white" style={{ fontSize: '20px' }}>auto_awesome</span>
          </div>
          <div>
            <h1 className="text-[17px] font-bold text-slate-900 dark:text-slate-100">Fusion Assistant</h1>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">RAG Workspace</p>
          </div>
        </div>
        <button
          onClick={onCloseMobile}
          className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100 lg:hidden"
          title="Đóng menu"
        >
          <span className="material-icons-round" style={{ fontSize: '18px' }}>close</span>
        </button>
      </div>

      <div className="p-4">
        <button
          onClick={onNewChat}
          className="group flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-slate-700 dark:bg-sky-500 dark:text-slate-950 dark:hover:bg-sky-400"
        >
          <span className="material-icons-round" style={{ fontSize: '18px' }}>add</span>
          Đoạn chat mới
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <div className="mb-5 rounded-2xl border border-slate-200/70 bg-slate-50/90 p-3 dark:border-slate-700/70 dark:bg-slate-900/60">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500 dark:text-slate-400">System</span>
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-semibold ${isActive ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300' : 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300'}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${isActive ? 'bg-emerald-500' : 'bg-rose-500'}`} />
              {isLoading ? 'Checking' : isActive ? 'Online' : 'Offline'}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-600 dark:text-slate-300">
            <div className="rounded-none border border-slate-200/70 bg-white px-2 py-2 dark:border-slate-700/70 dark:bg-slate-950/70">
              <p className="mb-1 text-[10px] uppercase text-slate-400">Docs : {<span className="font-bold">{documentCount}</span>}</p>
              </div>
            <div className="rounded-none border border-slate-200/70 bg-white px-2 py-2 dark:border-slate-700/70 dark:bg-slate-950/70">
              <p className="mb-1 text-[10px] uppercase  text-slate-400">History : { <span className="font-boild">{orderedSessions.length}</span>}</p>
            </div>
            <div className="col-span-2 rounded-none border border-slate-200/70 bg-white px-2 py-2 dark:border-slate-700/70 dark:bg-slate-950/70">
              <p className="mb-1 text-[10px] uppercase tracking-[0.08em] text-slate-400">Model</p>
              <p className="truncate font-semibold">{status?.llm_model || 'N/A'}</p>
            </div>
          </div>
        </div>

        <div className="mb-2 flex items-center justify-between px-1">
          <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500 dark:text-slate-400">Các đoạn chat</h3>
        </div>
        <div className="mb-4 space-y-1">
          {orderedSessions.map((session, idx) => {
            const isCurrent = session.id === activeSessionId;
            return (
              <div
                key={session.id}
                onClick={() => onSelectSession(session.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectSession(session.id);
                  }
                }}
                role="button"
                tabIndex={0}
                className={`group flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm transition ${
                  isCurrent
                    ? 'bg-sky-100 text-sky-800 dark:bg-sky-500/20 dark:text-sky-200'
                    : 'text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
                }`}
                title={getSessionTitle(session)}
              >
                <span className={`inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[10px] font-bold ${isCurrent ? 'bg-sky-200 text-sky-700 dark:bg-sky-500/30 dark:text-sky-100' : 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-200'}`}>
                  {idx + 1}
                </span>
                <span className="truncate">{getSessionTitle(session)}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.id);
                  }}
                  className="ml-auto flex h-7 w-7 items-center justify-center rounded-lg text-slate-400 opacity-0 transition hover:bg-rose-100 hover:text-rose-600 group-hover:opacity-100 dark:hover:bg-rose-500/20 dark:hover:text-rose-300"
                  title="Xóa đoạn chat"
                >
                  <span className="material-icons-round" style={{ fontSize: '16px' }}>delete</span>
                </button>
              </div>
            );
          })}
        </div>

      </div>

      <div className="space-y-2 border-t border-slate-200/70 p-4 dark:border-slate-700/70">
        <button
          onClick={onClearHistory}
          disabled={messages.length === 0}
          className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-45 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <span className="material-icons-round text-slate-400" style={{ fontSize: '16px' }}>history_toggle_off</span>
          Xóa toàn bộ lịch sử chat
        </button>
        <button
          onClick={onClearVectorStore}
          disabled={documentCount === 0}
          className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-45 dark:text-rose-400 dark:hover:bg-rose-500/10"
        >
          <span className="material-icons-round" style={{ fontSize: '16px' }}>delete_forever</span>
          Xóa toàn bộ kho tài liệu
        </button>
      </div>
    </aside>
  );
};
