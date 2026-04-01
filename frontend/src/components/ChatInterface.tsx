import React, { useEffect, useRef, useState } from "react";
import type { Context } from "../services/api";
import { ChatComposer } from "./chat/ChatComposer";
import { LoadingIndicator } from "./chat/LoadingIndicator";
import { MessageBubble } from "./chat/MessageBubble";
import { WelcomeMessage } from "./chat/WelcomeMessage";
import type { ChatHistoryMessage, Message } from "./chat/types";

interface ChatInterfaceProps {
    messages: Message[];
    setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
    onSendMessage: (message: string, history: ChatHistoryMessage[]) => Promise<{ answer: string; contexts: Context[] }>;
    isLoading: boolean;
    historyLimit: number;
}

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
                    <ChatComposer input={input} isLoading={isLoading} historyCount={historyCount} historyLimit={historyLimit} textareaRef={textareaRef} onSubmit={handleSubmit} onChange={handleTextareaInput} onKeyDown={handleKeyDown} />
                    <p className="mt-3 text-center text-xs text-slate-500 dark:text-slate-400">AI có thể trả lời chưa chính xác. Hãy kiểm tra lại các thông tin quan trọng.</p>
                </div>
            </footer>
        </div>
    );
};
