import { useState, useEffect, useCallback } from "react";
import "./styles/index";
import { api, type Context, type StatusResponse } from "./services/api";
import { Sidebar, FileUpload, ChatInterface, SettingsDialog } from "./components";
import type { Message } from "./components/ChatInterface";

interface ChatSessionPayload {
    id: string;
    createdAt: number;
    updatedAt: number;
    messages: Message[];
}

const CHAT_SESSIONS_KEY = "chatSessionsV1";
const ACTIVE_CHAT_SESSION_KEY = "activeChatSessionIdV1";

const createEmptySession = (): ChatSessionPayload => {
    const now = Date.now();
    return {
        id: String(now),
        createdAt: now,
        updatedAt: now,
        messages: [],
    };
};

function App() {
    const [darkMode, setDarkMode] = useState(false);
    const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
    const [status, setStatus] = useState<StatusResponse | null>(null);
    const [isLoadingStatus, setIsLoadingStatus] = useState(true);
    const [isUploading, setIsUploading] = useState(false);
    const [isChatLoading, setIsChatLoading] = useState(false);
    const [documentCount, setDocumentCount] = useState(0);
    const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
    const [chatSessions, setChatSessions] = useState<ChatSessionPayload[]>([]);
    const [activeSessionId, setActiveSessionId] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    const [isSessionReady, setIsSessionReady] = useState(false);
    const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);
    const [chunkSize, setChunkSize] = useState(1000);
    const [chunkOverlap, setChunkOverlap] = useState(100);
    const [retrievalMode, setRetrievalMode] = useState<"vector" | "hybrid">("hybrid");
    const [useReranker, setUseReranker] = useState(true);
    const [useSelfRag, setUseSelfRag] = useState(true);
    const [selectedFilenameFilter, setSelectedFilenameFilter] = useState<string>("all");
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isDocumentDialogOpen, setIsDocumentDialogOpen] = useState(false);
    const [deletingFilename, setDeletingFilename] = useState<string | null>(null);
    const historyLimit = status?.history_max_messages || 7;

    // Load all sessions + active session from sessionStorage
    useEffect(() => {
        const savedSessions = sessionStorage.getItem(CHAT_SESSIONS_KEY);
        let initialSessions: ChatSessionPayload[] = [];

        if (savedSessions) {
            try {
                const parsed = JSON.parse(savedSessions) as ChatSessionPayload[];
                if (Array.isArray(parsed)) {
                    initialSessions = parsed.filter((item) => item && typeof item.id === "string" && Array.isArray(item.messages));
                }
            } catch (e) {
                console.error("Lỗi load danh sách session chat:", e);
            }
        }

        if (initialSessions.length === 0) {
            initialSessions = [createEmptySession()];
        }

        const savedActiveSessionId = sessionStorage.getItem(ACTIVE_CHAT_SESSION_KEY);
        const defaultActiveSessionId = initialSessions[0].id;
        const resolvedActiveSessionId = savedActiveSessionId && initialSessions.some((session) => session.id === savedActiveSessionId) ? savedActiveSessionId : defaultActiveSessionId;

        const activeSession = initialSessions.find((session) => session.id === resolvedActiveSessionId) || initialSessions[0];

        setChatSessions(initialSessions);
        setActiveSessionId(activeSession.id);
        setMessages(activeSession.messages);
        setIsSessionReady(true);
    }, []);

    // Persist all sessions metadata to sessionStorage
    useEffect(() => {
        if (!isSessionReady) return;
        sessionStorage.setItem(CHAT_SESSIONS_KEY, JSON.stringify(chatSessions));
        if (activeSessionId) {
            sessionStorage.setItem(ACTIVE_CHAT_SESSION_KEY, activeSessionId);
        }
    }, [chatSessions, activeSessionId, isSessionReady]);

    // Keep current active session in sync when chat messages change
    useEffect(() => {
        if (!isSessionReady || !activeSessionId) return;
        setChatSessions((prev) =>
            prev.map((session) =>
                session.id === activeSessionId
                    ? {
                          ...session,
                          messages,
                          updatedAt: Date.now(),
                      }
                    : session,
            ),
        );
    }, [messages, activeSessionId, isSessionReady]);

    // Sync dark mode class on <html>
    useEffect(() => {
        const html = document.documentElement;
        if (darkMode) {
            html.classList.add("dark");
        } else {
            html.classList.remove("dark");
        }
    }, [darkMode]);

    useEffect(() => {
        fetchStatus();
    }, []);

    const fetchStatus = async () => {
        setIsLoadingStatus(true);
        try {
            const res = await api.getStatus();
            setStatus(res);
            setDocumentCount(res.document_count || 0);
            if (res.uploaded_files) {
                setUploadedFiles(res.uploaded_files);
            }
            if (res.default_chunk_size) {
                setChunkSize(res.default_chunk_size);
            }
            if (typeof res.default_chunk_overlap === "number") {
                setChunkOverlap(res.default_chunk_overlap);
            }
        } catch (error) {
            console.error("Error fetching status:", error);
        } finally {
            setIsLoadingStatus(false);
        }
    };

    const showNotification = (type: "success" | "error", message: string) => {
        setNotification({ type, message });
        setTimeout(() => setNotification(null), 5000);
    };

    const handleUpload = async (files: File[], options: { chunkSize: number; chunkOverlap: number }) => {
        if (options.chunkOverlap >= options.chunkSize) {
            showNotification("error", "Chunk overlap phải nhỏ hơn chunk size");
            return;
        }

        setIsUploading(true);
        try {
            const res = await api.uploadFiles(files, options);
            if (res.success) {
                showNotification("success", res.message);
                const newFiles = res.processed_files?.map((item) => item.filename) || [res.filename];
                setUploadedFiles((prev) => Array.from(new Set([...prev, ...newFiles])));
                setDocumentCount((prev) => prev + (res.total_chunks_added || res.chunks_added));
                await fetchStatus();
            } else {
                showNotification("error", res.error || "Upload thất bại");
            }
        } catch {
            showNotification("error", "Lỗi kết nối server");
        } finally {
            setIsUploading(false);
        }
    };

    const handleChat = useCallback(async (message: string, history: { role: "user" | "assistant"; content: string }[]): Promise<{ answer: string; contexts: Context[]; standaloneQuestion?: string; isFollowUpRewrite?: boolean; confidenceScore?: number; confidenceLabel?: "low" | "medium" | "high"; retrievalMode?: "vector" | "hybrid"; selfRagApplied?: boolean; rerankerModel?: string | null }> => {
        setIsChatLoading(true);
        try {
            const res = await api.chat(message, history, activeSessionId, {
                retrievalMode,
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
                };
            }
            return { answer: res.error || "Đã xảy ra lỗi", contexts: [] };
        } catch {
            return { answer: "Lỗi kết nối đến server", contexts: [] };
        } finally {
            setIsChatLoading(false);
        }
    }, [activeSessionId, retrievalMode, selectedFilenameFilter, useReranker, useSelfRag]);

    const handleResetSessionContext = async () => {
        if (!activeSessionId) return;
        if (!confirm("Bạn có chắc muốn reset ngữ cảnh của phiên chat hiện tại?")) return;

        try {
            const res = await api.clearSessionMemory(activeSessionId);
            if (!res.success) {
                showNotification("error", res.error || "Reset ngữ cảnh thất bại");
                return;
            }

            setMessages([]);
            setChatSessions((prev) =>
                prev.map((session) =>
                    session.id === activeSessionId
                        ? {
                              ...session,
                              messages: [],
                              updatedAt: Date.now(),
                          }
                        : session,
                ),
            );
            showNotification("success", "Đã reset ngữ cảnh phiên hiện tại");
        } catch {
            showNotification("error", "Lỗi khi reset ngữ cảnh phiên chat");
        }
    };

    const handleClearVectorStore = async () => {
        if (!confirm("Bạn có chắc muốn xóa tất cả tài liệu đã upload?")) return;
        try {
            const res = await api.clearVectorStore();
            if (res.success) {
                showNotification("success", "Đã xóa toàn bộ tài liệu");
                setDocumentCount(0);
                setUploadedFiles([]);
                setSelectedFilenameFilter("all");
                await fetchStatus();
            } else {
                showNotification("error", res.error || "Xóa thất bại");
            }
        } catch {
            showNotification("error", "Lỗi khi xóa dữ liệu");
        }
    };

    const handleDeleteDocument = async (filename: string) => {
        const targetFilename = filename.trim();
        if (!targetFilename) return;

        if (!confirm(`Bạn có chắc muốn xóa tài liệu \"${targetFilename}\"?`)) return;

        setDeletingFilename(targetFilename);
        try {
            const res = await api.deleteDocumentByFilename(targetFilename);
            if (!res.success) {
                showNotification("error", res.error || "Xóa tài liệu thất bại");
                return;
            }

            showNotification("success", res.message || `Đã xóa tài liệu ${targetFilename}`);

            if (selectedFilenameFilter === targetFilename) {
                setSelectedFilenameFilter("all");
            }

            setUploadedFiles(res.uploaded_files || []);
            setDocumentCount(res.document_count || 0);
            await fetchStatus();
        } catch {
            showNotification("error", "Lỗi khi xóa tài liệu");
        } finally {
            setDeletingFilename(null);
        }
    };

    const resetSessionMemories = useCallback(async (sessionIds: string[]): Promise<number> => {
        const uniqueSessionIds = Array.from(new Set(sessionIds.filter(Boolean)));
        if (uniqueSessionIds.length === 0) {
            return 0;
        }

        const results = await Promise.allSettled(uniqueSessionIds.map((sessionId) => api.clearSessionMemory(sessionId)));
        return results.filter((result) => result.status === "rejected").length;
    }, []);

    const handleClearHistory = async () => {
        if (!confirm("Bạn có chắc muốn xóa toàn bộ lịch sử chat?")) return;
        const failedResetCount = await resetSessionMemories(chatSessions.map((session) => session.id));

        const freshSession = createEmptySession();
        setChatSessions([freshSession]);
        setActiveSessionId(freshSession.id);
        setMessages([]);
        sessionStorage.setItem(CHAT_SESSIONS_KEY, JSON.stringify([freshSession]));
        sessionStorage.setItem(ACTIVE_CHAT_SESSION_KEY, freshSession.id);
        if (failedResetCount > 0) {
            showNotification("error", `Đã xóa lịch sử chat, nhưng có ${failedResetCount} session chưa reset được trên backend`);
            return;
        }

        showNotification("success", "Đã xóa lịch sử chat và reset memory backend");
    };

    const handleNewChat = () => {
        const newSession = createEmptySession();
        setChatSessions((prev) => [newSession, ...prev]);
        setActiveSessionId(newSession.id);
        setMessages([]);
        setMobileSidebarOpen(false);
        showNotification("success", "Đã tạo đoạn chat mới");
    };

    const handleSelectSession = (sessionId: string) => {
        const targetSession = chatSessions.find((session) => session.id === sessionId);
        if (!targetSession) return;
        setActiveSessionId(targetSession.id);
        setMessages(targetSession.messages);
        setMobileSidebarOpen(false);
    };

    const handleDeleteSession = async (sessionId: string) => {
        const targetSession = chatSessions.find((session) => session.id === sessionId);
        if (!targetSession) return;

        if (!confirm("Bạn có chắc muốn xóa đoạn chat này?")) return;

        const failedResetCount = await resetSessionMemories([sessionId]);

        const remainingSessions = chatSessions.filter((session) => session.id !== sessionId);

        if (remainingSessions.length === 0) {
            const newSession = createEmptySession();
            setChatSessions([newSession]);
            setActiveSessionId(newSession.id);
            setMessages([]);
            if (failedResetCount > 0) {
                showNotification("error", "Đã xóa đoạn chat, nhưng backend chưa reset memory session này");
                return;
            }

            showNotification("success", "Đã xóa đoạn chat và reset memory backend");
            return;
        }

        setChatSessions(remainingSessions);

        if (activeSessionId === sessionId) {
            const nextSession = remainingSessions[0];
            setActiveSessionId(nextSession.id);
            setMessages(nextSession.messages);
        }

        if (failedResetCount > 0) {
            showNotification("error", "Đã xóa đoạn chat, nhưng backend chưa reset memory session này");
            return;
        }

        showNotification("success", "Đã xóa đoạn chat và reset memory backend");
    };

    return (
        <div className="relative flex h-screen overflow-hidden text-slate-800 transition-colors duration-300 dark:text-slate-200">
            {mobileSidebarOpen && <button onClick={() => setMobileSidebarOpen(false)} className="fixed inset-0 z-30 bg-slate-950/45 backdrop-blur-[2px] lg:hidden" aria-label="Đóng menu" />}

            <Sidebar
                status={status}
                isLoading={isLoadingStatus}
                documentCount={documentCount}
                messages={messages}
                chatSessions={chatSessions}
                activeSessionId={activeSessionId}
                onClearVectorStore={handleClearVectorStore}
                onClearHistory={handleClearHistory}
                onResetSessionContext={handleResetSessionContext}
                onNewChat={handleNewChat}
                onSelectSession={handleSelectSession}
                onDeleteSession={handleDeleteSession}
                isMobileOpen={mobileSidebarOpen}
                onCloseMobile={() => setMobileSidebarOpen(false)}
            />

            <main className="relative flex min-w-0 flex-1 flex-col overflow-hidden p-2 md:p-3 lg:p-4">
                <div className="chat-shell relative z-10 flex min-h-0 flex-1 flex-col overflow-hidden rounded-[28px] shadow-2xl shadow-slate-900/8">
                    <header className="flex items-center justify-between border-b border-slate-200/70 px-3 py-3 dark:border-slate-700/70 md:px-5">
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setMobileSidebarOpen(true)}
                                className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 lg:hidden"
                                title="Mở menu"
                            >
                                <span className="material-icons-round" style={{ fontSize: "20px" }}>
                                    menu
                                </span>
                            </button>
                            <div>
                                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 md:text-lg">Document Chat</h2>
                                <p className="text-xs text-slate-500 dark:text-slate-400">Phong cách kết hợp ChatGPT + Gemini</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="hidden rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 md:inline-flex">
                                {status?.llm_model || "LLM"}
                            </span>
                            <button
                                onClick={() => setIsSettingsOpen(true)}
                                className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:-translate-y-0.5 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                                title="Cài đặt chunk"
                            >
                                <span className="material-icons-round" style={{ fontSize: "20px" }}>
                                    tune
                                </span>
                            </button>
                            <button
                                onClick={() => setDarkMode(!darkMode)}
                                className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:-translate-y-0.5 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                                title="Chuyển đổi giao diện"
                            >
                                <span className="material-icons-round" style={{ fontSize: "20px" }}>
                                    {darkMode ? "light_mode" : "dark_mode"}
                                </span>
                            </button>
                        </div>
                    </header>

                    {notification && (
                        <div className={`fixed right-4 top-4 z-50 flex items-center gap-2 rounded-2xl px-4 py-3 text-sm font-medium text-white shadow-xl animate-fade-in ${notification.type === "success" ? "bg-emerald-500" : "bg-rose-500"}`}>
                            <span className="material-icons-round" style={{ fontSize: "18px" }}>
                                {notification.type === "success" ? "check_circle" : "error"}
                            </span>
                            <p>{notification.message}</p>
                        </div>
                    )}

                    <SettingsDialog
                        isOpen={isSettingsOpen}
                        chunkSize={chunkSize}
                        chunkOverlap={chunkOverlap}
                        retrievalMode={retrievalMode}
                        useReranker={useReranker}
                        useSelfRag={useSelfRag}
                        onClose={() => setIsSettingsOpen(false)}
                        onApply={(settings) => {
                            setChunkSize(settings.chunkSize);
                            setChunkOverlap(settings.chunkOverlap);
                            setRetrievalMode(settings.retrievalMode);
                            setUseReranker(settings.useReranker);
                            setUseSelfRag(settings.useSelfRag);
                            showNotification(
                                "success",
                                `Đã cập nhật: chunk ${settings.chunkSize}/${settings.chunkOverlap}, retrieval ${settings.retrievalMode}, rerank ${settings.useReranker ? "on" : "off"}, self-rag ${settings.useSelfRag ? "on" : "off"}`,
                            );
                        }}
                    />

                    {isDocumentDialogOpen && (
                        <>
                            <button
                                type="button"
                                onClick={() => setIsDocumentDialogOpen(false)}
                                className="fixed inset-0 z-40 bg-slate-950/40 backdrop-blur-[2px]"
                                aria-label="Đóng quản lý tài liệu"
                            />
                            <div className="fixed inset-0 z-50 flex items-center justify-center p-3 md:p-5">
                                <div className="w-full max-w-3xl rounded-3xl border border-slate-200/80 bg-white p-4 shadow-2xl dark:border-slate-700 dark:bg-slate-900 md:p-5">
                                    <div className="flex items-start justify-between gap-3 border-b border-slate-200 pb-3 dark:border-slate-700">
                                        <div>
                                            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500 dark:text-slate-400">Tài liệu</p>
                                            <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Quản lý file đã upload</h3>
                                            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Đang có {uploadedFiles.length} file. Bạn có thể chọn lọc nhanh hoặc xóa từng file tại đây.</p>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={() => setIsDocumentDialogOpen(false)}
                                            className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                                            aria-label="Đóng"
                                        >
                                            <span className="material-icons-round" style={{ fontSize: "18px" }}>
                                                close
                                            </span>
                                        </button>
                                    </div>

                                    <div className="mt-3 flex flex-wrap items-center gap-2">
                                        <button
                                            type="button"
                                            onClick={() => setSelectedFilenameFilter("all")}
                                            className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
                                                selectedFilenameFilter === "all"
                                                    ? "border-sky-300 bg-sky-50 text-sky-700 dark:border-sky-500/60 dark:bg-sky-500/15 dark:text-sky-300"
                                                    : "border-slate-200 bg-white text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                                            }`}
                                        >
                                            Tất cả file
                                        </button>
                                        <FileUpload
                                            onUpload={handleUpload}
                                            isUploading={isUploading}
                                            compact
                                            chunkSize={chunkSize}
                                            chunkOverlap={chunkOverlap}
                                        />
                                    </div>

                                    <div className="mt-3 max-h-[55vh] space-y-2 overflow-y-auto pr-1">
                                        {uploadedFiles.length === 0 ? (
                                            <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-300">
                                                Chưa có tài liệu nào.
                                            </div>
                                        ) : (
                                            uploadedFiles.map((file) => (
                                                <div
                                                    key={file}
                                                    className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
                                                >
                                                    <div className="min-w-0">
                                                        <p className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">{file}</p>
                                                        <p className="text-[11px] text-slate-500 dark:text-slate-400">
                                                            {selectedFilenameFilter === file ? "Đang dùng làm bộ lọc" : "Không lọc theo file này"}
                                                        </p>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            type="button"
                                                            onClick={() => setSelectedFilenameFilter(file)}
                                                            className="rounded-full border border-sky-300/80 bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700 transition hover:bg-sky-100 dark:border-sky-500/50 dark:bg-sky-500/10 dark:text-sky-300 dark:hover:bg-sky-500/20"
                                                        >
                                                            Lọc theo file này
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={() => handleDeleteDocument(file)}
                                                            disabled={deletingFilename === file}
                                                            className="rounded-full border border-rose-300/80 bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-700 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-rose-500/50 dark:bg-rose-500/10 dark:text-rose-300 dark:hover:bg-rose-500/20"
                                                        >
                                                            {deletingFilename === file ? "Đang xóa..." : "Xóa file"}
                                                        </button>
                                                    </div>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            </div>
                        </>
                    )}

                    {documentCount === 0 ? (
                        <div className="flex flex-1 items-center justify-center overflow-y-auto px-4 py-8 md:px-8">
                            <div className="w-full max-w-3xl rounded-[30px] border border-slate-200/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5 dark:border-slate-700/70 dark:bg-slate-900/70 md:p-8">
                                <div className="mb-7 text-center">
                                    <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-br from-sky-500 to-emerald-500 shadow-lg shadow-sky-500/25">
                                        <span className="material-icons-round text-white" style={{ fontSize: "30px" }}>
                                            description
                                        </span>
                                    </div>
                                    <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100 md:text-4xl">Bắt đầu với tài liệu của bạn</h1>
                                    <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 md:text-base">Tải file lên để đặt câu hỏi, tóm tắt hoặc truy xuất thông tin theo ngữ cảnh.</p>
                                </div>

                                <FileUpload
                                    onUpload={handleUpload}
                                    isUploading={isUploading}
                                    chunkSize={chunkSize}
                                    chunkOverlap={chunkOverlap}
                                />

                                <div className="mt-3 flex justify-center">
                                    <button
                                        onClick={() => setIsSettingsOpen(true)}
                                        className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                                    >
                                        <span className="material-icons-round" style={{ fontSize: "14px" }}>
                                            tune
                                        </span>
                                        Cài đặt chunk: {chunkSize}/{chunkOverlap}
                                    </button>
                                </div>

                                <div className="mt-5 flex flex-wrap items-center justify-center gap-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">
                                    <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 dark:border-slate-700 dark:bg-slate-800">PDF</span>
                                    <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 dark:border-slate-700 dark:bg-slate-800">DOC / DOCX</span>
                                    <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 dark:border-slate-700 dark:bg-slate-800">PNG / JPG</span>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <>
                            <div className="border-b border-slate-200/70 px-3 py-3 dark:border-slate-700/70 md:px-6">
                                <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-2">
                                    <div className="flex min-w-0 items-center gap-2">
                                        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">Tài liệu</span>
                                        <span className="truncate rounded-full border border-emerald-300/70 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 dark:border-emerald-500/40 dark:bg-emerald-500/10 dark:text-emerald-300">
                                            {uploadedFiles.length} file đã upload
                                        </span>
                                        {selectedFilenameFilter !== "all" && (
                                            <span className="truncate rounded-full border border-sky-300/70 bg-sky-50 px-3 py-1 text-xs font-medium text-sky-700 dark:border-sky-500/40 dark:bg-sky-500/10 dark:text-sky-300">
                                                Đang lọc: {selectedFilenameFilter}
                                            </span>
                                        )}
                                    </div>

                                    <div className="flex flex-wrap items-center gap-2">
                                        <button
                                            type="button"
                                            onClick={() => setIsDocumentDialogOpen(true)}
                                            className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                                        >
                                            <span className="material-icons-round" style={{ fontSize: "13px" }}>
                                                inventory_2
                                            </span>
                                            Quản lý tài liệu
                                        </button>

                                        <label className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2 py-1 text-[11px] font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                                            <span>Lọc theo file:</span>
                                            <select
                                                value={selectedFilenameFilter}
                                                onChange={(e) => setSelectedFilenameFilter(e.target.value)}
                                                className="max-w-[180px] bg-transparent text-[11px] outline-none"
                                            >
                                                <option value="all">Tất cả</option>
                                                {uploadedFiles.map((file) => (
                                                    <option key={file} value={file}>
                                                        {file}
                                                    </option>
                                                ))}
                                            </select>
                                        </label>

                                        <FileUpload
                                            onUpload={handleUpload}
                                            isUploading={isUploading}
                                            compact
                                            chunkSize={chunkSize}
                                            chunkOverlap={chunkOverlap}
                                        />
                                    </div>
                                </div>
                            </div>

                            <ChatInterface messages={messages} setMessages={setMessages} onSendMessage={handleChat} isLoading={isChatLoading} historyLimit={historyLimit} />
                        </>
                    )}
                </div>
            </main>
        </div>
    );
}

export default App;
