const API_BASE_URL = "http://localhost:8000/api";

export type RetrievalMode = "vector" | "hybrid" | "hybrid_multivector";

export interface UploadResponse {
    success: boolean;
    message: string;
    filename: string;
    file_type: string;
    text_length: number;
    chunks_added: number;
    total_files?: number;
    total_chunks_added?: number;
    processed_files?: Array<{
        filename: string;
        file_type: string;
        text_length: number;
        chunks_added: number;
    }>;
    chunk_size?: number;
    chunk_overlap?: number;
    error?: string;
}

export interface Context {
    content: string;
    metadata: {
        filename?: string;
        file_type?: string;
        chunk_index?: number;
        total_chunks?: number;
        page_number?: number;
        char_start?: number;
        char_end?: number;
    };
    source_location?: {
        page_start?: number;
        page_end?: number;
        char_start?: number;
        char_end?: number;
    };
    highlights?: Array<{
        text: string;
        start: number;
        end: number;
    }>;
    score: number;
}

export interface ChatHistoryMessage {
    role: "user" | "assistant";
    content: string;
}

export interface ChatResponse {
    success: boolean;
    question: string;
    answer: string;
    contexts: Context[];
    has_context: boolean;
    session_id?: string;
    standalone_question?: string;
    rewritten?: boolean;
    retrieval_mode?: RetrievalMode;
    applied_filters?: {
        filenames?: string[];
        file_types?: string[];
        tags?: string[];
        page_from?: number | null;
        page_to?: number | null;
        uploaded_after?: string | null;
        uploaded_before?: string | null;
    };
    reranker?: {
        used: boolean;
        model?: string | null;
    };
    self_rag_applied?: boolean;
    confidence_score?: number;
    confidence_label?: "low" | "medium" | "high";
    self_check?: {
        supported?: boolean;
        confidence?: number;
        feedback?: string;
    };
    trace_id?: string;
    timings_ms?: {
        retrieve?: number;
        rerank?: number;
        generation?: number;
        evaluation?: number;
        total?: number;
    };
    error?: string;
}

export interface ChatStreamMeta {
    trace_id?: string;
    session_id?: string;
    standalone_question?: string;
    rewritten?: boolean;
    retrieval_mode?: RetrievalMode;
    reranker?: {
        used?: boolean;
        model?: string | null;
    };
    timings_ms?: {
        retrieve?: number;
        rerank?: number;
    };
}

export interface ChatStreamHandlers {
    onMeta?: (meta: ChatStreamMeta) => void;
    onToken?: (token: string) => void;
    onDone?: (result: ChatResponse) => void;
}

export interface ClearSessionMemoryResponse {
    success: boolean;
    session_id: string;
    cleared: boolean;
    message: string;
    error?: string;
}

export interface DeleteDocumentResponse {
    success: boolean;
    message?: string;
    filename?: string;
    removed_chunks?: number;
    removed_source_documents?: number;
    removed_qdrant_points?: number;
    document_count?: number;
    uploaded_files?: string[];
    error?: string;
}

export interface StatusResponse {
    success: boolean;
    status: string;
    llm_model: string;
    embedding_model: string;
    vector_db: string;
    vector_backend?: "faiss" | "qdrant";
    ollama_url: string;
    supported_retrieval_modes?: RetrievalMode[];
    cross_encoder_model?: string;
    history_max_messages?: number;
    default_chunk_size?: number;
    default_chunk_overlap?: number;
    chunking_strategy?: "fixed" | "recursive" | "semantic";
    multi_vector_enabled?: boolean;
    context_reorder_enabled?: boolean;
    context_compression_enabled?: boolean;
    self_rag_confidence_threshold?: number;
    qdrant_dual_write_enabled?: boolean;
    qdrant_shadow_read_enabled?: boolean;
    qdrant_point_count?: number;
    has_documents: boolean;
    document_count: number;
    source_document_count?: number;
    uploaded_files?: string[];
    error?: string;
}

export interface EvaluationCase {
    question: string;
    expected_keywords: string[];
}

export interface ChunkStrategyQuestionResult {
    question: string;
    expected_keywords: string[];
    retrieved_contexts: number;
    hit: boolean;
}

export interface ChunkStrategyReportItem {
    chunk_size: number;
    chunk_overlap: number;
    retrieval_accuracy: number;
    hits: number;
    total_questions: number;
    generated_chunks: number;
    details: ChunkStrategyQuestionResult[];
}

