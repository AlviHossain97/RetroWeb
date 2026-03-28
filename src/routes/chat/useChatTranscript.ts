import { useState, useEffect, useCallback } from "react";
import { saveChatMessages, loadChatMessages, clearChatMessages, type ChatMessage } from "../../lib/storage/db";
import type { Message } from "./constants";

export function useChatTranscript() {
  const [messages, setMessages] = useState<Message[]>([]);

  // Load from IndexedDB on mount
  useEffect(() => {
    loadChatMessages().then((saved) => {
      if (saved.length > 0) {
        setMessages(saved.map((m) => ({ role: m.role, content: m.content, images: m.images })));
      }
    });
  }, []);

  // Persist when messages change
  useEffect(() => {
    if (messages.length === 0) return;
    const toSave: ChatMessage[] = messages.map((m, i) => ({
      role: m.role,
      content: m.content,
      images: m.images,
      timestamp: i,
    }));
    saveChatMessages(toSave);
  }, [messages]);

  const appendUser = useCallback((msg: Message) => {
    setMessages(prev => [...prev, msg]);
  }, []);

  const appendAssistant = useCallback((msg: Message) => {
    setMessages(prev => [...prev, msg]);
  }, []);

  const patchLastAssistant = useCallback((patch: Partial<Message>) => {
    setMessages(prev => {
      const updated = [...prev];
      updated[updated.length - 1] = { ...updated[updated.length - 1], ...patch };
      return updated;
    });
  }, []);

  const replaceMessages = useCallback((msgs: Message[]) => {
    setMessages(msgs);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    clearChatMessages();
  }, []);

  const exportAsMarkdown = useCallback(() => {
    if (messages.length === 0) return;
    const md = messages.map(m => `**${m.role === "user" ? "You" : "AI"}:**\n${m.content}`).join("\n\n---\n\n");
    const blob = new Blob([`# PiStation AI Chat\n\n${md}`], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `retroweb-chat-${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [messages]);

  return {
    messages,
    appendUser,
    appendAssistant,
    patchLastAssistant,
    replaceMessages,
    clearMessages,
    exportAsMarkdown,
  };
}
