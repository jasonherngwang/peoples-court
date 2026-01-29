"use client";

import { useState, useEffect } from "react";
import { useAdjudicate } from "@/hooks/use-adjudicate";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Gavel,
  AlertCircle,
  Stamp,
  ExternalLink,
} from "lucide-react";

// Helper component for smooth streaming text
function StreamingText({
  text,
  animate = true,
}: {
  text: string;
  animate?: boolean;
}) {
  if (!animate) return <span>{text}</span>;

  // We split by words to animate them smoothly
  const words = text.split(" ");

  return (
    <>
      {words.map((word, i) => (
        <motion.span
          key={i}
          initial={{ opacity: 0, x: -2 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="inline-block mr-1"
        >
          {word}
        </motion.span>
      ))}
    </>
  );
}

export default function Home() {
  const [scenario, setScenario] = useState("");
  const [checksum, setChecksum] = useState<string>("");
  const [referenceId, setReferenceId] = useState<string>("");
  const {
    adjudicate,
    status,
    tokens,
    result,
    partialResult,
    isLoading,
    error,
  } = useAdjudicate();

  useEffect(() => {
    setChecksum(
      ((Math.random() * 0xffffff) << 0)
        .toString(16)
        .toUpperCase()
        .padStart(6, "0"),
    );
    setReferenceId(Date.now().toString().slice(-6));
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (scenario.trim()) {
      adjudicate(scenario);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-8 py-16">
      {/* Official Registry Header */}
      <header className="mb-20 space-y-8 text-center border-b-4 border-double border-ink pb-12">
        <div className="space-y-2">
          <h1 className="text-5xl font-serif font-black tracking-tight uppercase">
            Am I The Asshole?
          </h1>
          <h2 className="text-xl font-serif italic text-navy/80">
            Portal for Submission of Social Grievances
          </h2>
        </div>
      </header>

      <AnimatePresence mode="wait">
        {!isLoading && !partialResult ? (
          <motion.form
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onSubmit={handleSubmit}
            className="space-y-12"
          >
            <div className="space-y-4">
              <label className="text-base font-bold uppercase tracking-wider block">
                Statement of Grievance
              </label>
              <textarea
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                placeholder="I, [Declarant Name], hereby submit the following for review..."
                className="w-full h-80 registry-input text-lg focus:outline-none focus:border-navy focus:bg-parchment/30 transition-all font-serif italic text-ink"
              />
            </div>

            <div className="flex flex-col md:flex-row items-center gap-6 pt-4">
              <button
                type="submit"
                disabled={!scenario.trim()}
                className="registry-button w-full md:w-auto"
              >
                FORMALLY SUBMIT FOR REVIEW
              </button>
              <div className="text-[10px] font-bold italic opacity-40 max-w-xs leading-tight">
                BY SUBMITTING THIS FORM, YOU ACKNOWLEDGE THE JURISDICTION OF THE
                PEOPLE'S COURT AND AGREE TO BE BOUND BY ITS NON-BINDING VERDICT.
              </div>
            </div>
          </motion.form>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-12"
          >
            {/* Bureaucratic Status - only show while processing and we don't have enough to show the full case */}
            {!result && (
              <div className="border border-ink p-4 flex items-center justify-between bg-white">
                <div className="flex items-center gap-3">
                  <FileText className="text-navy animate-pulse" size={18} />
                  <span className="text-xs font-bold tracking-widest uppercase">
                    {status || "PROCESSING..."}
                  </span>
                </div>
                <span className="text-[10px] opacity-40 tabular-nums">
                  REF: PC-{referenceId || "######"}
                </span>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="border-4 border-double border-wax p-8 space-y-4 bg-wax/5">
                <div className="flex items-center gap-3 text-wax uppercase font-bold text-sm tracking-tighter">
                  <AlertCircle size={20} />
                  ADMINISTRATIVE ERROR REPORTED
                </div>
                <p className="text-ink/80 text-lg leading-relaxed">{error}</p>
                <button
                  onClick={() => window.location.reload()}
                  className="text-xs font-bold underline uppercase tracking-widest hover:text-wax"
                >
                  Resubmit Documentation
                </button>
              </div>
            )}

            {/* Final Case File */}
            {partialResult && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-16"
              >
                {/* Official Verdict Stamp */}
                {partialResult.verdict && (
                  <div className="relative py-12 text-center overflow-hidden">
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-[0.03] scale-150">
                      <Stamp size={200} />
                    </div>
                    <div className="relative z-10 flex flex-col items-center gap-2">
                      <span className="text-xs font-bold tracking-[0.5em] uppercase opacity-40">
                        The Final Ruling
                      </span>
                      <h2 className="text-6xl md:text-8xl font-serif font-black uppercase tracking-tighter">
                        {partialResult.verdict}
                      </h2>
                    </div>
                  </div>
                )}

                {/* Judicial Explanation */}
                {partialResult.explanation && (
                  <section className="space-y-6 pt-8">
                    <h3 className="text-sm font-bold uppercase tracking-[0.2em] border-b border-ink pb-2">
                      The Court's Determination
                    </h3>
                    <div className="font-serif text-2xl leading-relaxed text-ink font-medium">
                      {(() => {
                        const text = partialResult.explanation;
                        const precedents = partialResult.precedents || [];

                        // If no precedents yet, just stream the text
                        if (precedents.length === 0)
                          return <StreamingText text={text} />;

                        // Try to replace case_names with links
                        let parts: (string | React.ReactNode)[] = [text];

                        precedents.forEach((prec: any) => {
                          if (!prec.case_name) return;

                          const newParts: (string | React.ReactNode)[] = [];
                          parts.forEach((part) => {
                            if (typeof part !== "string") {
                              newParts.push(part);
                              return;
                            }

                            const subParts = part.split(prec.case_name);
                            subParts.forEach((subPart, i) => {
                              newParts.push(subPart);
                              if (i < subParts.length - 1) {
                                newParts.push(
                                  <button
                                    key={`${prec.id || prec.case_id}-${i}`}
                                    onClick={() =>
                                      document
                                        .getElementById(
                                          `prec-${prec.id || prec.case_id}`,
                                        )
                                        ?.scrollIntoView({ behavior: "smooth" })
                                    }
                                    className="text-navy underline font-bold hover:text-navy/80 transition-colors"
                                  >
                                    {prec.case_name}
                                  </button>,
                                );
                              }
                            });
                          });
                          parts = newParts;
                        });

                        return parts.map((part, i) =>
                          typeof part === "string" ? (
                            <StreamingText
                              key={i}
                              text={part}
                              animate={!result}
                            />
                          ) : (
                            part
                          ),
                        );
                      })()}
                    </div>
                  </section>
                )}

                {/* Exhibits / Precedents */}
                {partialResult.precedents && (
                  <section className="space-y-6 pt-8">
                    <h3 className="text-sm font-bold uppercase tracking-[0.2em] border-b border-ink pb-2">
                      Historical Precedents Cited
                    </h3>
                    <div className="space-y-6">
                      {partialResult.precedents.map((prec: any, i: number) => (
                        <div
                          key={i}
                          id={`prec-${prec.id || prec.case_id}`}
                          className="p-8 border-l-4 border-navy bg-white shadow-sm space-y-3"
                        >
                          <div className="flex justify-between items-start">
                            <h4 className="font-serif font-black text-xl text-ink leading-tight">
                              {prec.id ? (
                                <a
                                  href={`https://www.reddit.com/r/AmItheAsshole/comments/${prec.id}/`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="hover:text-navy transition-colors flex items-center gap-2"
                                >
                                  {prec.title}
                                  <ExternalLink
                                    size={14}
                                    className="opacity-40"
                                  />
                                </a>
                              ) : (
                                <span className="opacity-40 italic">
                                  {prec.case_name || `Retrieving Document...`}
                                </span>
                              )}
                            </h4>
                          </div>

                          <p className="text-base text-ink font-serif leading-relaxed italic border-t border-ink/5 pt-3">
                            {prec.comparison ? (
                              <StreamingText
                                text={prec.comparison}
                                animate={!result}
                              />
                            ) : (
                              "Architecting comparison..."
                            )}
                          </p>

                          {prec.case_name && (
                            <div className="text-[10px] font-bold uppercase tracking-widest opacity-40">
                              Archived as: {prec.case_name}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                <div className="flex justify-between items-center pt-12 border-t border-ink/20">
                  <button
                    onClick={() => window.location.reload()}
                    className="text-[10px] font-bold text-navy hover:underline tracking-widest uppercase"
                  >
                    {`<<`} Return to Registry Filing
                  </button>
                  {result && (
                    <div className="seal">
                      <span className="text-[10px] leading-none">
                        OFFICIAL
                        <br />
                        ORDER
                      </span>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <footer className="mt-32 pt-12 border-t border-double border-ink/40 text-[9px] font-bold tracking-[0.3em] uppercase opacity-30 text-center">
        This document and its contents are the property of the High Court of
        Social Grievances. Unauthorised adjudication is strictly prohibited.
        <br />
      </footer>
    </div>
  );
}
