"use client";

import { motion } from "framer-motion";
import { BookOpen } from "lucide-react";

interface Precedent {
  id?: string;
  case_id?: string;
  case_name?: string;
  title?: string;
  text?: string;
  comparison?: string;
  comments?: any[];
}

interface PrecedentCardProps {
  precedent: Precedent;
  isStreaming: boolean;
  onViewDetails: (prec: Precedent) => void;
}

// Helper for streaming text
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

export function PrecedentCard({
  precedent,
  isStreaming,
  onViewDetails,
}: PrecedentCardProps) {
  const precId = precedent.id || precedent.case_id;

  return (
    <div id={`prec-${precId}`} className="card-elevated space-y-4">
      {/* Case name badge */}
      {precedent.case_name && (
        <span className="status-badge">{precedent.case_name}</span>
      )}

      {/* Title and action */}
      <div className="flex justify-between items-start gap-4">
        <h4 className="heading-3">
          {precId ? (
            <a
              href={`https://www.reddit.com/comments/${precId}/`}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:opacity-70 transition-opacity"
            >
              {precedent.title || precedent.case_name}
            </a>
          ) : (
            precedent.title || (
              <span className="text-ink-muted italic">
                {precedent.case_name || "Retrieving Document..."}
              </span>
            )
          )}
        </h4>
        {precedent.id && (
          <button
            onClick={() => onViewDetails(precedent)}
            className="btn-secondary flex items-center gap-2 shrink-0"
            title="View Full Case"
          >
            <BookOpen size={14} />
            <span className="hidden sm:inline">View Case</span>
          </button>
        )}
      </div>

      {/* Comparison */}
      {precedent.comparison && (
        <div className="body-regular border-t border-border pt-4">
          <StreamingText text={precedent.comparison} animate={isStreaming} />
        </div>
      )}
    </div>
  );
}
