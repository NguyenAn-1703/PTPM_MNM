const API_BASE_URL = 'http://localhost:8000/api';

export interface UploadResponse {
  success: boolean;
  message: string;
  filename: string;
  file_type: string;
  text_length: number;
  chunks_added: number;
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
  has_documents: boolean;
  document_count: number;
  error?: string;
}

export const api = {
  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/upload/`, {
      method: 'POST',
      body: formData,
    });

    return response.json();
  },

  async chat(question: string): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/chat/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
    });

    return response.json();
  },

  async getStatus(): Promise<StatusResponse> {
    const response = await fetch(`${API_BASE_URL}/status/`);
    return response.json();
  },

  async clearVectorStore(): Promise<{ success: boolean; message?: string; error?: string }> {
    const response = await fetch(`${API_BASE_URL}/clear/`, {
      method: 'DELETE',
    });
    return response.json();
  },
};
