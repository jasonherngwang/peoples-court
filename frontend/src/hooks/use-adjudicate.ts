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

  // Extract partial result for incremental rendering with "Sticky" behavior
  const lastValidResult = useMemo(() => {
    if (result) return result;
    if (!tokens) return null;

    try {
      let json = tokens.trim();
      if (!json.startsWith("{")) return null;

      // Robustly close open objects/arrays
      let resultStr = json;
      let stack: string[] = [];
      let inString = false;
      let escaped = false;

      for (let i = 0; i < resultStr.length; i++) {
        const char = resultStr[i];
        if (escaped) {
          escaped = false;
          continue;
        }
        if (char === "\\") {
          escaped = true;
          continue;
        }
        if (char === '"') {
          inString = !inString;
          continue;
        }
        if (inString) continue;

        if (char === "{") stack.push("}");
        if (char === "[") stack.push("]");
        if (char === "}" || char === "]") {
          if (stack.length > 0 && stack[stack.length - 1] === char) {
            stack.pop();
          }
        }
      }

      if (inString) resultStr += '"';
      while (stack.length > 0) {
        resultStr += stack.pop();
      }

      return JSON.parse(resultStr);
    } catch (e) {
      return null;
    }
  }, [tokens, result]);

  // Use a ref to keep the result "Sticky" (if parsing fails mid-stream, keep last valid result)
  const stickyResultRef = useMemo(() => {
    let current: any = null;
    return {
      get: () => current,
      set: (val: any) => {
        if (val) current = val;
      },
      clear: () => {
        current = null;
      },
    };
  }, []);

  const partialResult = useMemo(() => {
    if (lastValidResult) {
      stickyResultRef.set(lastValidResult);
      return lastValidResult;
    }
    return stickyResultRef.get();
  }, [lastValidResult, stickyResultRef]);

  const adjudicate = useCallback(
    (scenario: string, k_precedents: number = 3) => {
      setMessages([]);
      stickyResultRef.clear();
      sendMessage(
        {
          text: scenario,
        },
        {
          body: { k_precedents },
        },
      );
    },
    [sendMessage, setMessages, stickyResultRef],
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
