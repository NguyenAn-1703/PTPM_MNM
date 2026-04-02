import React, { useMemo, useState } from "react";
import type { Message } from "./types";

interface MessageBubbleProps {
    message: Message;
    index: number;
    expandedContext: string | null;
    onToggleContext: (id: string | null) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, index, expandedContext, onToggleContext }) => {
    const isUser = message.role === "user";
    type PanelType = "debug" | "references" | "origins" | null;
    const [selectedContextIndex, setSelectedContextIndex] = useState<number | null>(null);
    const [activePanel, setActivePanel] = useState<PanelType>(null);
    const isReferenceOpen = activePanel === "references" && expandedContext === message.id;
    const isSourceOriginsOpen = activePanel === "origins";
    const isDebugPanelOpen = activePanel === "debug";

    const selectedContext = useMemo(() => {
        if (selectedContextIndex === null || !message.contexts) {
            return null;
        }
        return message.contexts[selectedContextIndex] || null;
    }, [message.contexts, selectedContextIndex]);

    const renderHighlightedContent = (content: string, highlights?: Array<{ start: number; end: number }>) => {
        if (!highlights || highlights.length === 0) {
            return <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-slate-700 dark:text-slate-200">{content}</p>;
        }

        const validRanges = [...highlights]
            .filter((item) => Number.isInteger(item.start) && Number.isInteger(item.end) && item.start >= 0 && item.end > item.start && item.end <= content.length)
            .sort((a, b) => a.start - b.start);

        if (validRanges.length === 0) {
            return <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-slate-700 dark:text-slate-200">{content}</p>;
        }

        const parts: React.ReactNode[] = [];
        let cursor = 0;

        validRanges.forEach((range, idx) => {
            if (range.start > cursor) {
                parts.push(<span key={`plain-${idx}-${cursor}`}>{content.slice(cursor, range.start)}</span>);
            }

            parts.push(
                <mark key={`highlight-${idx}-${range.start}`} className="rounded bg-amber-200/80 px-0.5 text-slate-900 dark:bg-amber-300/80">
                    {content.slice(range.start, range.end)}
                </mark>,
            );
            cursor = range.end;
        });

        if (cursor < content.length) {
            parts.push(<span key={`tail-${cursor}`}>{content.slice(cursor)}</span>);
        }

        return <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-slate-700 dark:text-slate-200">{parts}</p>;
    };

    const formatSourceLocation = (ctx: NonNullable<Message["contexts"]>[number]) => {
        const source = ctx.source_location;
        const page = source?.page_start ?? ctx.metadata.page_number;
        const charStart = source?.char_start ?? ctx.metadata.char_start;
        const charEnd = source?.char_end ?? ctx.metadata.char_end;

        const tokens: string[] = [];
        if (typeof page === "number") {
            tokens.push(`Trang ${page}`);
        }
        if (typeof charStart === "number" && typeof charEnd === "number") {
            tokens.push(`Vị trí ${charStart}-${charEnd}`);
        }

        return tokens.length > 0 ? tokens.join(" • ") : "Không có vị trí nguồn";
    };

    const handleToggleReferences = () => {
        if (isReferenceOpen) {
            onToggleContext(null);
            setActivePanel(null);
            setSelectedContextIndex(null);
            return;
        }

        onToggleContext(message.id);
        setActivePanel("references");
        setSelectedContextIndex(null);
    };

    const handleToggleSourceOrigins = () => {
        if (isSourceOriginsOpen) {
            setActivePanel(null);
            return;
        }

        onToggleContext(null);
        setSelectedContextIndex(null);
        setActivePanel("origins");
    };

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
                        {!isUser && message.isFollowUpRewrite && (
                            <span className="mb-2 inline-flex items-center gap-1 rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.06em] text-violet-700 dark:border-violet-500/45 dark:bg-violet-500/12 dark:text-violet-300">
                                <span className="material-icons-round" style={{ fontSize: "11px" }}>
                                    auto_fix_high
                                </span>
                                Follow-up rewritten
                            </span>
                        )}
                        {!isUser && typeof message.confidenceScore === "number" && (
                            <div className="mb-2 flex flex-wrap items-center gap-1.5">
                                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.06em] text-emerald-700 dark:border-emerald-500/45 dark:bg-emerald-500/12 dark:text-emerald-300">
                                    Confidence: {(message.confidenceScore * 100).toFixed(0)}% ({message.confidenceLabel || "n/a"})
                                </span>
                                {message.retrievalMode && (
                                    <span className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.06em] text-sky-700 dark:border-sky-500/45 dark:bg-sky-500/12 dark:text-sky-300">
                                        Retrieval: {message.retrievalMode}
                                    </span>
                                )}
                                {message.selfRagApplied && (
                                    <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.06em] text-amber-700 dark:border-amber-500/45 dark:bg-amber-500/12 dark:text-amber-300">
                                        Self-RAG retry
                                    </span>
                                )}
                                {message.rerankerModel && (
                                    <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.06em] text-slate-600 dark:border-slate-500/45 dark:bg-slate-500/12 dark:text-slate-300">
                                        Rerank: {message.rerankerModel}
                                    </span>
                                )}
                            </div>
                        )}
                        <p className="whitespace-pre-wrap">{message.content}</p>
                    </div>

                    {!isUser && message.contexts && message.contexts.length > 0 && (
                        <div className="mt-2 w-full">
                            <div className="flex flex-wrap items-center gap-2">
                                {message.standaloneQuestion && (
                                    <button
                                        type="button"
                                        onClick={() => {
                                            if (isDebugPanelOpen) {
                                                setActivePanel(null);
                                                return;
                                            }

                                            onToggleContext(null);
                                            setSelectedContextIndex(null);
                                            setActivePanel("debug");
                                        }}
                                        className="inline-flex items-center gap-1.5 rounded-full border border-violet-200/80 bg-violet-50 px-3 py-1 text-[11px] font-semibold text-violet-700 transition hover:bg-violet-100 dark:border-violet-500/40 dark:bg-violet-500/10 dark:text-violet-300 dark:hover:bg-violet-500/20"
                                    >
                                        <span className="material-icons-round" style={{ fontSize: "13px" }}>
                                            bug_report
                                        </span>
                                        Debug follow-up
                                        <span className={`material-icons-round transition-transform ${isDebugPanelOpen ? "rotate-180" : ""}`} style={{ fontSize: "14px" }}>
                                            expand_more
                                        </span>
                                    </button>
                                )}

                                <button
                                    onClick={handleToggleReferences}
                                    className="inline-flex items-center gap-1.5 rounded-full border border-slate-200/80 bg-white px-3 py-1 text-[11px] font-semibold text-slate-600 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                                >
                                    <span className="material-icons-round" style={{ fontSize: "13px" }}>
                                        menu_book
                                    </span>
                                    {message.contexts.length} nguồn tham chiếu
                                    <span className={`material-icons-round transition-transform ${isReferenceOpen ? "rotate-180" : ""}`} style={{ fontSize: "14px" }}>
                                        expand_more
                                    </span>
                                </button>

                                <button
                                    type="button"
                                    onClick={handleToggleSourceOrigins}
                                    className="inline-flex items-center gap-1.5 rounded-full border border-sky-200/80 bg-sky-50 px-3 py-1 text-[11px] font-semibold text-sky-700 transition hover:bg-sky-100 dark:border-sky-500/40 dark:bg-sky-500/10 dark:text-sky-300 dark:hover:bg-sky-500/20"
                                >
                                    <span className="material-icons-round" style={{ fontSize: "13px" }}>
                                        pin_drop
                                    </span>
                                    Hiển thị nguồn gốc
                                    <span className={`material-icons-round transition-transform ${isSourceOriginsOpen ? "rotate-180" : ""}`} style={{ fontSize: "14px" }}>
                                        expand_more
                                    </span>
                                </button>
                            </div>

                            {isDebugPanelOpen && message.standaloneQuestion && (
                                <div className="mt-2 rounded-2xl border border-violet-200/80 bg-violet-50/60 p-3 dark:border-violet-500/35 dark:bg-violet-500/10">
                                    <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-violet-700 dark:text-violet-300">Standalone question</p>
                                    <p className="mt-1 whitespace-pre-wrap text-[13px] leading-relaxed text-slate-700 dark:text-slate-100">{message.standaloneQuestion}</p>
                                </div>
                            )}

                            {isSourceOriginsOpen && (
                                <div className="mt-2 grid grid-cols-1 gap-2 rounded-2xl border border-sky-200/70 bg-sky-50/50 p-3 dark:border-sky-500/30 dark:bg-sky-500/10">
                                    {message.contexts.map((ctx, idx) => (
                                        <div key={`source-origin-${idx}`} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200/80 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900">
                                            <div>
                                                <p className="text-[11px] font-semibold text-slate-700 dark:text-slate-200">{ctx.metadata.filename || "Unknown Document"}</p>
                                                <p className="text-[11px] text-slate-500 dark:text-slate-400">{formatSourceLocation(ctx)}</p>
                                            </div>
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    onToggleContext(message.id);
                                                    setActivePanel("references");
                                                    setSelectedContextIndex(idx);
                                                }}
                                                className="rounded-full border border-slate-300 px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
                                            >
                                                Xem context
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {isReferenceOpen && (
                                <div className="mt-2 grid grid-cols-1 gap-2">
                                    {message.contexts.map((ctx, idx) => (
                                        <button
                                            key={idx}
                                            type="button"
                                            onClick={() => setSelectedContextIndex(idx)}
                                            className="rounded-2xl border border-slate-200/80 bg-white p-3 text-left text-sm shadow-sm transition hover:border-sky-300 hover:bg-sky-50/40 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-sky-500/60 dark:hover:bg-slate-800"
                                        >
                                            <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                                                <div className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
                                                    <span className="material-icons-round text-sky-500" style={{ fontSize: "12px" }}>
                                                        description
                                                    </span>
                                                    <span className="truncate">{ctx.metadata.filename || "Unknown Document"}</span>
                                                </div>
                                                <span className="shrink-0 rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-slate-500 dark:bg-slate-800 dark:text-slate-300">{(1 - ctx.score).toFixed(2)}</span>
                                            </div>
                                            <p className="mb-1 text-[11px] text-slate-500 dark:text-slate-400">{formatSourceLocation(ctx)}</p>
                                            <p className="line-clamp-3 text-[12px] leading-relaxed text-slate-700 dark:text-slate-300">{ctx.content}</p>
                                        </button>
                                    ))}

                                    {selectedContext && (
                                        <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-3 dark:border-amber-500/40 dark:bg-amber-500/10">
                                            <div className="mb-2 flex items-center justify-between gap-2">
                                                <p className="text-[12px] font-semibold text-slate-700 dark:text-slate-200">Context gốc được dùng để trả lời</p>
                                                <button
                                                    type="button"
                                                    onClick={() => setSelectedContextIndex(null)}
                                                    className="rounded-full border border-slate-300 px-2 py-0.5 text-[11px] font-semibold text-slate-600 hover:bg-white dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
                                                >
                                                    Đóng
                                                </button>
                                            </div>
                                            <p className="mb-2 text-[11px] text-slate-500 dark:text-slate-400">{formatSourceLocation(selectedContext)}</p>
                                            {renderHighlightedContent(selectedContext.content, selectedContext.highlights)}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
