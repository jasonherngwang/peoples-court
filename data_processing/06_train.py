import os
import logging
import torch
import torch._dynamo
from typing import List, Dict
from datasets import load_dataset, ClassLabel
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
    EarlyStoppingCallback,
)
from transformers.utils import logging as transformers_logging
from peft import LoraConfig, get_peft_model, TaskType
import evaluate
import numpy as np

LABEL_NAMES: List[str] = ["NTA", "YTA", "ESH", "NAH"]
ID2LABEL: Dict[int, str] = {i: name for i, name in enumerate(LABEL_NAMES)}
LABEL2ID: Dict[str, int] = {name: i for i, name in enumerate(LABEL_NAMES)}

transformers_logging.set_verbosity_error()
logging.getLogger("datasets").setLevel(logging.ERROR)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("trainer")

# Disable Dynamo to avoid overhead and compatibility issues with custom Flash Attention/PEFT.
torch._dynamo.config.suppress_errors = True
torch._dynamo.reset()

# Hardware optimization: TF32 provides significant speedups on Ampere/Ada GPUs
# with minimal impact on precision for training stability.
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

# Configuration
MODEL_ID = "answerdotai/ModernBERT-large"
DATA_PATH = "training_data.jsonl"
OUTPUT_DIR = "./models/aita-classifier"

# 1024 is chosen to balance memory usage and context coverage;
# ModernBERT supports up to 8k but most AITA posts fits within 1k.
MAX_LENGTH = 1024

# Pre-load metrics globally; avoid surprise failures in middle of run
try:
    _accuracy_metric = evaluate.load("accuracy")
    _f1_metric = evaluate.load("f1")
except ImportError as e:
    logger.error("[!] Error loading metrics: %s", e)
    logger.error("[!] Please run: pip install scikit-learn")
    raise e


def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)
    acc = _accuracy_metric.compute(predictions=predictions, references=labels)[
        "accuracy"
    ]
    f1 = _f1_metric.compute(
        predictions=predictions, references=labels, average="macro"
    )["f1"]
    return {"accuracy": acc, "f1": f1}


def main():
    logger.info("Initializing Training...")

    if not os.path.exists(DATA_PATH):
        logger.error(
            f"[!] Data file not found: {DATA_PATH}. Please generate training data first."
        )
        return

    dataset = load_dataset("json", data_files=DATA_PATH, split="train")
    dataset = dataset.cast_column("label", ClassLabel(names=LABEL_NAMES))
    dataset = dataset.train_test_split(
        test_size=0.1, seed=42, stratify_by_column="label"
    )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

    def tokenize_fn(batch):
        tokens = tokenizer(batch["text"], truncation=True, max_length=MAX_LENGTH)
        tokens["labels"] = batch["label"]
        return tokens

    tokenized = dataset.map(
        tokenize_fn, batched=True, remove_columns=dataset["train"].column_names
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID,
        num_labels=len(LABEL_NAMES),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        torch_dtype=torch.float32,
        attn_implementation="flash_attention_2",
    )

    if hasattr(model.config, "reference_compile"):
        model.config.reference_compile = False
    model.config.use_cache = False

    # LoRA Configuration
    # target_modules are specific to ModernBERT's attention and GLU layers.
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=16,
        lora_alpha=32,
        lora_dropout=0.1,
        target_modules=["Wqkv", "Wo", "W1", "W2"],
        modules_to_save=["classifier", "head"],
    )
    model = get_peft_model(model, lora_config)
    model.enable_input_require_grads()

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=5,
        per_device_train_batch_size=32,
        per_device_eval_batch_size=32,
        gradient_accumulation_steps=1,
        learning_rate=5e-5,
        warmup_ratio=0.1,  # Prevents gradient spikes in early steps.
        weight_decay=0.01,
        max_grad_norm=1.0,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        # bf16/tf32 utilized for modern hardware acceleration.
        bf16=True,
        tf32=True,
        gradient_checkpointing=True,
        # adamw_torch_fused provides better runtime performance by fusing kernel operations.
        optim="adamw_torch_fused",
        # 4 workers provides balanced throughput for RTX 4090 without CPU bottlenecks.
        dataloader_num_workers=4,
        dataloader_pin_memory=True,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    logger.info("Starting Training...")
    trainer.train()

    logger.info(f"Saving artifacts to {OUTPUT_DIR}...")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    logger.info("Training Complete!")


if __name__ == "__main__":
    main()
