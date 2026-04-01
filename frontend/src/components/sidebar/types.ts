import type { StatusResponse } from "../../services/api";
import type { Message } from "../ChatInterface";

export interface ChatSession {
    id: string;
    createdAt: number;
    updatedAt: number;
    messages: Message[];
}

export interface SidebarProps {
    status: StatusResponse | null;
    isLoading: boolean;
    documentCount: number;
    messages: Message[];
    chatSessions: ChatSession[];
    activeSessionId: string;
    onClearVectorStore: () => void;
    onClearHistory: () => void;
    onNewChat: () => void;
    onSelectSession: (sessionId: string) => void;
    onDeleteSession: (sessionId: string) => void;
    isMobileOpen: boolean;
    onCloseMobile: () => void;
}
