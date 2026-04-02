import type { Context } from "../../services/api";

export type MessageRole = "user" | "assistant";

export interface Message {
    id: string;
    role: MessageRole;
    content: string;
    contexts?: Context[];
    standaloneQuestion?: string;
    isFollowUpRewrite?: boolean;
    confidenceScore?: number;
    confidenceLabel?: "low" | "medium" | "high";
    retrievalMode?: "vector" | "hybrid" | "hybrid_multivector";
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
    isStreaming?: boolean;
    timestamp: number;
}

export interface ChatHistoryMessage {
    role: MessageRole;
    content: string;
}
