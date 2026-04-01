import React from "react";

interface SidebarHeaderProps {
    onCloseMobile: () => void;
}

export const SidebarHeader: React.FC<SidebarHeaderProps> = ({ onCloseMobile }) => (
    <div className="flex items-center justify-between border-b border-slate-200/70 px-5 py-5 dark:border-slate-700/70">
        <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-linear-to-br from-sky-500 to-emerald-500 shadow-lg shadow-sky-500/25">
                <span className="material-icons-round text-white" style={{ fontSize: "20px" }}>
                    auto_awesome
                </span>
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
            <span className="material-icons-round" style={{ fontSize: "18px" }}>
                close
            </span>
        </button>
    </div>
);
