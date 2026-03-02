import React, { useState, useRef, useEffect } from 'react';
import type { Context } from '../services/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  contexts?: Context[];
  timestamp: Date;
}

interface ChatHistoryMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatInterfaceProps {
  onSendMessage: (message: string, history: ChatHistoryMessage[]) => Promise<{ answer: string; contexts: Context[] }>;
  isLoading: boolean;
  historyLimit: number;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ onSendMessage, isLoading, historyLimit }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const historyCount = messages.filter((msg) => msg.role === 'user' || msg.role === 'assistant').length;
  const [input, setInput] = useState('');
  const [expandedContext, setExpandedContext] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '48px';
    }

    try {
      const history: ChatHistoryMessage[] = messages
        .filter((msg) => msg.role === 'user' || msg.role === 'assistant')
        .map((msg) => ({ role: msg.role, content: msg.content }))
        .slice(-historyLimit);

      const response = await onSendMessage(userMessage.content, history);
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        contexts: response.contexts,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Đã xảy ra lỗi khi xử lý câu hỏi. Vui lòng thử lại.',
          timestamp: new Date(),
        },
      ]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 128) + 'px';
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth">
        {messages.length === 0 ? (
          <WelcomeMessage />
        ) : (
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                expandedContext={expandedContext}
                onToggleContext={setExpandedContext}
              />
            ))}
            {isLoading && <LoadingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        )}
        {messages.length > 0 && isLoading && <div ref={messagesEndRef} />}
      </div>

      {/* Footer Input */}
      <footer className="flex-shrink-0 p-4 md:p-6 bg-white dark:bg-slate-800 border-t border-gray-200 dark:border-gray-700 z-30">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit}>
            <div className="flex items-center justify-between text-[11px] text-gray-400 dark:text-gray-500 mb-2 px-1">
              <span>
                Số lượng tin nhắn có thể nhớ chính xác : {Math.min(historyCount, historyLimit)}/{historyLimit}
              </span>
            </div>
            <div className="relative flex items-end gap-2 bg-gray-100 dark:bg-slate-900 rounded-2xl p-2 border border-transparent focus-within:border-indigo-500/50 focus-within:ring-2 focus-within:ring-indigo-500/20 transition-all duration-300">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleTextareaInput}
                onKeyDown={handleKeyDown}
                placeholder="Nhập câu hỏi về tài liệu đã upload..."
                rows={1}
                disabled={isLoading}
                className="w-full bg-transparent border-none text-gray-800 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-0 resize-none py-3 px-4 text-base"
                style={{ minHeight: '48px', maxHeight: '128px' }}
              />
              <div className="flex items-center gap-2 pb-1 pr-1 flex-shrink-0">
                {/* <button
                  type="button"
                  className="p-2 text-gray-400 hover:text-indigo-500 dark:text-gray-500 dark:hover:text-indigo-400 transition-colors rounded-full hover:bg-gray-200 dark:hover:bg-slate-700"
                  title="Đính kèm file"
                >
                  <span className="material-icons-round" style={{ fontSize: '20px' }}>attach_file</span>
                </button> */}
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white px-4 py-2 rounded-xl transition-all hover:shadow-lg hover:shadow-indigo-500/30 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none disabled:active:scale-100"
                >
                  <span className="material-icons-round" style={{ fontSize: '16px' }}>send</span>
                  <span className="text-sm font-semibold">Gửi</span>
                </button>
              </div>
            </div>
          </form>
          <p className="text-center text-xs text-gray-400 dark:text-gray-600 mt-2">
            AI có thể mắc lỗi. Hãy kiểm tra thông tin quan trọng.
          </p>
        </div>
      </footer>
    </div>
  );
};

const WelcomeMessage: React.FC = () => (
  <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in-up py-16">
    <div className="w-20 h-20 border border-gray-400 dark:border-gray-600 rounded-3xl flex items-center justify-center mb-6">
      <span className="material-icons-round text-black dark:text-white" style={{ fontSize: '40px' }}>forum</span>
    </div>
    <h2 className="text-3xl font-bold mb-3 bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-400">
      Chào mừng đến RAG Assistant!
    </h2>
    <p className="max-w-md text-gray-500 dark:text-gray-400 text-base leading-relaxed">
      Upload tài liệu (PDF, Word, Ảnh) sau đó đặt câu hỏi để AI trả lời dựa trên nội dung tài liệu của bạn.
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
        <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-white text-sm font-bold ${isUser ? 'bg-indigo-500' : 'bg-gradient-to-br from-emerald-500 to-teal-600'}`}>
            {isUser
              ? <span className="material-icons-round" style={{ fontSize: '16px' }}>person</span>
              : <span className="material-icons-round" style={{ fontSize: '16px' }}>smart_toy</span>
            }
          </div>
          <div className={`px-4 py-3 rounded-2xl ${isUser ? 'bg-indigo-500 text-white rounded-tr-sm' : 'bg-gray-100 dark:bg-slate-800 text-gray-800 dark:text-gray-100 rounded-tl-sm border border-gray-200 dark:border-gray-700'}`}>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
          </div>
        </div>

        {message.contexts && message.contexts.length > 0 && (
          <div className={`mt-3 ${isUser ? 'mr-11' : 'ml-11'}`}>
            <button
              onClick={() => onToggleContext(expandedContext === message.id ? null : message.id)}
              className="text-xs text-indigo-500 dark:text-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-300 flex items-center gap-1 cursor-pointer"
            >
              <span className={`material-icons-round transition-transform ${expandedContext === message.id ? 'rotate-90' : ''}`} style={{ fontSize: '14px' }}>chevron_right</span>
              Xem ngữ cảnh ({message.contexts.length})
            </button>

            {expandedContext === message.id && (
              <div className="mt-2 space-y-2 animate-fade-in">
                {message.contexts.map((ctx, idx) => (
                  <div key={idx} className="p-3 bg-gray-50 dark:bg-slate-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center gap-2 mb-2 text-xs text-gray-500 dark:text-gray-400">
                      <span className="material-icons-round" style={{ fontSize: '12px' }}>description</span>
                      <span>{ctx.metadata.filename || 'Unknown'}</span>
                      <span>•</span>
                      <span>Score: {(1 - ctx.score).toFixed(3)}</span>
                    </div>
                    <p className="text-xs text-gray-600 dark:text-gray-300 line-clamp-4">{ctx.content}</p>
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
        <span className="material-icons-round text-white" style={{ fontSize: '16px' }}>smart_toy</span>
      </div>
      <div className="px-4 py-3 rounded-2xl bg-gray-100 dark:bg-slate-800 rounded-tl-sm border border-gray-200 dark:border-gray-700">
        <div className="flex gap-1 items-center">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
        </div>
      </div>
    </div>
  </div>
);
