import React, { useState, useRef, useEffect } from "react";
import type { Context } from "../services/api";

export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    contexts?: Context[];
    timestamp: number;
}

interface ChatHistoryMessage {
    role: "user" | "assistant";
    content: string;
}

interface ChatInterfaceProps {
    messages: Message[];
    setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
    onSendMessage: (message: string, history: ChatHistoryMessage[]) => Promise<{ answer: string; contexts: Context[] }>;
    isLoading: boolean;
    historyLimit: number;
}

const SUGGESTIONS = ["Tóm tắt nội dung chính của tài liệu", "Liệt kê các ý quan trọng theo dạng bullet", "Cho tôi ví dụ minh họa từ tài liệu", "So sánh 2 phần nội dung nổi bật"];

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ messages, setMessages, onSendMessage, isLoading, historyLimit }) => {
    const [input, setInput] = useState("");
    const [expandedContext, setExpandedContext] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const historyCount = messages.filter((msg) => msg.role === "user" || msg.role === "assistant").length;

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content: input.trim(),
            timestamp: Date.now(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput("");

        if (textareaRef.current) {
            textareaRef.current.style.height = "56px";
        }

        try {
            const history: ChatHistoryMessage[] = messages
                .filter((msg) => msg.role === "user" || msg.role === "assistant")
                .map((msg) => ({ role: msg.role, content: msg.content }))
                .slice(-historyLimit);

            const response = await onSendMessage(userMessage.content, history);
            const assistantMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: response.answer,
                contexts: response.contexts,
                timestamp: Date.now(),
            };

            setMessages((prev) => [...prev, assistantMessage]);
        } catch {
            setMessages((prev) => [
                ...prev,
                {
                    id: (Date.now() + 1).toString(),
                    role: "assistant",
                    content: "Đã xảy ra lỗi khi xử lý câu hỏi. Vui lòng thử lại.",
                    timestamp: Date.now(),
                },
            ]);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e as unknown as React.FormEvent);
        }
    };

    const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setInput(e.target.value);
        const el = e.target;
        el.style.height = "auto";
        el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
    };

    const useSuggestion = (text: string) => {
        setInput(text);
        if (textareaRef.current) {
            textareaRef.current.focus();
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
        }
    };

    return (
        <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
            <div className="flex-1 overflow-y-auto px-3 pt-4 pb-2 md:px-8 md:pt-6">
                {messages.length === 0 ? (
                    <WelcomeMessage onPickSuggestion={useSuggestion} />
                ) : (
                    <div className="mx-auto w-full max-w-4xl space-y-6 pb-12">
                        {messages.map((message, index) => (
                            <MessageBubble key={message.id} message={message} index={index} expandedContext={expandedContext} onToggleContext={setExpandedContext} />
                        ))}
                        {isLoading && <LoadingIndicator />}
                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            <footer className="z-20 px-3 pb-5 pt-3 md:px-8 md:pb-7">
                <div className="mx-auto w-full max-w-4xl">
                    <form onSubmit={handleSubmit} className="chat-shell rounded-[28px] p-2 shadow-xl shadow-slate-900/10">
                        <div className="rounded-3xl bg-white/88 px-2 py-1 dark:bg-slate-950/75">
                            <div className="flex items-end gap-2">
                                <button
                                    type="button"
                                    className="mb-2 ml-2 flex h-8 w-8 items-center justify-center rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                                    title="Tính năng đính kèm đang phát triển"
                                >
                                    <span className="material-icons-round" style={{ fontSize: "17px" }}>
                                        attach_file
                                    </span>
                                </button>
                                <textarea
                                    ref={textareaRef}
                                    value={input}
                                    onChange={handleTextareaInput}
                                    onKeyDown={handleKeyDown}
                                    placeholder="Hỏi tài liệu của bạn..."
                                    rows={1}
                                    disabled={isLoading}
                                    className="w-full resize-none border-none bg-transparent py-3 pr-2 text-[15px] text-slate-800 placeholder:text-slate-400 focus:outline-none dark:text-slate-100 dark:placeholder:text-slate-500"
                                    style={{ minHeight: "56px", maxHeight: "180px" }}
                                />
                                <button
                                    type="submit"
                                    disabled={!input.trim() || isLoading}
                                    className="mb-2 mr-1 flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900 text-white transition hover:-translate-y-0.5 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-sky-500 dark:text-slate-950 dark:hover:bg-sky-400"
                                    title="Gửi"
                                >
                                    <span className="material-icons-round" style={{ fontSize: "18px" }}>
                                        north
                                    </span>
                                </button>
                            </div>
                            <div className="flex items-center justify-between px-3 pb-2 pt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                                <span className="rounded-full bg-slate-100 px-2 py-1 dark:bg-slate-800">
                                    History: {Math.min(historyCount, historyLimit)}/{historyLimit}
                                </span>
                                <span>Enter để gửi, Shift + Enter để xuống dòng</span>
                            </div>
                        </div>
                    </form>
                    <p className="mt-3 text-center text-xs text-slate-500 dark:text-slate-400">AI có thể trả lời chưa chính xác. Hãy kiểm tra lại các thông tin quan trọng.</p>
                </div>
            </footer>
        </div>
    );
};

const WelcomeMessage: React.FC<{ onPickSuggestion: (text: string) => void }> = ({ onPickSuggestion }) => (
    <div className="mx-auto flex h-full w-full max-w-4xl flex-col items-center justify-center px-3 py-14 text-center animate-fade-in-up">
        <div className="mb-6 flex h-18 w-18 animate-soft-pulse items-center justify-center rounded-3xl border border-sky-200 bg-white shadow-lg shadow-sky-500/15 dark:border-sky-500/30 dark:bg-slate-900">
            <span className="material-icons-round text-sky-500" style={{ fontSize: "34px" }}>
                auto_awesome
            </span>
        </div>
        <h2 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100 md:text-4xl">Chào bạn, mình có thể giúp gì hôm nay?</h2>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-500 dark:text-slate-400 md:text-base">Đặt câu hỏi về tài liệu đã upload và nhận câu trả lời có trích dẫn nguồn tham chiếu.</p>
        <div className="mt-7 grid w-full max-w-3xl grid-cols-1 gap-2 md:grid-cols-2">
            {SUGGESTIONS.map((item) => (
                <button
                    key={item}
                    onClick={() => onPickSuggestion(item)}
                    className="rounded-2xl border border-slate-200/80 bg-white/90 px-4 py-3 text-left text-sm font-medium text-slate-700 transition hover:-translate-y-0.5 hover:border-sky-300 hover:shadow-md dark:border-slate-700 dark:bg-slate-900/75 dark:text-slate-200 dark:hover:border-sky-500/50"
                >
                    {item}
                </button>
            ))}
        </div>
    </div>
);

interface MessageBubbleProps {
    message: Message;
    index: number;
    expandedContext: string | null;
    onToggleContext: (id: string | null) => void;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, index, expandedContext, onToggleContext }) => {
    const isUser = message.role === "user";

    return (
        <div id={`message-anchor-${index}`} className="animate-fade-in">
            <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
                {!isUser && (
                    <div className="mt-1 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-2xl border border-sky-200 bg-white dark:border-slate-700 dark:bg-slate-900">
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

const LoadingIndicator: React.FC = () => (
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
