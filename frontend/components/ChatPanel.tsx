"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Bot, User, MessageSquare, Calculator } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/types";

interface Props {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  loading: boolean;
  placeholder?: string;
  suggestions?: { label: string; text: string }[];
}

const DEFAULT_SUGGESTIONS = [
  { label: "Bürogebäude, 5.000m², 3 Etagen, 2 Aufzüge, TG 15 Wallboxen", text: "Bürogebäude, 5.000m², 3 Etagen, 2 Aufzüge, Tiefgarage mit 15 Wallboxen" },
  { label: "Krankenhaus, 20.000m², 8 Etagen, 5 Aufzüge, NEA", text: "Krankenhaus, 20.000m², 8 Etagen, 5 Aufzüge, Notstromaggregat, RLT-Anlage" },
];

export default function ChatPanel({ messages, onSend, loading, placeholder, suggestions }: Props) {
  const activeSuggestions = suggestions ?? DEFAULT_SUGGESTIONS;
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!loading) inputRef.current?.focus();
  }, [loading]);

  const handleSubmit = () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    onSend(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-blue-100 to-blue-50 flex items-center justify-center">
              <Calculator className="w-8 h-8 text-[#0046ad]" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-2">
              Wie kann ich Ihnen helfen?
            </h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto mb-4">
              Beschreiben Sie Ihr Gebäude und ich berechne die Prüfkosten
              für Elektro- und Gebäudetechnik.
            </p>
            <div className="flex flex-col items-center gap-2">
              {activeSuggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(s.text); inputRef.current?.focus(); }}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-blue-50 hover:border-blue-300 hover:text-blue-800 transition-all shadow-sm"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              "flex gap-4 animate-fade-in",
              msg.role === "user" ? "flex-row-reverse" : ""
            )}
          >
            {msg.role === "status" ? (
              <div className="w-full flex justify-center">
                <div className="flex items-center gap-2 px-3.5 py-2 text-xs text-[#0046ad] bg-blue-50 rounded-lg border border-blue-200/60 shadow-sm">
                  <span className="inline-block w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  <span className="font-medium">{msg.content}</span>
                </div>
              </div>
            ) : (
              <>
                {/* Avatar */}
                <div
                  className={cn(
                    "flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center",
                    msg.role === "user"
                      ? "bg-gradient-to-br from-[#0046ad] to-[#003890]"
                      : "bg-gradient-to-br from-slate-100 to-slate-200"
                  )}
                >
                  {msg.role === "user" ? (
                    <User className="w-4 h-4 text-white" />
                  ) : (
                    <Bot className="w-4 h-4 text-slate-600" />
                  )}
                </div>

                {/* Message Content */}
                <div
                  className={cn(
                    "flex-1 max-w-[85%]",
                    msg.role === "user" ? "flex justify-end" : ""
                  )}
                >
                  <div
                    className={cn(
                      "px-4 py-3 text-[13.5px] leading-relaxed rounded-2xl",
                      msg.role === "user"
                        ? "bg-[#0046ad] text-white rounded-tr-md"
                        : "bg-slate-50 border border-slate-200/60 text-slate-700 rounded-tl-md"
                    )}
                  >
                    {msg.role === "assistant" ? (
                      <span
                        dangerouslySetInnerHTML={{
                          __html: msg.content
                            .replace(/\*\*(.*?)\*\*/g, "<strong class='font-semibold text-slate-900'>$1</strong>")
                            .replace(/\*(.*?)\*/g, "<em>$1</em>")
                            .replace(/\n/g, "<br/>"),
                        }}
                      />
                    ) : (
                      msg.content
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        ))}

        {loading && messages[messages.length - 1]?.role !== "status" && (
          <div className="flex gap-4 animate-fade-in">
            <div className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200">
              <Bot className="w-4 h-4 text-slate-600" />
            </div>
            <div className="bg-slate-50 border border-slate-200/60 rounded-2xl rounded-tl-md px-4 py-3">
              <span className="inline-flex gap-1">
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-100 bg-slate-50/50">
        <div className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder ?? "Beschreiben Sie Ihr Gebäude..."}
            rows={1}
            className="flex-1 px-4 py-3 text-sm bg-white border border-slate-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 placeholder:text-slate-400"
            disabled={loading}
          />
          <button
            onClick={handleSubmit}
            disabled={loading || !input.trim()}
            className="h-[42px] w-[42px] flex-shrink-0 flex items-center justify-center bg-gradient-to-r from-[#0046ad] to-[#003890] hover:from-[#003890] hover:to-[#002d6e] text-white shadow-lg shadow-blue-800/25 rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
        <p className="mt-2 text-[10px] text-center text-slate-400">
          Enter zum Senden, Shift+Enter für neue Zeile
        </p>
      </div>
    </>
  );
}
