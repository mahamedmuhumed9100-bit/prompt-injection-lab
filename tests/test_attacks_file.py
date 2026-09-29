from lab.bot import SECRET
from lab.runner import load_attacks
from lab.scoring import leaked

ATTACKS = load_attacks("attacks.yaml")
CATEGORIES = {"direct_override", "role_play", "obfuscation", "indirect",
              "authority", "extraction", "benign"}


def test_every_attack_has_the_required_fields():
    for attack in ATTACKS:
        assert set(attack) == {"id", "category", "prompt"}, attack


def test_ids_are_unique():
    ids = [attack["id"] for attack in ATTACKS]
    assert len(ids) == len(set(ids))


def test_categories_are_known():
    for attack in ATTACKS:
        assert attack["category"] in CATEGORIES, attack["id"]


def test_no_prompt_contains_the_secret():
    # If a prompt contained the secret, a model echoing the prompt back would
    # look like a leak and the results would be wrong.
    for attack in ATTACKS:
        assert not leaked(attack["prompt"], SECRET), attack["id"]
