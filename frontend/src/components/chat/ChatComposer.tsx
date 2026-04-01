import React from "react";

interface ChatComposerProps {
    input: string;
    isLoading: boolean;
    historyCount: number;
    historyLimit: number;
    textareaRef: React.RefObject<HTMLTextAreaElement | null>;
    onSubmit: (e: React.FormEvent) => Promise<void>;
    onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
    onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({ input, isLoading, historyCount, historyLimit, textareaRef, onSubmit, onChange, onKeyDown }) => (
    <form onSubmit={onSubmit} className="chat-shell rounded-[28px] p-2 shadow-xl shadow-slate-900/10">
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
                    onChange={onChange}
                    onKeyDown={onKeyDown}
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
);
