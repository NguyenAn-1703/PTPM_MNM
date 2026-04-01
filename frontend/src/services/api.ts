const API_BASE_URL = "http://localhost:8000/api";

export interface UploadResponse {
    success: boolean;
    message: string;
    filename: string;
    file_type: string;
    text_length: number;
    chunks_added: number;
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
    };
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
    error?: string;
}

export interface StatusResponse {
    success: boolean;
    status: string;
    llm_model: string;
    embedding_model: string;
    vector_db: string;
    ollama_url: string;
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

export const api = {
    async uploadFile(file: File, options?: { chunkSize?: number; chunkOverlap?: number }): Promise<UploadResponse> {
        const formData = new FormData();
        formData.append("file", file);
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

    async chat(question: string, history: ChatHistoryMessage[] = []): Promise<ChatResponse> {
        const response = await fetch(`${API_BASE_URL}/chat/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ question, history }),
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
};
