const API_BASE_URL = "http://localhost:8000/api";

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
    retrieval_mode?: "vector" | "hybrid";
    applied_filters?: {
        filenames?: string[];
        file_types?: string[];
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
    error?: string;
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
    ollama_url: string;
    supported_retrieval_modes?: Array<"vector" | "hybrid">;
    cross_encoder_model?: string;
    history_max_messages?: number;
    default_chunk_size?: number;
    default_chunk_overlap?: number;
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
    mode: "vector" | "hybrid" | "hybrid_rerank";
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
            retrievalMode?: "vector" | "hybrid";
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
        retrieval_modes?: Array<"vector" | "hybrid" | "hybrid_rerank">;
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
