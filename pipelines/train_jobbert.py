"""
Fine-tune JobBERT on SkillSpan for skill NER.

Downloads jjzha/skillspan from HuggingFace and fine-tunes jjzha/jobbert-base-cased
to recognize skill/knowledge spans in job descriptions.

Output: models/jobbert-skill-ner/  (model + tokenizer + label config)

Usage:
    python pipelines/train_jobbert.py          # ~15-20 mins on Apple MPS
    python pipelines/train_jobbert.py --epochs 5  # more training = better F1
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import numpy as np
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
)

sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings
from pipelines.utils import get_torch_device

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_MODEL = "jjzha/jobbert-base-cased"
DATASET_NAME = "jjzha/skillspan"
OUTPUT_DIR = settings.BASE_DIR / "models" / "jobbert-skill-ner"

# SkillSpan label scheme
LABEL_NAMES = ["O", "B-Skill", "I-Skill", "B-Knowledge", "I-Knowledge"]
LABEL2ID = {label: i for i, label in enumerate(LABEL_NAMES)}
ID2LABEL = {i: label for i, label in enumerate(LABEL_NAMES)}

# At inference, both Skill and Knowledge spans count as "skills"
SKILL_LABELS = {"B-Skill", "I-Skill", "B-Knowledge", "I-Knowledge"}


def tokenize_and_align_labels(
    examples: dict,
    tokenizer: AutoTokenizer,
    label_all_tokens: bool = False,
) -> dict:
    """
    Tokenize words and align NER labels to subword tokens.

    BERT splits words into subword pieces (e.g., "PyTorch" → ["Py", "##Torch"]).
    Only the first subword token gets the real label; the rest get -100 (ignored
    by the loss function). This is the standard approach for BERT NER fine-tuning.
    """
    tokenized = tokenizer(
        examples["tokens"],
        truncation=True,
        max_length=512,
        is_split_into_words=True,
    )

    aligned_labels = []
    for i, label_ids in enumerate(examples["label_ids"]):
        word_ids = tokenized.word_ids(batch_index=i)
        previous_word_id = None
        label_row = []
        for word_id in word_ids:
            if word_id is None:
                # Special tokens ([CLS], [SEP]) → ignored
                label_row.append(-100)
            elif word_id != previous_word_id:
                # First subword of a new word → use actual label
                label_row.append(label_ids[word_id])
            else:
                # Continuation subword → label_all_tokens keeps it, else ignore
                label_row.append(label_ids[word_id] if label_all_tokens else -100)
            previous_word_id = word_id
        aligned_labels.append(label_row)

    tokenized["labels"] = aligned_labels
    return tokenized


def compute_metrics(eval_pred: tuple, id2label: dict) -> dict:
    """
    Compute token-level NER metrics using seqeval.
    Reports per-class F1 + macro average.
    """
    from seqeval.metrics import classification_report, f1_score, precision_score, recall_score

    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=2)

    # Remove padding (-100) and convert IDs to label strings
    true_labels = [[id2label[l] for l in label_row if l != -100] for label_row in labels]
    pred_labels = [
        [id2label[p] for p, l in zip(pred_row, label_row) if l != -100]
        for pred_row, label_row in zip(predictions, labels)
    ]

    return {
        "precision": precision_score(true_labels, pred_labels),
        "recall": recall_score(true_labels, pred_labels),
        "f1": f1_score(true_labels, pred_labels),
    }


def train(num_epochs: int = 3, batch_size: int = 4, force_cpu: bool = False) -> None:
    """Run the full fine-tuning pipeline."""
    logger.info("═" * 60)
    logger.info("JobBERT Fine-tuning on SkillSpan")
    logger.info("═" * 60)

    if force_cpu:
        # Disable MPS before any model/trainer init to prevent OOM crashes
        # on Apple Silicon when other apps have consumed shared GPU memory
        torch.backends.mps.is_available = lambda: False  # type: ignore[method-assign]
        torch.backends.mps.is_built = lambda: False  # type: ignore[method-assign]
        os.environ["ACCELERATE_USE_MPS_DEVICE"] = "NO"
        logger.info("CPU mode: MPS disabled, running on CPU (~1-2 hrs)")

    device = get_torch_device()
    logger.info(f"Device: {device}")

    # ── 1. Load dataset ───────────────────────────────────────────────────────
    logger.info(f"Loading dataset: {DATASET_NAME}")
    raw_dataset = load_dataset(DATASET_NAME)
    logger.info(f"  Train: {len(raw_dataset['train']):,} examples")
    logger.info(f"  Validation: {len(raw_dataset['validation']):,} examples")

    # ── 2. Merge tags_skill + tags_knowledge → integer label_ids ──────────────
    # New schema splits labels into two string columns; merge into one int column.
    # Skill tags take priority over Knowledge tags when both are non-O.
    skill_str2id = {"O": 0, "B": 1, "I": 2}
    know_str2id = {"O": 0, "B": 3, "I": 4}

    def merge_tags(examples: dict) -> dict:
        merged = []
        for skill_row, know_row in zip(examples["tags_skill"], examples["tags_knowledge"]):
            row = []
            for s, k in zip(skill_row, know_row):
                skill_id = skill_str2id.get(s, 0)
                know_id = know_str2id.get(k, 0)
                row.append(skill_id if skill_id != 0 else know_id)
            merged.append(row)
        examples["label_ids"] = merged
        return examples

    # Debug: inspect first example's raw tags before merging
    first = raw_dataset["train"][0]
    available_cols = list(first.keys())
    logger.info(f"  Dataset columns: {available_cols}")
    if "tags_skill" in first:
        logger.info(f"  Sample tags_skill[:5]: {first['tags_skill'][:5]}")
    if "tags_knowledge" in first:
        logger.info(f"  Sample tags_knowledge[:5]: {first['tags_knowledge'][:5]}")

    raw_dataset = raw_dataset.map(merge_tags, batched=True)
    unique_ids = sorted({t for ex in raw_dataset["train"] for t in ex["label_ids"]})
    logger.info(f"  Label IDs present: {unique_ids} → {[ID2LABEL[i] for i in unique_ids]}")

    # ── 3. Load tokenizer ─────────────────────────────────────────────────────
    logger.info(f"Loading tokenizer: {BASE_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    # ── 4. Tokenize + align labels ────────────────────────────────────────────
    logger.info("Tokenizing and aligning labels...")
    tokenized_dataset = raw_dataset.map(
        lambda examples: tokenize_and_align_labels(examples, tokenizer),
        batched=True,
        remove_columns=raw_dataset["train"].column_names,
    )

    # ── 5. Load model ─────────────────────────────────────────────────────────
    logger.info(f"Loading model: {BASE_MODEL}")
    model = AutoModelForTokenClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(LABEL_NAMES),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,  # JobBERT has different classifier head size
    )
    model.to(device)

    # ── 6. Training arguments ─────────────────────────────────────────────────
    # MPS workaround: use_mps_device is deprecated in newer transformers,
    # the Trainer auto-detects MPS via torch.backends.mps
    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR / "checkpoints"),
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=4,  # smaller eval batch to reduce MPS peak
        gradient_accumulation_steps=4,  # effective batch = batch_size*4
        gradient_checkpointing=not force_cpu,  # only on GPU; adds CPU overhead
        warmup_steps=100,
        weight_decay=0.01,
        learning_rate=2e-5,
        eval_strategy="epoch",  # evaluate after each epoch — catch underperformance early
        save_strategy="epoch",  # must match eval_strategy when load_best_model_at_end=True
        save_total_limit=2,  # keep only the 2 best checkpoints
        logging_steps=50,
        report_to="none",  # no wandb
        dataloader_num_workers=0,  # MPS stability
        fp16=False,  # MPS doesn't support fp16
        bf16=False,
        seed=42,
    )

    data_collator = DataCollatorForTokenClassification(tokenizer)

    # ── Class weights: penalise O-label dominance (~85% of tokens) ───────────
    label_counts = np.bincount(
        [label for ex in tokenized_dataset["train"]["labels"] for label in ex if label != -100]
    )
    class_weights = torch.tensor(
        1.0 / (label_counts / label_counts.sum()),
        dtype=torch.float,
    ).to(device)
    logger.info(
        f"Class weights: { {ID2LABEL[i]: f'{w:.1f}' for i, w in enumerate(class_weights.tolist())} }"
    )

    class WeightedTrainer(Trainer):
        """Trainer subclass that applies inverse-frequency class weights to the loss."""

        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.get("labels")
            outputs = model(**inputs)
            logits = outputs.get("logits")
            loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights, ignore_index=-100)
            loss = loss_fn(logits.view(-1, model.config.num_labels), labels.view(-1))
            return (loss, outputs) if return_outputs else loss

    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["validation"],
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=lambda p: compute_metrics(p, ID2LABEL),
    )

    # ── 7. Train ──────────────────────────────────────────────────────────────
    logger.info(f"Starting training — {num_epochs} epochs, batch size {batch_size}")
    logger.info("This takes ~15-20 mins on Apple MPS, ~1-2 hours on CPU...")
    train_result = trainer.train()
    logger.info(f"Training complete ✅  loss={train_result.training_loss:.4f}")

    # ── 8. Evaluate on test set ───────────────────────────────────────────────
    if "test" in raw_dataset:
        tokenized_test = raw_dataset["test"].map(
            lambda examples: tokenize_and_align_labels(examples, tokenizer),
            batched=True,
            remove_columns=raw_dataset["test"].column_names,
        )
        metrics = trainer.evaluate(tokenized_test)
        logger.info(f"Test metrics: {metrics}")

    # ── 9. Save model + config ────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))

    # Save label config so extract_skills.py can load it
    label_config = {
        "id2label": ID2LABEL,
        "label2id": LABEL2ID,
        "label_names": LABEL_NAMES,
        "skill_labels": sorted(SKILL_LABELS),
        "base_model": BASE_MODEL,
        "dataset": DATASET_NAME,
    }
    (OUTPUT_DIR / "label_config.json").write_text(json.dumps(label_config, indent=2))
    logger.info(f"Model saved → {OUTPUT_DIR} ✅")
    logger.info("Next step: run 'make extract' to re-run skill extraction with JobBERT")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    parser = argparse.ArgumentParser(description="Fine-tune JobBERT on SkillSpan")
    parser.add_argument("--epochs", type=int, default=15, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size per device")
    parser.add_argument(
        "--cpu", action="store_true", help="Force CPU (use when MPS is OOM due to other apps)"
    )
    args = parser.parse_args()
    train(num_epochs=args.epochs, batch_size=args.batch_size, force_cpu=args.cpu)