export interface ChunkStrategyEvaluationResponse {
    success: boolean;
    chunk_sizes: number[];
    chunk_overlaps: number[];
    top_k: number;
    summary: {
        source_documents: number;
        evaluated_configs: number;
        metric: string;
    };
    best_config: ChunkStrategyReportItem | null;
    reports: ChunkStrategyReportItem[];
    error?: string;
}

export interface RetrievalBenchmarkDetail {
    question: string;
    expected_keywords: string[];
    hit: boolean;
    latency_ms: number;
    retrieved_contexts: number;
    reranker_used: boolean;
}

export interface RetrievalBenchmarkModeReport {
    mode: "vector" | "hybrid" | "hybrid_rerank" | "hybrid_multivector";
    retrieval_accuracy: number;
    hits: number;
    total_questions: number;
    avg_latency_ms: number;
    details: RetrievalBenchmarkDetail[];
}

export interface RetrievalBenchmarkResponse {
    success: boolean;
    top_k: number;
    retrieval_modes: string[];
    applied_filters: {
        filenames: string[];
        file_types: string[];
        tags?: string[];
        page_from?: number | null;
        page_to?: number | null;
        uploaded_after?: string | null;
        uploaded_before?: string | null;
    };
    summary: {
        metric: string;
        question_count: number;
        evaluated_modes: number;
        top_k: number;
    };
    best_mode: RetrievalBenchmarkModeReport | null;
    reports: RetrievalBenchmarkModeReport[];
    error?: string;
}

