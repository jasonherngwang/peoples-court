"use client";

import { motion } from "framer-motion";
import { Gavel, Scale } from "lucide-react";

const VALID_VERDICTS = ["NTA", "YTA", "ESH", "NAH"];

const VERDICT_LABELS: Record<string, string> = {
  NTA: "Not The Asshole",
  YTA: "You're The Asshole",
  ESH: "Everyone Sucks Here",
  NAH: "No Assholes Here",
};

interface Precedent {
  id?: string;
  case_id?: string;
  case_name?: string;
  title?: string;
  comparison?: string;
}

interface VerdictDisplayProps {
  verdict?: string;
  explanation?: string;
  precedents?: Precedent[];
  isStreaming: boolean;
  onPrecedentClick: (prec: Precedent) => void;
  onScrollToPrecedent: (id: string) => void;
}

// Helper component for streaming text animation
function StreamingText({
  text,
  animate = true,
}: {
  text: string;
  animate?: boolean;
}) {
  if (!animate) return <span>{text}</span>;

  const words = text.split(" ");

  return (
    <>
      {words.map((word, i) => (
        <motion.span
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2, delay: i * 0.02 }}
          className="inline-block mr-1"
        >
          {word}
        </motion.span>
      ))}
    </>
  );
}

export function VerdictDisplay({
  verdict,
  explanation,
  precedents = [],
  isStreaming,
  onPrecedentClick,
  onScrollToPrecedent,
}: VerdictDisplayProps) {
  const verdictClass = verdict ? `verdict-${verdict.toLowerCase()}` : "";

  // Process explanation to link precedent names
  const processExplanation = () => {
    if (!explanation) return null;

    let text = explanation;

    // Clean up quotes around case names
    precedents.forEach((prec) => {
      if (!prec.case_name) return;
      text = text.replaceAll(`'${prec.case_name}'`, prec.case_name);
      text = text.replaceAll(`"${prec.case_name}"`, prec.case_name);
    });

    // Split for linking
    let parts: (string | React.ReactNode)[] = [text];

    precedents.forEach((prec) => {
      if (!prec.case_name) return;

      const caseName = prec.case_name; // Store to maintain type narrowing

      const newParts: (string | React.ReactNode)[] = [];
      parts.forEach((part) => {
        if (typeof part !== "string") {
          newParts.push(part);
          return;
        }

        const subParts = part.split(caseName);
        subParts.forEach((subPart, i) => {
          newParts.push(subPart);
          if (i < subParts.length - 1) {
            const precId = prec.id || prec.case_id;
            newParts.push(
              <button
                key={`${precId}-${i}`}
                onClick={() => precId && onScrollToPrecedent(`prec-${precId}`)}
                className="link-inline font-medium cursor-pointer"
              >
                {caseName}
              </button>,
            );
          }
        });
      });
      parts = newParts;
    });

    return parts.map((part, i) =>
      typeof part === "string" ? (
        <StreamingText key={i} text={part} animate={isStreaming} />
      ) : (
        part
      ),
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-12 pt-4"
    >
      {/* Verdict */}
      {verdict && VALID_VERDICTS.includes(verdict) && (
        <div className="relative text-center space-y-2 py-8">
          {/* Large gavel background */}
          <div
            className="absolute inset-0 flex items-center justify-center opacity-40 pointer-events-none"
            aria-hidden="true"
          >
            <img
              src="/gavel.png"
              alt=""
              className="w-[28rem] h-[28rem] object-contain"
            />
          </div>

          {/* Content on top */}
          <div className="relative z-10">
            <p className="heading-2">The Court Rules</p>
            <h2 className={`verdict-badge ${verdictClass} mt-3`}>{verdict}</h2>
            <p className="body-large !font-semibold -mt-2">
              {VERDICT_LABELS[verdict]}
            </p>
          </div>
        </div>
      )}

      {/* Explanation */}
      {explanation && (
        <section className="space-y-4">
          <div className="flex items-center gap-2 heading-2">
            <Scale size={14} />
            The Court's Determination
          </div>
          <div className="body-large">{processExplanation()}</div>
        </section>
      )}
    </motion.div>
  );
}
