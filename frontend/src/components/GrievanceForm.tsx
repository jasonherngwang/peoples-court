"use client";

import { FormEvent } from "react";
import { SuggestedPrompts } from "./SuggestedPrompts";

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
    <form onSubmit={onSubmit} className="space-y-8 w-full">
      <div className="w-full space-y-4">
        <label className="heading-2 block text-center">
          Statement of Grievance
        </label>
        <textarea
          value={scenario}
          onChange={(e) => onScenarioChange(e.target.value)}
          placeholder="AITA because I..."
          className="input-textarea h-80 w-full"
        />
      </div>

      <div className="flex flex-col items-center gap-6">
        <button
          type="submit"
          disabled={!scenario.trim()}
          className="btn-primary min-w-[200px]"
        >
          Adjudicate
        </button>
      </div>
    </form>
  );
}