export const api = {
    async uploadFiles(files: File[], options?: { chunkSize?: number; chunkOverlap?: number }): Promise<UploadResponse> {
        const formData = new FormData();
        files.forEach((file) => formData.append("files", file));
        if (options?.chunkSize) {
            formData.append("chunk_size", String(options.chunkSize));
        }
        if (typeof options?.chunkOverlap === "number") {
            formData.append("chunk_overlap", String(options.chunkOverlap));
        }

        const response = await fetch(`${API_BASE_URL}/upload/`, {
            method: "POST",
            body: formData,
        });

        return response.json();
    },

    async uploadFile(file: File, options?: { chunkSize?: number; chunkOverlap?: number }): Promise<UploadResponse> {
        return this.uploadFiles([file], options);
    },

    async chat(
        question: string,
        history: ChatHistoryMessage[] = [],
        sessionId?: string,
        options?: {
            retrievalMode?: RetrievalMode;
            filenames?: string[];
            fileTypes?: string[];
            useReranker?: boolean;
            useSelfRag?: boolean;
        },
    ): Promise<ChatResponse> {
        const response = await fetch(`${API_BASE_URL}/chat/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                question,
                history,
                session_id: sessionId,
                retrieval_mode: options?.retrievalMode || "hybrid",
                filenames: options?.filenames || [],
                file_types: options?.fileTypes || [],
                use_reranker: options?.useReranker ?? true,
                use_self_rag: options?.useSelfRag ?? true,
            }),
        });

        return response.json();
    },

    async chatStream(
        question: string,
        history: ChatHistoryMessage[] = [],
        sessionId?: string,
        options?: {
            retrievalMode?: RetrievalMode;
            filenames?: string[];
            fileTypes?: string[];
            useReranker?: boolean;
            useSelfRag?: boolean;
        },
        handlers?: ChatStreamHandlers,
    ): Promise<ChatResponse> {
        const response = await fetch(`${API_BASE_URL}/chat/stream/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "text/event-stream",
            },
            body: JSON.stringify({
                question,
                history,
                session_id: sessionId,
                retrieval_mode: options?.retrievalMode || "hybrid",
                filenames: options?.filenames || [],
                file_types: options?.fileTypes || [],
                use_reranker: options?.useReranker ?? true,
                use_self_rag: options?.useSelfRag ?? true,
            }),
        });

        if (!response.ok) {
            const payload = (await response.json()) as ChatResponse;
            throw new Error(payload.error || "Streaming request failed");
        }

        const reader = response.body?.getReader();
        if (!reader) {
            throw new Error("Streaming body không khả dụng");
        }

        const decoder = new TextDecoder("utf-8");
        let buffer = "";
        let doneResult: ChatResponse | null = null;

        const processEventBlock = (block: string) => {
            const lines = block.split("\n");
            let eventName = "message";
            const dataLines: string[] = [];

            lines.forEach((line) => {
                if (line.startsWith("event:")) {
                    eventName = line.slice(6).trim();
                    return;
                }
                if (line.startsWith("data:")) {
                    dataLines.push(line.slice(5).trim());
                }
            });

            if (dataLines.length === 0) {
                return;
            }

            let payload: ChatResponse | ChatStreamMeta | { token?: string; error?: string } = {};
            try {
                payload = JSON.parse(dataLines.join("\n")) as typeof payload;
            } catch {
                payload = {};
            }

            if (eventName === "meta") {
                handlers?.onMeta?.(payload as ChatStreamMeta);
                return;
            }

            if (eventName === "token") {
                const token = String((payload as { token?: string }).token || "");
                if (token) {
                    handlers?.onToken?.(token);
                }
                return;
            }

            if (eventName === "error") {
                throw new Error(String((payload as { error?: string }).error || "Streaming error"));
            }

            if (eventName === "done") {
                doneResult = {
                    success: true,
                    question,
                    answer: String((payload as ChatResponse).answer || ""),
                    contexts: (payload as ChatResponse).contexts || [],
                    has_context: Boolean((payload as ChatResponse).has_context),
                    session_id: (payload as ChatResponse).session_id,
                    standalone_question: (payload as ChatResponse).standalone_question,
                    rewritten: (payload as ChatResponse).rewritten,
                    retrieval_mode: (payload as ChatResponse).retrieval_mode,
                    applied_filters: (payload as ChatResponse).applied_filters,
                    reranker: (payload as ChatResponse).reranker,
                    self_rag_applied: (payload as ChatResponse).self_rag_applied,
                    confidence_score: (payload as ChatResponse).confidence_score,
                    confidence_label: (payload as ChatResponse).confidence_label,
                    self_check: (payload as ChatResponse).self_check,
                    trace_id: (payload as ChatResponse).trace_id,
                    timings_ms: (payload as ChatResponse).timings_ms,
                };
                handlers?.onDone?.(doneResult);
            }
        };

        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }

            buffer += decoder.decode(value, { stream: true });
            const chunks = buffer.split("\n\n");
            buffer = chunks.pop() || "";

            chunks.forEach((block) => {
                if (!block.trim()) {
                    return;
                }
                processEventBlock(block.trim());
            });
        }

        if (buffer.trim()) {
            processEventBlock(buffer.trim());
        }

        if (!doneResult) {
            throw new Error("Không nhận được event done từ server");
        }

        return doneResult;
    },

    async getStatus(): Promise<StatusResponse> {
        const response = await fetch(`${API_BASE_URL}/status/`);
        return response.json();
    },

    async clearVectorStore(): Promise<{ success: boolean; message?: string; error?: string }> {
        const response = await fetch(`${API_BASE_URL}/clear/`, {
            method: "DELETE",
        });
        return response.json();
    },

    async deleteDocumentByFilename(filename: string): Promise<DeleteDocumentResponse> {
        const response = await fetch(`${API_BASE_URL}/documents/delete/`, {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ filename }),
        });

        return response.json();
    },

    async clearSessionMemory(sessionId: string): Promise<ClearSessionMemoryResponse> {
        const response = await fetch(`${API_BASE_URL}/chat/memory/clear/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ session_id: sessionId }),
        });

        return response.json();
    },

    async evaluateChunkStrategy(payload: {
        evaluation_set: EvaluationCase[];
        chunk_sizes?: number[];
        chunk_overlaps?: number[];
        top_k?: number;
    }): Promise<ChunkStrategyEvaluationResponse> {
        const response = await fetch(`${API_BASE_URL}/chunk-strategy/evaluate/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });
        return response.json();
    },

    async benchmarkRetrieval(payload: {
        evaluation_set: EvaluationCase[];
        top_k?: number;
        retrieval_modes?: Array<"vector" | "hybrid" | "hybrid_rerank" | "hybrid_multivector">;
        filenames?: string[];
        file_types?: string[];
    }): Promise<RetrievalBenchmarkResponse> {
        const response = await fetch(`${API_BASE_URL}/retrieval/benchmark/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });
        return response.json();
    },
};
