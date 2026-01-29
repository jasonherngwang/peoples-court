"use client";

import { useState, useEffect } from "react";
import { Sparkles, RotateCw } from "lucide-react";
import suggestedPrompts from "../data/suggested-prompts.json";

interface Prompt {
  id: number;
  text: string;
  theme: string;
}

interface SuggestedPromptsProps {
  onSelect: (text: string) => void;
}

export function SuggestedPrompts({ onSelect }: SuggestedPromptsProps) {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const getRandomPrompts = (count: number) => {
    return [...suggestedPrompts]
      .sort(() => 0.5 - Math.random())
      .slice(0, count);
  };

  useEffect(() => {
    setPrompts(getRandomPrompts(6));
  }, []);

  const handleRefresh = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsRefreshing(true);
    setTimeout(() => {
      setPrompts(getRandomPrompts(6));
      setIsRefreshing(false);
    }, 300);
  };

  return (
    <div className="prompts-container-wide space-y-4 animate-fade-in pt-24 pb-16 flex flex-col items-center">
      <div className="flex items-center justify-center gap-3 w-full">
        <h2 className="heading-2 uppercase tracking-widest text-ink/80 text-center">
          Example Grievances
        </h2>
        <button
          type="button"
          onClick={handleRefresh}
          className="p-1.5 text-blue hover:text-blue-dark transition-colors cursor-pointer group rounded-full hover:bg-blue/5"
          title="Shuffle suggestions"
        >
          <RotateCw
            size={18}
            className={`transition-transform duration-500 ${isRefreshing ? "rotate-180" : "group-hover:rotate-45"}`}
          />
        </button>
      </div>

      <div className="prompt-grid">
        {prompts.map((prompt) => (
          <button
            key={prompt.id}
            type="button"
            onClick={() => onSelect(prompt.text)}
            className="prompt-chip group animate-slide-up"
          >
            <span className="prompt-chip-text">"{prompt.text}"</span>
          </button>
        ))}
      </div>
    </div>
  );
}
