import React from "react";
import type { Message } from "./types";

interface MessageBubbleProps {
    message: Message;
    index: number;
    expandedContext: string | null;
    onToggleContext: (id: string | null) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, index, expandedContext, onToggleContext }) => {
    const isUser = message.role === "user";

    return (
        <div id={`message-anchor-${index}`} className="animate-fade-in">
            <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
                {!isUser && (
                    <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl border border-sky-200 bg-white dark:border-slate-700 dark:bg-slate-900">
                        <span className="material-icons-round text-sky-500" style={{ fontSize: "18px" }}>
                            smart_toy
                        </span>
                    </div>
                )}

                <div className={`max-w-[92%] md:max-w-[82%] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
                    <div
                        className={`rounded-3xl px-4 py-3 text-[15px] leading-relaxed shadow-sm ${
                            isUser ? "bg-slate-900 text-white dark:bg-sky-500 dark:text-slate-950" : "border border-slate-200/80 bg-white text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                        }`}
                    >
                        <p className="whitespace-pre-wrap">{message.content}</p>
                    </div>

                    {!isUser && message.contexts && message.contexts.length > 0 && (
                        <div className="mt-2 w-full">
                            <button
                                onClick={() => onToggleContext(expandedContext === message.id ? null : message.id)}
                                className="inline-flex items-center gap-1.5 rounded-full border border-slate-200/80 bg-white px-3 py-1 text-[11px] font-semibold text-slate-600 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                            >
                                <span className="material-icons-round" style={{ fontSize: "13px" }}>
                                    menu_book
                                </span>
                                {message.contexts.length} nguồn tham chiếu
                                <span className={`material-icons-round transition-transform ${expandedContext === message.id ? "rotate-180" : ""}`} style={{ fontSize: "14px" }}>
                                    expand_more
                                </span>
                            </button>

                            {expandedContext === message.id && (
                                <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
                                    {message.contexts.map((ctx, idx) => (
                                        <div key={idx} className="rounded-2xl border border-slate-200/80 bg-white p-3 text-sm shadow-sm dark:border-slate-700 dark:bg-slate-900">
                                            <div className="mb-1.5 flex items-center justify-between gap-2 text-[11px]">
                                                <div className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
                                                    <span className="material-icons-round text-sky-500" style={{ fontSize: "12px" }}>
                                                        description
                                                    </span>
                                                    <span className="truncate">{ctx.metadata.filename || "Unknown Document"}</span>
                                                </div>
                                                <span className="rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-slate-500 dark:bg-slate-800 dark:text-slate-300">{(1 - ctx.score).toFixed(2)}</span>
                                            </div>
                                            <p className="line-clamp-3 text-[12px] leading-relaxed text-slate-700 dark:text-slate-300">{ctx.content}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
