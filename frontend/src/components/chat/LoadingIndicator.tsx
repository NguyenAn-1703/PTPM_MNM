import React from "react";

export const LoadingIndicator: React.FC = () => (
    <div className="flex justify-start">
        <div className="mt-1 flex h-9 w-9 items-center justify-center rounded-2xl border border-sky-200 bg-white dark:border-slate-700 dark:bg-slate-900">
            <span className="material-icons-round text-sky-500" style={{ fontSize: "18px" }}>
                smart_toy
            </span>
        </div>
        <div className="ml-3 rounded-3xl border border-slate-200/80 bg-white px-4 py-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 animate-bounce rounded-full bg-slate-500 [animation-delay:-0.2s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-slate-500 [animation-delay:-0.1s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-slate-500" />
            </div>
        </div>
    </div>
);
