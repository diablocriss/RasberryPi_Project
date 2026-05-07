"""Train the hotel-reception FastText intent classifier.

Usage:
    python -m src.intent.train
    # or, from src/:
    python intent/train.py

Outputs:
    src/intent/hotel_reception_intent.bin
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import fasttext
except ImportError:
    sys.stderr.write(
        "fasttext is not installed. Install with `pip install fasttext-wheel` "
        "(prebuilt wheels for Windows/Linux/macOS).\n"
    )
    raise

# Allow running both as `python -m src.intent.train` and directly.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from intent.preprocess import preprocess  # type: ignore
else:
    from .preprocess import preprocess

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent  # robot_voice/
DATA_FILE = HERE / "training_data.json"
MODEL_FILE = PROJECT_ROOT / "models" / "hotel_reception_intent.bin"
TRAIN_TXT = HERE / "_train.txt"
VALID_TXT = HERE / "_valid.txt"

LABEL_PREFIX = "__label__"
SEED = 42
SPLIT_RATIO = 0.8

# Fillers prepended to training utterances to simulate hesitant guests.
# Applied only to TRAIN to keep validation honest.
FILLERS = [
    "um", "uh", "excuse me", "hi", "hello",
    "so", "yeah so", "well", "okay so", "please",
]

# Per-intent fillers that are domain-appropriate so we don't accidentally
# inject signal that swaps the label (e.g. don't add "bye" before a check-in).
INTENT_FILLER_BLOCKLIST = {
    "greeting": {"hi", "hello"},
    "goodbye": {"hi", "hello"},
    "thanks": {"please"},
}

# Pretty colors for console output (consistent with TTS purple / STT yellow).
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"
RESET = "\033[0m"


def _load_dataset() -> list[tuple[str, str]]:
    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    samples: list[tuple[str, str]] = []
    for intent in data["intents"]:
        label = intent["name"]
        for utt in intent["utterances"]:
            text = preprocess(utt)
            if text:
                samples.append((text, label))
    return samples


def _stratified_split(
    samples: list[tuple[str, str]], ratio: float, seed: int
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    rng = random.Random(seed)
    by_label: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for s in samples:
        by_label[s[1]].append(s)
    train, valid = [], []
    for label, items in by_label.items():
        rng.shuffle(items)
        cut = max(1, int(len(items) * ratio))
        train.extend(items[:cut])
        valid.extend(items[cut:] or [items[-1]])  # never leave a label without validation
    rng.shuffle(train)
    rng.shuffle(valid)
    return train, valid


def _augment_train(
    train: list[tuple[str, str]], seed: int
) -> list[tuple[str, str]]:
    """Generate synthetic training variants: filler prefixes + light typo noise.

    Doubles-to-triples the effective training set size to fight the small-data
    problem. Validation set is *not* augmented so reported metrics stay honest.
    """
    rng = random.Random(seed + 1)
    out: list[tuple[str, str]] = list(train)

    # 1) Filler-prefix augmentation (one filler per sample).
    for text, label in train:
        # Skip very short utterances ("yes", "no") so we don't drown the signal.
        if len(text.split()) < 2:
            continue
        choices = [f for f in FILLERS if f not in INTENT_FILLER_BLOCKLIST.get(label, set())]
        if not choices:
            continue
        filler = rng.choice(choices)
        out.append((f"{filler} {text}", label))

    # 2) Drop-a-word augmentation (mimic dropped audio frames / casual speech).
    for text, label in train:
        words = text.split()
        if len(words) < 4:  # don't mutilate short ones
            continue
        idx = rng.randrange(len(words))
        dropped = " ".join(w for i, w in enumerate(words) if i != idx)
        if dropped:
            out.append((dropped, label))

    rng.shuffle(out)
    return out


def _write_fasttext_file(path: Path, samples: list[tuple[str, str]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for text, label in samples:
            f.write(f"{LABEL_PREFIX}{label} {text}\n")


def _per_intent_metrics(
    y_true: list[str], y_pred: list[str]
) -> dict[str, dict[str, float]]:
    labels = sorted(set(y_true) | set(y_pred))
    metrics: dict[str, dict[str, float]] = {}
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        metrics[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": tp + fn,
        }
    return metrics


def _print_confusion(y_true: list[str], y_pred: list[str]) -> None:
    labels = sorted(set(y_true) | set(y_pred))
    matrix: dict[str, Counter] = {label: Counter() for label in labels}
    for t, p in zip(y_true, y_pred):
        matrix[t][p] += 1

    short = [lab[:4] for lab in labels]
    header = " " * 14 + " ".join(f"{s:>4s}" for s in short)
    print(f"\n{CYAN}Confusion matrix (rows=true, cols=pred){RESET}")
    print(header)
    for label in labels:
        row = " ".join(f"{matrix[label][p]:>4d}" for p in labels)
        print(f"{label:14s}{row}")


def main() -> int:
    print(f"{CYAN}== FastText hotel-reception intent training =={RESET}")
    samples = _load_dataset()
    label_counts = Counter(label for _, label in samples)

    print(f"{DIM}Loaded {len(samples)} samples across {len(label_counts)} intents:{RESET}")
    for label, n in sorted(label_counts.items()):
        print(f"  {label:14s} {n}")

    train, valid = _stratified_split(samples, SPLIT_RATIO, SEED)
    print(
        f"\nSplit: {GREEN}{len(train)} train{RESET} / "
        f"{YELLOW}{len(valid)} validation{RESET} ({int(SPLIT_RATIO*100)}/{int((1-SPLIT_RATIO)*100)})"
    )

    train_aug = _augment_train(train, SEED)
    print(f"After augmentation: {GREEN}{len(train_aug)} train{RESET} (filler+drop variants added)")

    _write_fasttext_file(TRAIN_TXT, train_aug)
    _write_fasttext_file(VALID_TXT, valid)

    print(f"\n{CYAN}Training FastText...{RESET}")
    # Spec hyperparameters; minCount lowered to 1 (small dataset) and
    # char n-grams (minn/maxn) added for typo robustness.
    model = fasttext.train_supervised(
        input=str(TRAIN_TXT),
        lr=0.5,
        epoch=50,
        wordNgrams=2,
        dim=100,
        loss="softmax",
        minCount=1,
        bucket=200_000,
        minn=3,
        maxn=6,
        thread=1,    # deterministic across runs
        verbose=0,
    )

    # Validation
    y_true: list[str] = []
    y_pred: list[str] = []
    misclassified: list[tuple[str, str, str, float]] = []
    for text, label in valid:
        labels, probs = model.predict(text, k=1)
        pred = labels[0].replace(LABEL_PREFIX, "")
        prob = float(probs[0])
        y_true.append(label)
        y_pred.append(pred)
        if pred != label:
            misclassified.append((text, label, pred, prob))

    overall_acc = sum(1 for t, p in zip(y_true, y_pred) if t == p) / max(1, len(y_true))
    print(f"\n{GREEN}Overall validation accuracy: {overall_acc*100:.2f}%{RESET}")

    metrics = _per_intent_metrics(y_true, y_pred)
    print(f"\n{CYAN}Per-intent metrics:{RESET}")
    print(f"  {'intent':14s} {'P':>6s} {'R':>6s} {'F1':>6s} {'n':>4s}")
    for label in sorted(metrics):
        m = metrics[label]
        f1_color = GREEN if m["f1"] >= 0.85 else (YELLOW if m["f1"] >= 0.70 else RED)
        print(
            f"  {label:14s} "
            f"{m['precision']:6.2f} {m['recall']:6.2f} "
            f"{f1_color}{m['f1']:6.2f}{RESET} "
            f"{int(m['support']):>4d}"
        )

    _print_confusion(y_true, y_pred)

    if misclassified:
        print(f"\n{YELLOW}Misclassified examples ({len(misclassified)}):{RESET}")
        for text, true, pred, prob in misclassified[:30]:
            print(f"  [{true} -> {pred} @ {prob:.2f}]  {text}")
    else:
        print(f"\n{GREEN}No misclassifications on the validation set.{RESET}")

    # Save model
    model.save_model(str(MODEL_FILE))
    print(f"\n{GREEN}Saved model -> {MODEL_FILE}{RESET}")

    # Targets
    unknown_recall = metrics.get("unknown", {}).get("recall", 0.0)
    f1_min = min(m["f1"] for m in metrics.values())
    print(f"\n{CYAN}Targets check:{RESET}")
    print(f"  overall accuracy > 0.90 : {overall_acc:.2f}  {'OK' if overall_acc > 0.90 else 'MISS'}")
    print(f"  per-intent F1   > 0.85  : min={f1_min:.2f}  {'OK' if f1_min > 0.85 else 'MISS'}")
    print(f"  unknown recall  > 0.80  : {unknown_recall:.2f}  {'OK' if unknown_recall > 0.80 else 'MISS'}")

    # Cleanup intermediate files
    for p in (TRAIN_TXT, VALID_TXT):
        try:
            p.unlink()
        except OSError:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
