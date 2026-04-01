import React from "react";

interface WelcomeMessageProps {
    onPickSuggestion: (text: string) => void;
}

const SUGGESTIONS = ["Tóm tắt nội dung chính của tài liệu", "Liệt kê các ý quan trọng theo dạng bullet", "Cho tôi ví dụ minh họa từ tài liệu", "So sánh 2 phần nội dung nổi bật"];

export const WelcomeMessage: React.FC<WelcomeMessageProps> = ({ onPickSuggestion }) => (
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
