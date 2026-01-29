"use client";

import { FormEvent } from "react";

interface GrievanceFormProps {
  scenario: string;
  onScenarioChange: (value: string) => void;
  onSubmit: (e: FormEvent) => void;
}

export function GrievanceForm({
  scenario,
  onScenarioChange,
  onSubmit,
}: GrievanceFormProps) {
  return (
    <form onSubmit={onSubmit} className="space-y-8">
      <div className="space-y-3">
        <label className="heading-2 block">Statement of Grievance</label>
        <textarea
          value={scenario}
          onChange={(e) => onScenarioChange(e.target.value)}
          placeholder="AITA because..."
          className="input-textarea h-72"
        />
      </div>

      <div className="flex flex-col sm:flex-row items-center gap-6">
        <button
          type="submit"
          disabled={!scenario.trim()}
          className="btn-primary w-full sm:w-auto"
        >
          Adjudicate
        </button>
        <p className="body-small text-center sm:text-left max-w-xs">
          Your grievance will be analyzed against a decade of{" "}
          <a
            href="https://www.reddit.com/r/AmItheAsshole/"
            target="_blank"
            rel="noopener noreferrer"
            className="link-inline"
          >
            historical precedents
          </a>{" "}
          to render a verdict.
        </p>
      </div>
    </form>
  );
}
