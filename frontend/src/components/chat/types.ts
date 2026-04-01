import type { Context } from "../../services/api";

export type MessageRole = "user" | "assistant";

export interface Message {
    id: string;
    role: MessageRole;
    content: string;
    contexts?: Context[];
    standaloneQuestion?: string;
    isFollowUpRewrite?: boolean;
    timestamp: number;
}

export interface ChatHistoryMessage {
    role: MessageRole;
    content: string;
}
