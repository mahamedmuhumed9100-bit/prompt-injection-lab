"""Turning raw results into a CSV file and a Markdown summary."""

import csv

FIELDS = ["config", "attack_id", "category", "trial", "leaked", "blocked_by", "reply"]


def write_csv(results, path):
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)


def rate(hits, total):
    """Show a rate with its raw counts, e.g. "4/12 (33%)".

    The counts matter because the samples are small: 1/3 and 100/300 are
    both 33%, but only one of them means much.
    """
    return f"{hits}/{total} ({hits / total:.0%})" if total else "-"


def select(results, config, category=None):
    return [r for r in results
            if r["config"] == config and (category is None or r["category"] == category)]


def summary_markdown(results, model_name, trials, date):
    # dict.fromkeys removes duplicates but keeps the order the configs ran in.
    configs = list(dict.fromkeys(r["config"] for r in results))
    attacks = [r for r in results if r["category"] != "benign"]
    benign = [r for r in results if r["category"] == "benign"]
    categories = sorted({r["category"] for r in attacks})

    header = "| | " + " | ".join(configs) + " |"
    divider = "|---" * (len(configs) + 1) + "|"

    lines = [
        "# Results",
        "",
        f"- Model: `{model_name}`",
        f"- Attempts per prompt: {trials}",
        f"- Date: {date}",
        "",
        "## How often the secret leaked",
        "",
        "Lower is better. Columns are the defences that were switched on.",
        "",
        header,
        divider,
    ]
    for category in categories:
        cells = [rate(sum(r["leaked"] for r in rows), len(rows))
                 for rows in (select(attacks, c, category) for c in configs)]
        lines.append(f"| {category} | " + " | ".join(cells) + " |")
    overall = [rate(sum(r["leaked"] for r in rows), len(rows))
               for rows in (select(attacks, c) for c in configs)]
    lines.append("| **overall** | " + " | ".join(overall) + " |")

    if benign:
        cells = [rate(sum(bool(r["blocked_by"]) for r in rows), len(rows))
                 for rows in (select(benign, c) for c in configs)]
        lines += [
            "",
            "## How often harmless prompts were wrongly blocked",
            "",
            "Also lower is better. A defence that blocks normal questions has a real cost.",
            "",
            header,
            divider,
            "| benign | " + " | ".join(cells) + " |",
        ]

    if "all" in configs:
        survivors = {}
        for r in select(attacks, "all"):
            survivors.setdefault(r["attack_id"], []).append(r["leaked"])
        survivors = {attack: tries for attack, tries in survivors.items() if any(tries)}
        lines += ["", "## Attacks that got past every defence", ""]
        if survivors:
            lines += [f"- `{attack}`: leaked {sum(tries)}/{len(tries)} times"
                      for attack, tries in survivors.items()]
        else:
            lines.append("None in this run.")

    return "\n".join(lines) + "\n"
