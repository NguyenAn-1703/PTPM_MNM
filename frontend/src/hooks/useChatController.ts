import { useCallback, useState } from "react";
import { api, type Context, type RetrievalMode } from "../services/api";

interface UseChatControllerOptions {
    activeSessionId: string;
    retrievalMode: RetrievalMode;
    topK: number;
    selectedFilenameFilter: string;
    useReranker: boolean;
    useSelfRag: boolean;
}

interface ChatControllerResult {
    answer: string;
    contexts: Context[];
    standaloneQuestion?: string;
    isFollowUpRewrite?: boolean;
    confidenceScore?: number;
    confidenceLabel?: "low" | "medium" | "high";
    retrievalMode?: RetrievalMode;
    selfRagApplied?: boolean;
    rerankerModel?: string | null;
    traceId?: string;
    timingsMs?: {
        retrieve?: number;
        rerank?: number;
        generation?: number;
        evaluation?: number;
        total?: number;
    };
}

export const useChatController = ({ activeSessionId, retrievalMode, topK, selectedFilenameFilter, useReranker, useSelfRag }: UseChatControllerOptions) => {
    const [isChatLoading, setIsChatLoading] = useState(false);

    const handleChat = useCallback(async (
        message: string,
        history: { role: "user" | "assistant"; content: string }[],
        callbacks?: { onToken?: (token: string) => void },
    ): Promise<ChatControllerResult> => {
        setIsChatLoading(true);
        try {
            const streamRes = await api.chatStream(
                message,
                history,
                activeSessionId,
                {
                    retrievalMode,
                    topK,
                    filenames: selectedFilenameFilter !== "all" ? [selectedFilenameFilter] : [],
                    useReranker,
                    useSelfRag,
                },
                {
                    onToken: callbacks?.onToken,
                },
            );

            if (streamRes.success) {
                return {
                    answer: streamRes.answer,
                    contexts: streamRes.contexts,
                    standaloneQuestion: streamRes.standalone_question,
                    isFollowUpRewrite: Boolean(streamRes.rewritten),
                    confidenceScore: streamRes.confidence_score,
                    confidenceLabel: streamRes.confidence_label,
                    retrievalMode: streamRes.retrieval_mode,
                    selfRagApplied: streamRes.self_rag_applied,
                    rerankerModel: streamRes.reranker?.model || null,
                    traceId: streamRes.trace_id,
                    timingsMs: streamRes.timings_ms,
                };
            }

            const res = await api.chat(message, history, activeSessionId, {
                retrievalMode,
                topK,
                filenames: selectedFilenameFilter !== "all" ? [selectedFilenameFilter] : [],
                useReranker,
                useSelfRag,
            });
            if (res.success) {
                return {
                    answer: res.answer,
                    contexts: res.contexts,
                    standaloneQuestion: res.standalone_question,
                    isFollowUpRewrite: Boolean(res.rewritten),
                    confidenceScore: res.confidence_score,
                    confidenceLabel: res.confidence_label,
                    retrievalMode: res.retrieval_mode,
                    selfRagApplied: res.self_rag_applied,
                    rerankerModel: res.reranker?.model || null,
                    traceId: res.trace_id,
                    timingsMs: res.timings_ms,
                };
            }
            return { answer: res.error || "Đã xảy ra lỗi", contexts: [] };
        } catch {
            return { answer: "Lỗi kết nối đến server", contexts: [] };
        } finally {
            setIsChatLoading(false);
        }
    }, [activeSessionId, retrievalMode, selectedFilenameFilter, topK, useReranker, useSelfRag]);

    return {
        isChatLoading,
        handleChat,
    };
};
