import React from "react";
import type { StatusResponse } from "../../services/api";

interface SidebarSystemCardProps {
    status: StatusResponse | null;
    isLoading: boolean;
    documentCount: number;
    sessionCount: number;
}

export const SidebarSystemCard: React.FC<SidebarSystemCardProps> = ({ status, isLoading, documentCount, sessionCount }) => {
    const isActive = !isLoading && status?.success;

    return (
        <div className="mb-5 rounded-2xl border border-slate-200/70 bg-slate-50/90 p-3 dark:border-slate-700/70 dark:bg-slate-900/60">
            <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">System</span>
                <span
                    className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-semibold ${isActive ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300" : "bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300"}`}
                >
                    <span className={`h-1.5 w-1.5 rounded-full ${isActive ? "bg-emerald-500" : "bg-rose-500"}`} />
                    {isLoading ? "Checking" : isActive ? "Online" : "Offline"}
                </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-600 dark:text-slate-300">
                <div className="rounded-none border border-slate-200/70 bg-white px-2 py-2 dark:border-slate-700/70 dark:bg-slate-950/70">
                    <p className="mb-1 text-[10px] uppercase text-slate-400">Docs : </p>
                    <span className="font-bold">{documentCount}</span>
                </div>
                <div className="rounded-none border border-slate-200/70 bg-white px-2 py-2 dark:border-slate-700/70 dark:bg-slate-950/70">
                    <p className="mb-1 text-[10px] uppercase text-slate-400">History : </p>
                    <span className="font-bold">{sessionCount}</span>
                </div>
                <div className="col-span-2 rounded-none border border-slate-200/70 bg-white px-2 py-2 dark:border-slate-700/70 dark:bg-slate-950/70">
                    <p className="mb-1 text-[10px] uppercase tracking-[0.08em] text-slate-400">Model</p>
                    <p className="truncate font-semibold">{status?.llm_model || "N/A"}</p>
                </div>
            </div>
        </div>
    );
};
