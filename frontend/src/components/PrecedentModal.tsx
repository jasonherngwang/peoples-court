"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, FileText, MessageSquare } from "lucide-react";

interface Comment {
  author: string;
  body: string;
  score: number;
}

interface Precedent {
  id?: string;
  case_id?: string;
  case_name?: string;
  title?: string;
  text?: string;
  comments?: Comment[];
}

interface PrecedentModalProps {
  precedent: Precedent | null;
  onClose: () => void;
}

export function PrecedentModal({ precedent, onClose }: PrecedentModalProps) {
  if (!precedent) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Overlay */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="modal-overlay"
        />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.98, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.98, y: 10 }}
          className="modal-content relative w-full max-w-3xl flex flex-col z-[60] bg-cream"
        >
          {/* Header */}
          <div className="p-4 sm:p-6 border-b border-border flex flex-col sm:flex-row justify-between sm:items-center gap-3 shrink-0 bg-cream">
            <div className="space-y-1">
              <p className="heading-2">Case Archive</p>
              <p className="body-regular">
                {precedent.case_name || "Case Details"}
              </p>
            </div>
            <div className="flex items-center gap-2 sm:gap-3">
              <a
                href={`https://www.reddit.com/comments/${precedent.id || precedent.case_id}/`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary text-xs sm:text-sm flex-1 sm:flex-initial text-center"
              >
                Reddit→
              </a>
              <button
                onClick={onClose}
                className="p-2 hover:bg-cream-dark rounded-md transition-colors cursor-pointer shrink-0"
              >
                <X size={20} strokeWidth={1.5} />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-8">
            {/* Original Post */}
            <section className="space-y-4">
              <div className="space-y-4">
                <h4 className="font-serif text-3xl font-normal leading-tight text-ink">
                  {precedent.title}
                </h4>
                <div className="body-regular whitespace-pre-wrap">
                  {precedent.text}
                </div>
              </div>
            </section>

            {/* Comments */}
            {precedent.comments && precedent.comments.length > 0 && (
              <section className="space-y-4">
                <div className="flex items-center gap-2 heading-2 text-blue">
                  <MessageSquare size={14} />
                  Community Judgments
                </div>
                <div className="space-y-3">
                  {precedent.comments.map((comment, idx) => (
                    <div key={idx} className="card-elevated space-y-2">
                      <div
                        className="body-regular"
                        dangerouslySetInnerHTML={{ __html: comment.body }}
                      />
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
