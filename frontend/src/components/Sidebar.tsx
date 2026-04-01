import React from "react";
import { SidebarActions } from "./sidebar/SidebarActions";
import { SidebarHeader } from "./sidebar/SidebarHeader";
import { SidebarSessionList } from "./sidebar/SidebarSessionList";
import { SidebarSystemCard } from "./sidebar/SidebarSystemCard";
import type { SidebarProps } from "./sidebar/types";

export const Sidebar: React.FC<SidebarProps> = ({ status, isLoading, documentCount, messages, chatSessions, activeSessionId, onClearVectorStore, onClearHistory, onNewChat, onSelectSession, onDeleteSession, isMobileOpen, onCloseMobile }) => {
    const orderedSessions = [...chatSessions].sort((a, b) => b.updatedAt - a.updatedAt);

    return (
        <aside
            className={`fixed inset-y-0 left-0 z-40 flex w-72.5 flex-col border-r border-slate-200/60 bg-white/92 shadow-2xl shadow-slate-900/10 backdrop-blur-xl transition-transform duration-300 dark:border-slate-700/70 dark:bg-slate-950/88 lg:static lg:z-20 lg:w-[300px] lg:translate-x-0 ${
                isMobileOpen ? "translate-x-0" : "-translate-x-full"
            }`}
        >
            <SidebarHeader onCloseMobile={onCloseMobile} />

            <div className="p-4">
                <button
                    onClick={onNewChat}
                    className="group flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-slate-700 dark:bg-sky-500 dark:text-slate-950 dark:hover:bg-sky-400"
                >
                    <span className="material-icons-round" style={{ fontSize: "18px" }}>
                        add
                    </span>
                    Đoạn chat mới
                </button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 pb-4">
                <SidebarSystemCard status={status} isLoading={isLoading} documentCount={documentCount} sessionCount={orderedSessions.length} />
                <SidebarSessionList sessions={orderedSessions} activeSessionId={activeSessionId} onSelectSession={onSelectSession} onDeleteSession={onDeleteSession} />
            </div>

            <SidebarActions hasMessages={messages.length > 0} hasDocuments={documentCount > 0} onClearHistory={onClearHistory} onClearVectorStore={onClearVectorStore} />
        </aside>
    );
};
