"""Running every prompt against every defence configuration."""

import yaml

from lab.bot import SECRET, Bot, Defences
from lab.scoring import leaked

# The experiment: the same prompts, sent to the bot with different defences on.
# "none" is the baseline everything else is compared against.
CONFIGS = {
    "none": Defences(),
    "hardened_prompt": Defences(hardened_prompt=True),
    "input_filter": Defences(input_filter=True),
    "output_filter": Defences(output_filter=True),
    "all": Defences(hardened_prompt=True, input_filter=True, output_filter=True),
}


def load_attacks(path):
    with open(path, encoding="utf-8") as file:
        return yaml.safe_load(file)["attacks"]


def run_experiment(model, attacks, configs, trials, verbose=False):
    """Send every prompt `trials` times under every config.

    LLM replies are random, so the same prompt can leak on one attempt and
    be refused on the next. That's why each prompt is sent more than once.
    Returns one result dict per attempt.
    """
    results = []
    total = len(configs) * len(attacks) * trials
    for config_name, defences in configs.items():
        bot = Bot(model, defences)
        for attack in attacks:
            for trial in range(1, trials + 1):
                reply, blocked_by = bot.reply(attack["prompt"])
                result = {
                    "config": config_name,
                    "attack_id": attack["id"],
                    "category": attack["category"],
                    "trial": trial,
                    "leaked": leaked(reply, SECRET),
                    "blocked_by": blocked_by or "",
                    "reply": reply,
                }
                results.append(result)
                if verbose:
                    # flush=True so progress shows up straight away, even
                    # when the output is being saved to a file.
                    print(f"[{len(results):>4}/{total}] {config_name:<16} {attack['id']:<6} {describe(result)}",
                          flush=True)
    return results


def describe(result):
    if result["leaked"]:
        return "LEAKED"
    if result["blocked_by"]:
        return f"blocked by {result['blocked_by']}"
    return "safe"
