import torch
import os
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from sentence_transformers import SentenceTransformer
from typing import Dict, Optional, List
from .config import EMBED_MODEL_NAME


class Jury:
    """Handles pre-deliberation polling using a fine-tuned transformer model."""

    def __init__(self, model_id: str, adapter_path: Optional[str] = None):
        if torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"

        import logging
        import transformers.utils.logging as tf_logging

        tf_logging.set_verbosity_error()
        tf_logging.disable_progress_bar()
        logging.getLogger("peft").setLevel(logging.ERROR)

        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_id, num_labels=4
        )
        if adapter_path and os.path.exists(adapter_path):
            from peft import PeftModel

            self.model = PeftModel.from_pretrained(self.model, adapter_path)

        self.model.to(self.device).eval()
        self.labels = ["NTA", "YTA", "ESH", "NAH"]

    def predict(self, text: str) -> Dict[str, float]:
        """Predicts the probability of each AITA verdict."""
        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, max_length=512
        ).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

        return {label: float(prob) for label, prob in zip(self.labels, probs[0])}


class Embedder:
    """Handles text embedding using Sentence Transformers."""

    def __init__(self, model_id: str = EMBED_MODEL_NAME):
        self.model = SentenceTransformer(model_id, trust_remote_code=True)

    def encode(self, text: str, dim: int = 256) -> List[float]:
        """Encodes text into a vector, optionally truncating dimensions."""
        # Note: nomic-embed-text-v1.5 supports Matryoshka embeddings
        embedding = self.model.encode(text, convert_to_numpy=True)
        if dim < len(embedding):
            return embedding[:dim].tolist()
        return embedding.tolist()
