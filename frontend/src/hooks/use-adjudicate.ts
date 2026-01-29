"use client";

import { useChat } from "@ai-sdk/react";
import { useMemo, useCallback, useEffect } from "react";
import { DefaultChatTransport } from "ai";

export interface AdjudicationResult {
  verdict: string;
  explanation: string;
  precedents: Array<{
    id: string; // from DB
    case_id: string; // from Judge
    case_name: string; // from Judge
    title: string;
    verdict: string;
    text: string;
    comparison: string;
    url?: string;
  }>;
  consensus: Record<string, number>;
}

export function useAdjudicate() {
  const { messages, sendMessage, setMessages, status, error } = useChat({
    transport: new DefaultChatTransport({
      api: "/api/adjudicate",
    }),
  });

  // Extract tokens from the last assistant message parts
  const tokens = useMemo(() => {
    const lastAssistantMessage = [...messages]
      .reverse()
      .find((m) => m.role === "assistant");
    if (!lastAssistantMessage || !(lastAssistantMessage as any).parts)
      return "";

    return (lastAssistantMessage as any).parts
      .filter((p: any) => p.type === "text-delta" || p.type === "text")
      .map((p: any) => p.delta || p.text || "")
      .join("");
  }, [messages]);

  // Extract status from custom data parts
  const adjudicationStatus = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const message = messages[i];
      if (message.role === "assistant" && (message as any).parts) {
        const statusPart = (message as any).parts
          .reverse()
          .find((p: any) => p.type === "data-status");
        if (statusPart) return statusPart.data.status;
      }
    }
    return "";
  }, [messages]);

  const result = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const message = messages[i];
      if (message.role === "assistant" && (message as any).parts) {
        const resultPart = (message as any).parts.find(
          (p: any) => p.type === "data-result",
        );
        if (resultPart) return resultPart.data as AdjudicationResult;
      }
    }
    return null;
  }, [messages]);

  // Extract partial result for incremental rendering
  const partialResult = useMemo(() => {
    if (result) return result;
    if (!tokens) return null;

    try {
      // Attempt to fix common JSON truncation issues at the end of the stream
      let json = tokens.trim();
      if (!json.startsWith("{")) return null;

      // Close open objects/arrays for a valid parse during streaming
      let openBrackets =
        (json.match(/\{/g) || []).length - (json.match(/\}/g) || []).length;
      let openBraces =
        (json.match(/\[/g) || []).length - (json.match(/\]/g) || []).length;

      while (openBraces > 0) {
        json += "]";
        openBraces--;
      }
      while (openBrackets > 0) {
        json += "}";
        openBrackets--;
      }

      return JSON.parse(json);
    } catch (e) {
      return null;
    }
  }, [tokens, result]);

  const adjudicate = useCallback(
    (scenario: string, k_precedents: number = 3) => {
      setMessages([]);
      sendMessage(
        {
          text: scenario,
        },
        {
          body: { k_precedents },
        },
      );
    },
    [sendMessage, setMessages],
  );

  return {
    status: adjudicationStatus,
    tokens,
    result,
    partialResult,
    isLoading: status === "submitted" || status === "streaming",
    error: error?.message || null,
    adjudicate,
  };
}
