import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  streamObject,
} from "ai";
import { google } from "@ai-sdk/google";
import { z } from "zod";

export const runtime = "edge";

// Simple in-memory rate limit for Edge (ephemeral, but good as a speed bump)
const rateLimitMap = new Map<string, { count: number; lastReset: number }>();
const RATE_LIMIT = 3; // requests
const WINDOW_MS = 60 * 1000; // 1 minute

export async function POST(req: Request) {
  try {
    // 0. Simple Rate Limiting
    const ip = req.headers.get("x-forwarded-for")?.split(",")[0] || "anonymous";
    const now = Date.now();
    const userLimit = rateLimitMap.get(ip) || { count: 0, lastReset: now };

    if (now - userLimit.lastReset > WINDOW_MS) {
      userLimit.count = 0;
      userLimit.lastReset = now;
    }

    if (userLimit.count >= RATE_LIMIT) {
      return new Response(
        "Excessive judicial inquiries. Please wait a moment.",
        { status: 429 },
      );
    }

    userLimit.count++;
    rateLimitMap.set(ip, userLimit);

    const { messages, k_precedents } = await req.json();
    const lastMessage = messages[messages.length - 1];

    let scenario = "";
    if (lastMessage.parts) {
      const textParts = lastMessage.parts.filter((p: any) => p.type === "text");
      scenario = textParts.map((p: any) => p.text).join("");
    } else {
      scenario = lastMessage.content || lastMessage.text || "";
    }

    const stream = createUIMessageStream({
      execute: async ({ writer }) => {
        try {
          // 1. Fetch Context from OCI backend
          writer.write({
            type: "data-status" as any,
            data: { status: "Searching for precedents..." },
          });

          if (!process.env.NEXT_PUBLIC_API_URL) {
            throw new Error("NEXT_PUBLIC_API_URL is not configured on Vercel.");
          }

          const contextResponse = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/context`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-API-Key": process.env.INTERNAL_API_KEY || "",
              },
              body: JSON.stringify({ scenario, k_precedents }),
              // Ensure we don't hang too long on cold OCI
              signal: AbortSignal.timeout(15000),
            },
          );

          if (!contextResponse.ok) {
            const errText = await contextResponse.text();
            throw new Error(
              `Retriever Error (${contextResponse.status}): ${errText || contextResponse.statusText}`,
            );
          }

          const { precedents, consensus } = await contextResponse.json();

          // 2. Build Context for Judge
          let contextText =
            "### CURRENT EVIDENCE PROVIDED BY THE PLAINTIFF:\n\n";
          contextText += scenario + "\n\n";
          contextText += "### PRE-DELIBERATION JURY POLLING:\n";
          Object.entries(consensus).forEach(([label, prob]) => {
            contextText += `- ${label}: ${((prob as number) * 100).toFixed(2)}%\n`;
          });
          contextText += "\n";
          contextText += "### RELEVANT CASE LAW (PRECEDENTS):\n\n";
          precedents.forEach((p: any, i: number) => {
            contextText += `CASE ${i + 1}: ID \`${p.id}\` - Title: ${p.title}\n`;
            contextText += `Official Reddit Verdict: ${p.verdict}\n`;
            contextText += `Facts: ${p.text.substring(0, 1000)}...\n`;
            contextText += "Top Judgments from the Jury:\n";
            p.comments?.forEach((c: any) => {
              contextText += `- ${c.author} (Score ${c.score}): ${c.body.substring(0, 200)}...\n`;
            });
            contextText += "\n---\n";
          });

          // 3. Adjudicate with Gemini (Stream Object for robust JSON)
          writer.write({
            type: "data-status" as any,
            data: { status: "The Judge is deliberating..." },
          });

          const { partialObjectStream } = await streamObject({
            model: google("gemini-2.5-flash-lite"),
            schema: z.object({
              verdict: z.enum(["YTA", "NTA", "ESH", "NAH"]),
              explanation: z.string(),
              precedents: z.array(
                z.object({
                  case_id: z.string(),
                  case_name: z.string(),
                  comparison: z.string(),
                }),
              ),
            }),
            prompt: `
              You are the Judge of 'The People's Court'. Your task is to provide a final verdict in just 3-4 concise, authoritative sentences.
              
              Mandatory Instructions:
              1. Verdict: Must be one of YTA, NTA, ESH, NAH.
              2. Explanation: Provide a few sentences explaining your ruling. You MUST refer to the precedents below by their 'case_name'.
              3. Precedents: For each case provided in the context, create a very short (1 sentence) comparison and an amusing/descriptive 'case_name' (e.g., 'The Case of the Audacious Avocado'). 
              
              ${contextText}
            `,
          });

          // Loop through the object stream and emit tokens for the custom parser
          let lastFullString = "";
          let textStreamStarted = false;

          for await (const partialObject of partialObjectStream) {
            const currentString = JSON.stringify(partialObject);
            const delta = currentString.slice(lastFullString.length);
            if (delta) {
              if (!textStreamStarted) {
                writer.write({ type: "text-start", id: "adjudication" });
                textStreamStarted = true;
              }
              writer.write({
                type: "text-delta",
                id: "adjudication",
                delta: delta,
              });
            }
            lastFullString = currentString;
          }

          if (textStreamStarted) {
            writer.write({ type: "text-end", id: "adjudication" });
          }

          // Final Enrichment
          try {
            const finalObject = JSON.parse(lastFullString);
            const dbMap = new Map(precedents.map((p: any) => [p.id, p]));
            const enrichedPrecedents = finalObject.precedents.map(
              (cite: any) => {
                const data = dbMap.get(cite.case_id);
                return data ? { ...data, ...cite } : cite;
              },
            );

            writer.write({
              type: "data-result" as any,
              data: {
                ...finalObject,
                precedents: enrichedPrecedents,
                consensus,
              },
            });
          } catch (e) {
            console.error("Enrichment Error:", e);
          }
        } catch (e: any) {
          console.error("Stream Execution Error:", e);
          writer.write({
            type: "data-status" as any,
            data: { status: `Court Error: ${e.message}` },
          });
        }
      },
    });

    return createUIMessageStreamResponse({ stream });
  } catch (error: any) {
    console.error("Proxy Error:", error);
    return new Response(`Internal Server Error: ${error.message}`, {
      status: 500,
    });
  }
}
