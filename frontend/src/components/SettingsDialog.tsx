import React, { useState } from "react";

const CHUNK_SIZE_OPTIONS = [500, 1000, 1500, 2000] as const;
const CHUNK_OVERLAP_OPTIONS = [50, 100, 200, 300] as const;
const TOP_K_OPTIONS = [3, 5, 8, 10] as const;

const ensureOption = (value: number, options: readonly number[], fallback: number): number => {
    return options.includes(value) ? value : fallback;
};

interface SettingsDialogProps {
    isOpen: boolean;
    chunkSize: number;
    chunkOverlap: number;
    topK: number;
    retrievalMode: "vector" | "hybrid" | "hybrid_multivector";
    useReranker: boolean;
    useSelfRag: boolean;
    onClose: () => void;
    onApply: (settings: { chunkSize: number; chunkOverlap: number; topK: number; retrievalMode: "vector" | "hybrid" | "hybrid_multivector"; useReranker: boolean; useSelfRag: boolean }) => void;
}

export const SettingsDialog: React.FC<SettingsDialogProps> = ({ isOpen, chunkSize, chunkOverlap, topK, retrievalMode, useReranker, useSelfRag, onClose, onApply }) => {
    const [draftChunkSize, setDraftChunkSize] = useState(ensureOption(chunkSize, CHUNK_SIZE_OPTIONS, 1500));
    const [draftChunkOverlap, setDraftChunkOverlap] = useState(ensureOption(chunkOverlap, CHUNK_OVERLAP_OPTIONS, 300));
    const [draftTopK, setDraftTopK] = useState(ensureOption(topK, TOP_K_OPTIONS, 5));
    const [draftRetrievalMode, setDraftRetrievalMode] = useState<"vector" | "hybrid" | "hybrid_multivector">(retrievalMode || "hybrid");
    const [draftUseReranker, setDraftUseReranker] = useState(Boolean(useReranker));
    const [draftUseSelfRag, setDraftUseSelfRag] = useState(Boolean(useSelfRag));

    const resetDrafts = () => {
        setDraftChunkSize(ensureOption(chunkSize, CHUNK_SIZE_OPTIONS, 1500));
        setDraftChunkOverlap(ensureOption(chunkOverlap, CHUNK_OVERLAP_OPTIONS, 300));
        setDraftTopK(ensureOption(topK, TOP_K_OPTIONS, 5));
        setDraftRetrievalMode(retrievalMode || "hybrid");
        setDraftUseReranker(Boolean(useReranker));
        setDraftUseSelfRag(Boolean(useSelfRag));
    };

    const handleClose = () => {
        resetDrafts();
        onClose();
    };

    if (!isOpen) return null;

    const isInvalid = draftChunkOverlap >= draftChunkSize;

    const handleApply = () => {
        if (isInvalid) return;
        onApply({
            chunkSize: draftChunkSize,
            chunkOverlap: draftChunkOverlap,
            topK: draftTopK,
            retrievalMode: draftRetrievalMode,
            useReranker: draftUseReranker,
            useSelfRag: draftUseSelfRag,
        });
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <button aria-label="Close settings" className="absolute inset-0 bg-slate-950/50 backdrop-blur-sm" onClick={handleClose} />

            <div className="relative z-10 w-full max-w-md rounded-3xl border border-slate-200/70 bg-white p-5 shadow-2xl dark:border-slate-700 dark:bg-slate-900 md:p-6">
                <div className="mb-4 flex items-start justify-between">
                    <div>
                        <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Cài đặt Chunking</h3>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Điều chỉnh tham số chunk trước khi upload tài liệu.</p>
                    </div>
                    <button
                        className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                        onClick={handleClose}
                        title="Đóng cài đặt"
                    >
                        <span className="material-icons-round" style={{ fontSize: "18px" }}>
                            close
                        </span>
                    </button>
                </div>

                <div className="space-y-3">
                    <label className="block rounded-2xl border border-slate-200/80 bg-slate-50/70 p-3 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-300">
                        Chunk size
                        <select
                            value={draftChunkSize}
                            onChange={(e) => setDraftChunkSize(Number(e.target.value))}
                            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-sky-400 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
                        >
                            {CHUNK_SIZE_OPTIONS.map((option) => (
                                <option key={option} value={option}>
                                    {option}
                                </option>
                            ))}
                        </select>
                    </label>

                    <label className="block rounded-2xl border border-slate-200/80 bg-slate-50/70 p-3 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-300">
                        Chunk overlap
                        <select
                            value={draftChunkOverlap}
                            onChange={(e) => setDraftChunkOverlap(Number(e.target.value))}
                            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-sky-400 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
                        >
                            {CHUNK_OVERLAP_OPTIONS.map((option) => (
                                <option key={option} value={option}>
                                    {option}
                                </option>
                            ))}
                        </select>
                    </label>

                    {isInvalid && <p className="text-xs font-semibold text-rose-500">Chunk overlap phải nhỏ hơn chunk size.</p>}

                    <label className="block rounded-2xl border border-slate-200/80 bg-slate-50/70 p-3 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-300">
                        Top-K retrieval
                        <select
                            value={draftTopK}
                            onChange={(e) => setDraftTopK(Number(e.target.value))}
                            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-sky-400 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
                        >
                            {TOP_K_OPTIONS.map((option) => (
                                <option key={option} value={option}>
                                    {option}
                                </option>
                            ))}
                        </select>
                    </label>

                    <label className="block rounded-2xl border border-slate-200/80 bg-slate-50/70 p-3 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-300">
                        Retrieval mode
                        <select
                            value={draftRetrievalMode}
                            onChange={(e) => setDraftRetrievalMode(e.target.value as "vector" | "hybrid" | "hybrid_multivector")}
                            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-sky-400 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
                        >
                            <option value="hybrid">Hybrid (Vector + Keyword)</option>
                            <option value="hybrid_multivector">Hybrid Multi-vector</option>
                            <option value="vector">Vector only</option>
                        </select>
                    </label>

                    <label className="flex items-center justify-between rounded-2xl border border-slate-200/80 bg-slate-50/70 p-3 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-300">
                        <span>Bật cross-encoder rerank</span>
                        <input type="checkbox" checked={draftUseReranker} onChange={(e) => setDraftUseReranker(e.target.checked)} className="h-4 w-4" />
                    </label>

                    <label className="flex items-center justify-between rounded-2xl border border-slate-200/80 bg-slate-50/70 p-3 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-300">
                        <span>Bật Self-RAG (tự đánh giá)</span>
                        <input type="checkbox" checked={draftUseSelfRag} onChange={(e) => setDraftUseSelfRag(e.target.checked)} className="h-4 w-4" />
                    </label>
                </div>

                <div className="mt-5 flex items-center justify-end gap-2">
                    <button
                        onClick={handleClose}
                        className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                        Hủy bỏ
                    </button>
                    <button
                        onClick={handleApply}
                        disabled={isInvalid}
                        className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-45 dark:bg-sky-500 dark:text-slate-950 dark:hover:bg-sky-400"
                    >
                        Lưu cài đặt
                    </button>
                </div>
            </div>
        </div>
    );
};
