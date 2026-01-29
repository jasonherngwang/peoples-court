"use client";

import { useState, useEffect } from "react";
import { useAdjudicate } from "@/hooks/use-adjudicate";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Gavel,
  AlertCircle,
  Stamp,
  BookOpen,
  X,
  MessageSquare,
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

const VALID_VERDICTS = ["NTA", "YTA", "ESH", "NAH"];

export default function Home() {
  const [scenario, setScenario] = useState("");
  const [checksum, setChecksum] = useState<string>("");
  const [referenceId, setReferenceId] = useState<string>("");
  const [selectedPrecedent, setSelectedPrecedent] = useState<any>(null);
  const [isGrievanceExpanded, setIsGrievanceExpanded] = useState(false);

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

  // Determine if the results are substantial enough to show
  const isReady =
    (partialResult?.verdict &&
      VALID_VERDICTS.includes(partialResult.verdict)) ||
    (partialResult?.explanation && partialResult.explanation.length > 20);

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
        {!isLoading && !isReady ? (
          <motion.form
            key="input-form"
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
            key="results-view"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-12 min-h-[60vh]"
          >
            {/* Bureaucratic Status - hide as soon as we are ready */}
            {!isReady && !error && (
              <motion.div
                exit={{ opacity: 0, height: 0 }}
                className="border border-ink p-4 flex items-center justify-between bg-white overflow-hidden"
              >
                <div className="flex items-center gap-3">
                  <FileText className="text-navy animate-pulse" size={18} />
                  <span className="text-xs font-bold tracking-widest uppercase">
                    {status || "PROCESSING..."}
                  </span>
                </div>
                <span className="text-[10px] opacity-40 tabular-nums">
                  REF: PC-{referenceId || "######"}
                </span>
              </motion.div>
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
                  className="text-xs font-bold underline uppercase tracking-widest hover:text-wax cursor-pointer"
                >
                  Resubmit Documentation
                </button>
              </div>
            )}

            {/* Final Case File Content */}
            {isReady && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-12"
              >
                {/* Official Verdict Stamp */}
                {partialResult.verdict &&
                  VALID_VERDICTS.includes(partialResult.verdict) && (
                    <div className="relative py-4 text-center">
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-[0.03] scale-125 pointer-events-none">
                        <Stamp size={160} />
                      </div>
                      <div className="relative z-10 flex flex-col items-center gap-1">
                        <span className="text-[10px] font-bold tracking-[0.5em] uppercase opacity-40">
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
                  <section className="space-y-6 pt-4">
                    <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-ink border-b-2 border-ink pb-2">
                      The Court's Determination
                    </h3>
                    <div className="font-serif text-lg leading-relaxed text-ink">
                      {(() => {
                        let text = partialResult.explanation;
                        const precedents = partialResult.precedents || [];

                        // 1. Clean up quotes around case names if the LLM added them
                        precedents.forEach((prec: any) => {
                          if (!prec.case_name) return;
                          text = text.replaceAll(
                            `'${prec.case_name}'`,
                            prec.case_name,
                          );
                          text = text.replaceAll(
                            `"${prec.case_name}"`,
                            prec.case_name,
                          );
                        });

                        // 2. Split for linking
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
                                    className="text-navy underline font-bold hover:text-navy/80 transition-colors cursor-pointer"
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

                {/* Original Grievance */}
                <section className="space-y-4">
                  <h3 className="text-[11px] font-bold uppercase tracking-[0.2em] text-ink/70 border-b border-ink/20 pb-1.5 flex justify-between items-center">
                    <span>Statement of Grievance (Original)</span>
                    {scenario.length > 500 && (
                      <button
                        onClick={() =>
                          setIsGrievanceExpanded(!isGrievanceExpanded)
                        }
                        className="text-[9px] hover:text-navy hover:underline cursor-pointer"
                      >
                        {isGrievanceExpanded ? "COLLAPSE" : "EXPAND"}
                      </button>
                    )}
                  </h3>
                  <div
                    className={`font-serif text-lg leading-relaxed text-ink/70 italic border-l-2 border-ink/10 pl-6 whitespace-pre-wrap relative overflow-hidden transition-all duration-300 ${!isGrievanceExpanded && scenario.length > 500 ? "max-h-[300px]" : ""}`}
                  >
                    {scenario}
                    {!isGrievanceExpanded && scenario.length > 500 && (
                      <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-white to-transparent pointer-events-none" />
                    )}
                  </div>
                  {!isGrievanceExpanded && scenario.length > 500 && (
                    <button
                      onClick={() => setIsGrievanceExpanded(true)}
                      className="text-xs font-bold uppercase tracking-widest text-navy hover:underline ml-6 mt-2"
                    >
                      Read Full Grievance
                    </button>
                  )}
                </section>

                {/* Exhibits / Precedents */}
                {partialResult.precedents && (
                  <section className="space-y-6 pt-4">
                    <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-ink border-b-2 border-ink pb-2">
                      Historical Precedents Cited
                    </h3>
                    <div className="space-y-6">
                      {partialResult.precedents.map((prec: any, i: number) => (
                        <div
                          key={i}
                          id={`prec-${prec.id || prec.case_id}`}
                          className="p-8 border-l-4 border-navy bg-white shadow-sm space-y-3"
                        >
                          <div className="space-y-4">
                            {prec.case_name && (
                              <div className="text-sm font-bold uppercase tracking-widest text-navy bg-navy/5 inline-block px-2 py-0.5">
                                {prec.case_name}
                              </div>
                            )}
                            <div className="flex justify-between items-start gap-4">
                              <h4 className="font-serif font-black text-xl text-ink leading-tight">
                                {prec.id || prec.case_id ? (
                                  <a
                                    href={`https://www.reddit.com/comments/${prec.id || prec.case_id}/`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="hover:text-navy hover:underline transition-all cursor-pointer"
                                  >
                                    {prec.title || prec.case_name}
                                  </a>
                                ) : (
                                  prec.title || (
                                    <span className="opacity-40 italic">
                                      {prec.case_name ||
                                        `Retrieving Document...`}
                                    </span>
                                  )
                                )}
                              </h4>
                              {prec.id && (
                                <button
                                  onClick={() => setSelectedPrecedent(prec)}
                                  className="p-2 hover:bg-navy/5 text-navy transition-colors cursor-pointer border border-navy/20"
                                  title="Inspect Original Case File"
                                >
                                  <BookOpen size={18} />
                                </button>
                              )}
                            </div>
                          </div>

                          <div className="text-base text-ink font-serif leading-relaxed italic border-t border-ink/5 pt-3">
                            {prec.comparison
                              ? (() => {
                                  let comp = prec.comparison;
                                  const allPrecedents =
                                    partialResult.precedents || [];
                                  allPrecedents.forEach((p: any) => {
                                    if (!p.case_name) return;
                                    comp = comp.replaceAll(
                                      `'${p.case_name}'`,
                                      p.case_name,
                                    );
                                    comp = comp.replaceAll(
                                      `"${p.case_name}"`,
                                      p.case_name,
                                    );
                                  });
                                  return (
                                    <StreamingText
                                      text={comp}
                                      animate={!result}
                                    />
                                  );
                                })()
                              : "Architecting comparison..."}
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                <div className="flex justify-between items-center pt-8 border-t border-ink/20">
                  <button
                    onClick={() => window.location.reload()}
                    className="text-[10px] font-bold text-navy hover:underline tracking-widest uppercase cursor-pointer"
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

      {/* Legal Archive Modal */}
      <AnimatePresence>
        {selectedPrecedent && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedPrecedent(null)}
              className="absolute inset-0 bg-navy/80 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.98, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98, y: 10 }}
              className="relative w-full max-w-4xl max-h-[90vh] bg-background border-2 border-ink overflow-hidden flex flex-col shadow-2xl"
            >
              {/* Modal Header */}
              <div className="p-6 border-b border-ink flex justify-between items-center bg-white">
                <div className="space-y-1">
                  <div className="text-[10px] font-bold uppercase tracking-[0.3em] text-navy/60">
                    Archives Section: Case Law Detail
                  </div>
                  <h3 className="font-serif font-black text-xl uppercase leading-tight text-ink">
                    {selectedPrecedent.case_name || "Official Case Record"}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedPrecedent(null)}
                  className="p-1 hover:bg-ink/5 text-ink/40 hover:text-ink transition-colors cursor-pointer"
                >
                  <X size={24} strokeWidth={1.5} />
                </button>
              </div>

              {/* Modal Content */}
              <div className="flex-1 overflow-y-auto p-10 font-serif space-y-12 bg-white selection:bg-navy/10">
                {/* Original Post */}
                <section className="space-y-6">
                  <div className="flex items-center gap-3 text-[10px] font-bold uppercase tracking-widest text-navy/40 border-b border-ink/5 pb-2">
                    <FileText size={14} />
                    Original Documentation
                  </div>
                  <div className="space-y-6">
                    <h4 className="text-2xl font-black leading-tight text-ink">
                      {selectedPrecedent.title}
                    </h4>
                    <div className="text-base leading-relaxed text-ink/80 whitespace-pre-wrap font-medium">
                      {selectedPrecedent.text}
                    </div>
                  </div>
                </section>

                {/* Evidence: Jury Comments */}
                {selectedPrecedent.comments &&
                  selectedPrecedent.comments.length > 0 && (
                    <section className="space-y-6">
                      <div className="flex items-center gap-3 text-[10px] font-bold uppercase tracking-widest text-navy/40 border-b border-ink/5 pb-2">
                        <MessageSquare size={14} />
                        Cross-Examination: Jury Judgments
                      </div>
                      <div className="space-y-4">
                        {selectedPrecedent.comments.map(
                          (comment: any, idx: number) => (
                            <div
                              key={idx}
                              className="p-6 border border-ink/5 bg-parchment/10 space-y-3 relative overflow-hidden"
                            >
                              <div className="flex justify-between items-center text-[9px] uppercase font-bold tracking-[0.2em] opacity-40">
                                <span>JUROR: {comment.author}</span>
                                <span>STRENGTH: {comment.score}</span>
                              </div>
                              <p className="text-base leading-relaxed italic text-ink/80">
                                "{comment.body}"
                              </p>
                            </div>
                          ),
                        )}
                      </div>
                    </section>
                  )}
              </div>

              {/* Modal Footer */}
              <div className="p-4 border-t border-ink/10 bg-white flex justify-between items-center text-[9px] font-bold tracking-widest uppercase opacity-40">
                <span>Ref ID: {selectedPrecedent.id}</span>
                <span>Verification Status: Certified Copy</span>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
