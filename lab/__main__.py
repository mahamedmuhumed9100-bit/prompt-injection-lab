"""Command-line entry point. Run `python -m lab --help` to see the options."""

import argparse
import datetime
import sys
from pathlib import Path

import requests

from lab.bot import SECRET
from lab.models import FakeModel, OllamaModel
from lab.report import summary_markdown, write_csv
from lab.runner import CONFIGS, load_attacks, run_experiment


def main():
    parser = argparse.ArgumentParser(
        description="Attack a chatbot with prompt injections and measure how often it leaks its secret."
    )
    parser.add_argument("--model", default="llama3.2:3b",
                        help="Ollama model to attack (default: %(default)s)")
    parser.add_argument("--trials", type=int, default=3,
                        help="attempts per prompt per config (default: %(default)s)")
    parser.add_argument("--limit", type=int,
                        help="only use the first N prompts, for a quick check")
    parser.add_argument("--configs", default=",".join(CONFIGS),
                        help="comma-separated defence configs to run (default: %(default)s)")
    parser.add_argument("--attacks", default="attacks.yaml",
                        help="file of prompts to send (default: %(default)s)")
    parser.add_argument("--out", default="results",
                        help="folder to save results in (default: %(default)s)")
    parser.add_argument("--fake", action="store_true",
                        help="use a fake offline model instead of Ollama, to test the plumbing")
    args = parser.parse_args()

    names = args.configs.split(",")
    unknown = [name for name in names if name not in CONFIGS]
    if unknown:
        parser.error(f"unknown config(s): {', '.join(unknown)}. Choose from: {', '.join(CONFIGS)}")
    configs = {name: CONFIGS[name] for name in names}

    attacks = load_attacks(args.attacks)[:args.limit]
    model = FakeModel(SECRET) if args.fake else OllamaModel(args.model)
    model_name = "fake" if args.fake else args.model

    try:
        results = run_experiment(model, attacks, configs, args.trials, verbose=True)
    except requests.ConnectionError:
        sys.exit(f"Couldn't reach Ollama at {model.host}. Is it running? Start it with: ollama serve")
    except RuntimeError as error:
        sys.exit(str(error))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(results, out / "results.csv")
    summary = summary_markdown(results, model_name, args.trials, datetime.date.today())
    (out / "report.md").write_text(summary, encoding="utf-8")

    print("\n" + summary)
    print(f"Saved {out / 'results.csv'} and {out / 'report.md'}")


if __name__ == "__main__":
    main()
