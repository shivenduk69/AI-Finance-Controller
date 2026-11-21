import React, { useState, useRef, useEffect } from 'react';
import { Sparkles, X, Send, Bot, User, ChevronDown, ChevronUp, RefreshCw, FileText } from 'lucide-react';
import aiApi from '../../api/aiApi';

export default function FloatingAIAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I am your AI Finance Controller. Ask me anything about reconciliation math, fee calculations, bank deposit discrepancies, or policy guidelines.',
      sources: [],
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeSources, setActiveSources] = useState(null);
  const messagesEndRef = useRef(null);

  const quickPrompts = [
    'Generate close summary',
    'Audit pay_95822412',
    'Explain bank mismatch 10-08-2026',
    'Check missing order ID rule',
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSend = async (queryText) => {
    const query = queryText || inputQuery;
    if (!query.trim() || loading) return;

    const userMessage = { role: 'user', content: query.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInputQuery('');
    setLoading(true);

    try {
      const res = await aiApi.chat({ query: query.trim() });
      if (res && res.success) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: res.answer,
            sources: res.sources || [],
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: res?.answer || 'Failed to generate financial analysis. Please try again.',
            sources: [],
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${err.message || 'AI service unavailable.'}`,
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleResetThread = () => {
    setMessages([
      {
        role: 'assistant',
        content: 'New conversation started. How can I assist with your financial close audit today?',
        sources: [],
      },
    ]);
  };

  return (
    <>
      {/* Floating Toggle Pill */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-40 flex items-center gap-2.5 px-4 py-3 bg-gradient-to-r from-primary to-primary-light text-white rounded-full shadow-xl hover:shadow-2xl hover:scale-105 transition-all text-xs font-semibold font-outfit uppercase tracking-wider"
        >
          <Sparkles className="w-4 h-4 animate-spin-slow" />
          <span>Ask AI Assistant</span>
        </button>
      )}

      {/* Slide-out Floating Popover */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-96 sm:w-[420px] h-[580px] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-5 duration-200">
          {/* Header */}
          <div className="px-4 py-3 bg-sidebar text-white flex items-center justify-between border-b border-sidebar-border">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-primary/40 flex items-center justify-center text-primary-subtle border border-primary/50">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-xs font-bold font-outfit uppercase tracking-wide">
                  AI Finance Controller
                </h3>
                <p className="text-[10px] text-slate-400">Gemini RAG & Invariant Auditor</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={handleResetThread}
                title="Restart Thread"
                className="p-1.5 text-slate-400 hover:text-white rounded-md hover:bg-sidebar-hover transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-slate-400 hover:text-white rounded-md hover:bg-sidebar-hover transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Quick Prompts Bar */}
          <div className="p-2.5 bg-slate-50 border-b border-slate-100 flex gap-1.5 overflow-x-auto text-[11px] no-scrollbar">
            {quickPrompts.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(prompt)}
                disabled={loading}
                className="px-2.5 py-1 bg-white border border-slate-200 rounded-full text-slate-700 hover:border-primary hover:text-primary transition-all whitespace-nowrap shadow-xs disabled:opacity-50"
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Message Stream */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3.5 bg-slate-50/30 text-xs">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-6 h-6 rounded-md bg-primary text-white flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-3.5 h-3.5" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-xl p-3 ${
                    msg.role === 'user'
                      ? 'bg-primary text-white rounded-br-none'
                      : 'bg-white border border-slate-200/90 text-slate-800 rounded-bl-none shadow-xs'
                  }`}
                >
                  <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>

                  {/* RAG Sources Accordion */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2.5 pt-2 border-t border-slate-100 text-[11px]">
                      <button
                        onClick={() =>
                          setActiveSources(activeSources === idx ? null : idx)
                        }
                        className="flex items-center gap-1 text-primary font-semibold hover:underline"
                      >
                        <FileText className="w-3 h-3" />
                        <span>{msg.sources.length} Grounded Document Sources</span>
                        {activeSources === idx ? (
                          <ChevronUp className="w-3 h-3" />
                        ) : (
                          <ChevronDown className="w-3 h-3" />
                        )}
                      </button>

                      {activeSources === idx && (
                        <div className="mt-2 space-y-1.5 pl-2 border-l-2 border-primary/30">
                          {msg.sources.map((src, sIdx) => (
                            <div key={sIdx} className="bg-slate-50 p-2 rounded border border-slate-200/80">
                              <p className="font-semibold text-slate-700">
                                {src.file_name} (Chunk #{src.chunk_index})
                              </p>
                              <p className="text-slate-500 line-clamp-2 mt-0.5 font-mono text-[10px]">
                                {src.text_content}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="w-6 h-6 rounded-md bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                    <User className="w-3.5 h-3.5" />
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex gap-2.5 items-center text-xs text-slate-400">
                <div className="w-6 h-6 rounded-md bg-primary text-white flex items-center justify-center shrink-0">
                  <Bot className="w-3.5 h-3.5" />
                </div>
                <div className="p-3 bg-white border border-slate-200 rounded-xl flex items-center gap-2">
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:0.2s]" />
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:0.4s]" />
                  <span>Auditing financial datasets...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Box */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="p-3 bg-white border-t border-slate-200 flex items-center gap-2"
          >
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask financial question, transaction ID, or date..."
              className="flex-1 text-xs px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-slate-800"
            />
            <button
              type="submit"
              disabled={loading || !inputQuery.trim()}
              className="p-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors disabled:opacity-40"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
