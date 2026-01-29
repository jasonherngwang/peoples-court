"use client";

import { useState } from "react";
import { useAdjudicate } from "@/hooks/use-adjudicate";
import { AnimatePresence, motion } from "framer-motion";
import { Loader2, FileText, Scroll } from "lucide-react";

import { Header } from "@/components/Header";
import { GrievanceForm } from "@/components/GrievanceForm";
import { VerdictDisplay } from "@/components/VerdictDisplay";
import { PrecedentCard } from "@/components/PrecedentCard";
import { PrecedentModal } from "@/components/PrecedentModal";
import { SuggestedPrompts } from "@/components/SuggestedPrompts";

const VALID_VERDICTS = ["NTA", "YTA", "ESH", "NAH"];

export default function Home() {
  const [scenario, setScenario] = useState("");
  const [selectedPrecedent, setSelectedPrecedent] = useState<any>(null);
  const [isGrievanceExpanded, setIsGrievanceExpanded] = useState(false);

  const { adjudicate, status, result, partialResult, isLoading, error } =
    useAdjudicate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (scenario.trim()) {
      adjudicate(scenario);
    }
  };

  const scrollToPrecedent = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  // Determine if results are ready to show
  const isReady =
    (partialResult?.verdict &&
      VALID_VERDICTS.includes(partialResult.verdict)) ||
    (partialResult?.explanation && partialResult.explanation.length > 20);

  // Determine if we're showing results
  const showingResults = isLoading || isReady;

  return (
    <div className="min-h-screen flex flex-col py-8 gap-12">
      <Header showDescription={!showingResults} />

      <main className="container-narrow pb-16">
        <AnimatePresence mode="wait">
          {!isLoading && !isReady ? (
            <motion.div
              key="form"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="w-full"
            >
              <GrievanceForm
                scenario={scenario}
                onScenarioChange={setScenario}
                onSubmit={handleSubmit}
              />
            </motion.div>
          ) : (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-16 w-full"
            >
              {/* Loading State */}
              {!isReady && !error && (
                <div className="flex items-center justify-center gap-3 py-16">
                  <Loader2 className="w-6 h-6 animate-spin text-blue" />
                  <span className="body-large font-medium">
                    {status || "Analyzing your case..."}
                  </span>
                </div>
              )}

              {/* Error State */}
              {error && (
                <div className="card-elevated text-center py-8 space-y-4">
                  <p className="heading-3 text-verdict-yta">
                    Something went wrong
                  </p>
                  <p className="body-regular">{error}</p>
                  <button
                    onClick={() => window.location.reload()}
                    className="btn-secondary"
                  >
                    Try Again
                  </button>
                </div>
              )}

              {/* Results */}
              {isReady && (
                <>
                  <VerdictDisplay
                    verdict={partialResult.verdict}
                    explanation={partialResult.explanation}
                    precedents={partialResult.precedents}
                    isStreaming={!result}
                    onPrecedentClick={setSelectedPrecedent}
                    onScrollToPrecedent={scrollToPrecedent}
                  />

                  {/* Original Grievance */}
                  <section className="space-y-3">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2 heading-2">
                        <FileText size={14} />
                        Your Statement
                      </div>
                      {scenario.length > 400 && (
                        <button
                          onClick={() =>
                            setIsGrievanceExpanded(!isGrievanceExpanded)
                          }
                          className="body-small text-blue hover:underline cursor-pointer"
                        >
                          {isGrievanceExpanded ? "Collapse" : "Expand"}
                        </button>
                      )}
                    </div>
                    <div
                      className={`card body-regular italic whitespace-pre-wrap relative overflow-hidden transition-all duration-300 ${
                        !isGrievanceExpanded && scenario.length > 400
                          ? "max-h-48"
                          : ""
                      }`}
                    >
                      {scenario}
                      {!isGrievanceExpanded && scenario.length > 400 && (
                        <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-white to-transparent" />
                      )}
                    </div>
                  </section>

                  {/* Precedents */}
                  {partialResult.precedents &&
                    partialResult.precedents.length > 0 && (
                      <section className="space-y-4">
                        <div className="flex items-center gap-2 heading-2">
                          <Scroll size={14} />
                          Historical Precedents
                        </div>
                        <div className="space-y-4">
                          {partialResult.precedents.map(
                            (prec: any, i: number) => (
                              <PrecedentCard
                                key={prec.id || prec.case_id || i}
                                precedent={prec}
                                isStreaming={!result}
                                onViewDetails={setSelectedPrecedent}
                              />
                            ),
                          )}
                        </div>
                      </section>
                    )}

                  {/* Back button */}
                  <div className="pt-6 border-t border-border">
                    <button
                      onClick={() => window.location.reload()}
                      className="btn-secondary"
                    >
                      ← Submit New Grievance
                    </button>
                  </div>
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {!showingResults && (
        <section className="pb-16">
          <SuggestedPrompts onSelect={setScenario} />
        </section>
      )}

      {/* Precedent Modal */}
      <PrecedentModal
        precedent={selectedPrecedent}
        onClose={() => setSelectedPrecedent(null)}
      />
    </div>
  );
}
