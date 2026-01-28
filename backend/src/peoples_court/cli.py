import argparse
import json
import logging
import os
import sys
import warnings
from dotenv import load_dotenv

# Silence noisy environment-level warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

warnings.filterwarnings("ignore")

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Explicitly silence child loggers
for logger_name in [
    "transformers",
    "peft",
    "sentence_transformers",
    "huggingface_hub",
    "httpx",
    "urllib3",
    "google",
    "absl",
    "torch",
]:
    logging.getLogger(logger_name).setLevel(logging.ERROR)


def judge_main():
    """CLI entry point for the Judge (Diagnostic/Testing tool)."""
    parser = argparse.ArgumentParser(description="AITA Judge Adjudication")
    parser.add_argument("scenario", type=str, help="The social conflict to judge")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    # Immediate feedback without interactive elements
    print("The Court is considering your request...", file=sys.stderr)

    # Lazy load heavy dependencies
    import transformers
    from transformers.utils import logging as transformers_logging

    # Silence transformers as early as possible after import
    transformers.logging.set_verbosity_error()
    transformers_logging.disable_progress_bar()

    # Import the core engine
    from .adjudicator import adjudicate as core_adjudicate
    from .config import (
        DB_NAME,
        EMBED_MODEL_NAME,
        JURY_MODEL_ID,
        JURY_ADAPTER_PATH,
        JUDGE_MODEL_NAME,
    )

    load_dotenv()

    # Load API key from env
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment.", file=sys.stderr)
        sys.exit(1)

    try:
        result = core_adjudicate(
            scenario=args.scenario,
            db_name=DB_NAME,
            embed_model_name=EMBED_MODEL_NAME,
            jury_model_id=JURY_MODEL_ID,
            jury_adapter_path=JURY_ADAPTER_PATH,
            judge_model_name=JUDGE_MODEL_NAME,
            api_key=api_key,
        )

        if "error" in result:
            print(f"Adjudication failed: {result['error']}", file=sys.stderr)
            return

        if args.json:
            print(json.dumps(result, indent=2))
            return

        # --- Diagnostics Table (Text Based) ---
        if "diagnostics" in result:
            h_rank = result["diagnostics"]["hybrid"]
            v_res = result["diagnostics"]["vector"]
            k_res = result["diagnostics"]["keyword"]

            print("\nJudicial Diagnostics: Retrieval & Ranking")
            print("-" * 80)
            print(
                f"{'Rank':<5} | {'Vector Search (Cos Sim)':<25} | {'Keyword (BM25)':<20} | {'Hybrid (RRF)':<15}"
            )
            print("-" * 80)

            for i in range(min(10, len(h_rank))):
                v = f"{v_res[i][0]} ({v_res[i][1]:.3f})" if i < len(v_res) else "-"
                k = f"{k_res[i][0]} ({k_res[i][1]:.2f})" if i < len(k_res) else "-"
                r = f"{h_rank[i][0]} ({h_rank[i][1]:.4f})" if i < len(h_rank) else "-"
                print(f"{i + 1:<5} | {v:<25} | {k:<20} | {r:<15}")
            print("-" * 80)

        # --- Formal Output ---
        print("\n" + "=" * 80)
        print(f"\n{result['opening_statement']}\n")

        # --- Jury Consensus ---
        print("Jury Consensus (ModernBERT)")
        print("-" * 30)
        for label, prob in result["consensus"].items():
            print(f"{label:<5}: {prob * 100:>6.2f}%")
        print("-" * 30)

        print(f"\nFINAL JUDICIAL VERDICT: {result['verdict']}")
        print(f"\nTHE FACTS OF THE CASE\n{result['facts']}")

        print("\nLEGAL PRECEDENTS")
        for p in result["precedents"]:
            print(f"- Case {p['case_id']}: {p['comparison']}")

        print(f"\nTHE DELIBERATION\n{result['deliberation']}")
        print("\n" + "=" * 80 + "\n")

    except Exception as e:
        print(f"Fatal error during adjudication: {e}", file=sys.stderr)


if __name__ == "__main__":
    judge_main()
