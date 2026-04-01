import type { Context } from "../../services/api";

export type MessageRole = "user" | "assistant";

export interface Message {
    id: string;
    role: MessageRole;
    content: string;
    contexts?: Context[];
    timestamp: number;
}

export interface ChatHistoryMessage {
    role: MessageRole;
    content: string;
}
