import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, Bot, User, Send, Plus, Trash2, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import aiApi from '../../api/aiApi';

export default function AIChatPage() {
  const [conversations, setConversations] = useState([]);
  const [currentConvId, setCurrentConvId] = useState(null);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Welcome to the AI Finance Intelligence Console. I have access to your live 3-way reconciliation datasets and policy guidelines. Ask any question about close variances, specific transaction audits, or bank credit status.',
      sources: [],
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeSources, setActiveSources] = useState(null);
  const messagesEndRef = useRef(null);

  const loadConversations = async () => {
    try {
      const res = await aiApi.getConversations();
      if (res?.success) setConversations(res.data || []);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSelectConversation = async (convId) => {
    try {
      setCurrentConvId(convId);
      setLoading(true);
      const res = await aiApi.getConversationMessages(convId);
      if (res?.success) {
        const loadedMessages = (res.data || []).map((m) => ({
          role: m.role,
          content: m.content,
          sources: m.sources ? (typeof m.sources === 'string' ? JSON.parse(m.sources) : m.sources) : [],
        }));
        setMessages(loadedMessages);
      }
    } catch (err) {
      console.error('Failed to load conversation messages:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleNewConversation = () => {
    setCurrentConvId(null);
    setMessages([
      {
        role: 'assistant',
        content: 'New audit thread created. What would you like to investigate?',
        sources: [],
      },
    ]);
  };

  const handleDeleteConversation = async (e, convId) => {
    e.stopPropagation();
    try {
      await aiApi.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.conversation_id !== convId));
      if (currentConvId === convId) handleNewConversation();
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!inputQuery.trim() || loading) return;

    const userText = inputQuery.trim();
    setInputQuery('');
    setMessages((prev) => [...prev, { role: 'user', content: userText }]);
    setLoading(true);

    try {
      const res = await aiApi.chat({
        query: userText,
        conversation_id: currentConvId,
      });

      if (res?.success) {
        if (!currentConvId && res.conversation_id) {
          setCurrentConvId(res.conversation_id);
          loadConversations();
        }
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
            content: res?.answer || 'Failed to complete analysis.',
            sources: [],
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${err.message || 'AI processing failure.'}`,
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex gap-4">
      {/* Left Conversations Sidebar */}
      <div className="w-72 bg-white rounded-xl border border-slate-200/80 shadow-sm flex flex-col overflow-hidden shrink-0 hidden md:flex">
        <div className="p-3 border-b border-slate-100 flex items-center justify-between">
          <span className="text-xs font-bold font-outfit text-navy uppercase tracking-wider">
            Audit Threads
          </span>
          <button
            onClick={handleNewConversation}
            className="p-1 text-primary hover:bg-primary/10 rounded-md transition-colors"
            title="New Conversation"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-slate-100 p-2 space-y-1">
          {conversations.length === 0 ? (
            <p className="p-4 text-xs text-slate-400 text-center">No previous threads.</p>
          ) : (
            conversations.map((c) => (
              <div
                key={c.conversation_id}
                onClick={() => handleSelectConversation(c.conversation_id)}
                className={`p-2.5 rounded-lg text-xs cursor-pointer flex items-center justify-between group transition-colors ${
                  currentConvId === c.conversation_id
                    ? 'bg-primary/10 text-primary font-semibold'
                    : 'text-slate-700 hover:bg-slate-50'
                }`}
              >
                <span className="truncate pr-2">{c.title || 'Conversation'}</span>
                <button
                  onClick={(e) => handleDeleteConversation(e, c.conversation_id)}
                  className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-600 p-1 rounded transition-opacity"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Stream Container */}
      <div className="flex-1 bg-white rounded-xl border border-slate-200/80 shadow-sm flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/20 text-primary flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold font-outfit text-navy">
                Autonomous Financial Intelligence Console
              </h3>
              <p className="text-xs text-slate-500">Gemini 2.0 Flash + pgvector Grounded RAG</p>
            </div>
          </div>
          <button
            onClick={handleNewConversation}
            className="text-xs font-semibold text-primary hover:underline md:hidden"
          >
            New Thread
          </button>
        </div>

        {/* Message Stream */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4 text-xs bg-slate-50/30">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 rounded-lg bg-primary text-white flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
                  <Bot className="w-4 h-4" />
                </div>
              )}
              <div
                className={`max-w-2xl rounded-xl p-4 ${
                  msg.role === 'user'
                    ? 'bg-primary text-white rounded-br-none shadow-sm'
                    : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-xs'
                }`}
              >
                <div className="whitespace-pre-wrap leading-relaxed text-xs">{msg.content}</div>

                {/* Grounded Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-slate-100">
                    <button
                      onClick={() => setActiveSources(activeSources === idx ? null : idx)}
                      className="flex items-center gap-1.5 text-[11px] font-semibold text-primary hover:underline"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      <span>{msg.sources.length} Grounded Context Sources</span>
                      {activeSources === idx ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </button>

                    {activeSources === idx && (
                      <div className="mt-2 space-y-1.5 pl-3 border-l-2 border-primary/30">
                        {msg.sources.map((src, sIdx) => (
                          <div key={sIdx} className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                            <p className="font-semibold text-slate-800 text-[11px]">
                              {src.file_name} (Chunk #{src.chunk_index})
                            </p>
                            <p className="text-slate-600 font-mono text-[10px] mt-0.5 line-clamp-2">
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
                <div className="w-7 h-7 rounded-lg bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="flex gap-3 items-center text-xs text-slate-400">
              <div className="w-7 h-7 rounded-lg bg-primary text-white flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4" />
              </div>
              <div className="p-3.5 bg-white border border-slate-200 rounded-xl flex items-center gap-2">
                <div className="w-2 h-2 bg-primary rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:0.2s]" />
                <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:0.4s]" />
                <span>Auditing transactions and policy documents...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Query Input */}
        <form onSubmit={handleSend} className="p-4 bg-white border-t border-slate-200 flex items-center gap-3">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask question regarding settlements, discrepancies, or policy guidelines..."
            className="flex-1 text-xs px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-slate-800"
          />
          <button
            type="submit"
            disabled={loading || !inputQuery.trim()}
            className="px-4 py-2.5 bg-primary hover:bg-primary-dark text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            <span>Send</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
}
