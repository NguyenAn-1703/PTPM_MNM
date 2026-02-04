import React, { useState, useRef, useEffect } from 'react';
import type { Context } from '../services/api';


interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  contexts?: Context[];
  timestamp: Date;
}

interface ChatInterfaceProps {
  onSendMessage: (message: string) => Promise<{ answer: string; contexts: Context[] }>;
  isLoading: boolean;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ onSendMessage, isLoading }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [expandedContext, setExpandedContext] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');

    try {
      const response = await onSendMessage(input.trim());
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        contexts: response.contexts,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Đã xảy ra lỗi khi xử lý câu hỏi. Vui lòng thử lại.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <WelcomeMessage />
        ) : (
          messages.map(message => (
            <MessageBubble 
              key={message.id} 
              message={message} 
              expandedContext={expandedContext}
              onToggleContext={setExpandedContext}
            />
          ))
        )}
        
        {isLoading && <LoadingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-slate-700/50">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Nhập câu hỏi về tài liệu đã upload..."
            className="flex-1 input-field"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="btn-primary flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            Gửi
          </button>
        </div>
      </form>
    </div>
  );
};

const WelcomeMessage: React.FC = () => (
  <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in">
    <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-6">
      <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
      </svg>
    </div>
    <h2 className="text-2xl font-bold text-white mb-2">Chào mừng đến RAG Assistant!</h2>
    <p className="text-slate-400 max-w-md">
      Upload tài liệu (PDF, Word, Ảnh) sau đó đặt câu hỏi để AI trả lời dựa trên nội dung tài liệu.
    </p>
  </div>
);

interface MessageBubbleProps {
  message: Message;
  expandedContext: string | null;
  onToggleContext: (id: string | null) => void;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, expandedContext, onToggleContext }) => {
  const isUser = message.role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      <div className={`max-w-3xl ${isUser ? 'order-2' : 'order-1'}`}>
        {/* Avatar */}
        <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
          <div className={`
            w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
            ${isUser ? 'bg-indigo-500' : 'bg-gradient-to-br from-emerald-500 to-teal-600'}
          `}>
            {isUser ? '👤' : '🤖'}
          </div>
          
          <div className={`
            px-4 py-3 rounded-2xl
            ${isUser 
              ? 'bg-indigo-500 text-white rounded-tr-sm' 
              : 'bg-slate-800 text-slate-100 rounded-tl-sm'
            }
          `}>
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>
        </div>

        {/* Retrieved Context */}
        {message.contexts && message.contexts.length > 0 && (
          <div className="mt-3 ml-11">
            <button
              onClick={() => onToggleContext(expandedContext === message.id ? null : message.id)}
              className="text-sm text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
            >
              <svg className={`w-4 h-4 transition-transform ${expandedContext === message.id ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              View Retrieved Context ({message.contexts.length})
            </button>
            
            {expandedContext === message.id && (
              <div className="mt-2 space-y-2 animate-fade-in">
                {message.contexts.map((ctx, idx) => (
                  <div key={idx} className="p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
                    <div className="flex items-center gap-2 mb-2 text-xs text-slate-400">
                      <span>📄 {ctx.metadata.filename || 'Unknown'}</span>
                      <span>•</span>
                      <span>Score: {(1 - ctx.score).toFixed(3)}</span>
                    </div>
                    <p className="text-sm text-slate-300 line-clamp-4">{ctx.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const LoadingIndicator: React.FC = () => (
  <div className="flex justify-start animate-fade-in">
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
        🤖
      </div>
      <div className="px-4 py-3 rounded-2xl bg-slate-800 rounded-tl-sm">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-slate-400 rounded-full animate-pulse" style={{ animationDelay: '0ms' }}></span>
          <span className="w-2 h-2 bg-slate-400 rounded-full animate-pulse" style={{ animationDelay: '150ms' }}></span>
          <span className="w-2 h-2 bg-slate-400 rounded-full animate-pulse" style={{ animationDelay: '300ms' }}></span>
        </div>
      </div>
    </div>
  </div>
);
