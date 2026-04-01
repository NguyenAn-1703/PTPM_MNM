import React from "react";

interface SidebarActionsProps {
    hasMessages: boolean;
    hasDocuments: boolean;
    onClearHistory: () => void;
    onClearVectorStore: () => void;
    onResetSessionContext: () => void;
}

export const SidebarActions: React.FC<SidebarActionsProps> = ({ hasMessages, hasDocuments, onClearHistory, onClearVectorStore, onResetSessionContext }) => (
    <div className="space-y-2 border-t border-slate-200/70 p-4 dark:border-slate-700/70">
        <button
            onClick={onResetSessionContext}
            disabled={!hasMessages}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-amber-700 transition hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-45 dark:text-amber-300 dark:hover:bg-amber-500/10"
        >
            <span className="material-icons-round" style={{ fontSize: "16px" }}>
                refresh
            </span>
            Reset ngữ cảnh phiên hiện tại
        </button>
        <button
            onClick={onClearHistory}
            disabled={!hasMessages}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-45 dark:text-slate-300 dark:hover:bg-slate-800"
        >
            <span className="material-icons-round text-slate-400" style={{ fontSize: "16px" }}>
                history_toggle_off
            </span>
            Xóa toàn bộ lịch sử chat
        </button>
        <button
            onClick={onClearVectorStore}
            disabled={!hasDocuments}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-45 dark:text-rose-400 dark:hover:bg-rose-500/10"
        >
            <span className="material-icons-round" style={{ fontSize: "16px" }}>
                delete_forever
            </span>
            Xóa toàn bộ tài liệu
        </button>
    </div>
);
