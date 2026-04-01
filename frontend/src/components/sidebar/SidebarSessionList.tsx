import React from "react";
import type { ChatSession } from "./types";

interface SidebarSessionListProps {
    sessions: ChatSession[];
    activeSessionId: string;
    onSelectSession: (sessionId: string) => void;
    onDeleteSession: (sessionId: string) => void;
}

const getSessionTitle = (session: ChatSession): string => {
    const firstUserMessage = session.messages.find((item) => item.role === "user");
    if (firstUserMessage) {
        return firstUserMessage.content;
    }
    return "Đoạn chat mới";
};

export const SidebarSessionList: React.FC<SidebarSessionListProps> = ({ sessions, activeSessionId, onSelectSession, onDeleteSession }) => (
    <>
        <div className="mb-2 flex items-center justify-between px-1">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">Các đoạn chat</h3>
        </div>
        <div className="mb-4 space-y-1">
            {sessions.map((session, idx) => {
                const isCurrent = session.id === activeSessionId;
                const sessionTitle = getSessionTitle(session);

                return (
                    <div
                        key={session.id}
                        onClick={() => onSelectSession(session.id)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                onSelectSession(session.id);
                            }
                        }}
                        role="button"
                        tabIndex={0}
                        className={`group flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm transition ${
                            isCurrent ? "bg-sky-100 text-sky-800 dark:bg-sky-500/20 dark:text-sky-200" : "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                        }`}
                        title={sessionTitle}
                    >
                        <span
                            className={`inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[10px] font-bold ${
                                isCurrent ? "bg-sky-200 text-sky-700 dark:bg-sky-500/30 dark:text-sky-100" : "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-200"
                            }`}
                        >
                            {idx + 1}
                        </span>
                        <span className="truncate">{sessionTitle}</span>
                        <button
                            type="button"
                            onClick={(e) => {
                                e.stopPropagation();
                                onDeleteSession(session.id);
                            }}
                            className="ml-auto flex h-7 w-7 items-center justify-center rounded-lg text-slate-400 opacity-0 transition hover:bg-rose-100 hover:text-rose-600 group-hover:opacity-100 dark:hover:bg-rose-500/20 dark:hover:text-rose-300"
                            title="Xóa đoạn chat"
                        >
                            <span className="material-icons-round" style={{ fontSize: "16px" }}>
                                delete
                            </span>
                        </button>
                    </div>
                );
            })}
        </div>
    </>
);
