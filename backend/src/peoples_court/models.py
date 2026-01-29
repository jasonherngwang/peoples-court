import os
import json
from google import genai
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from sentence_transformers import SentenceTransformer
from typing import Dict, Any, Optional, List

from .config import JUDGE_MODEL_NAME, EMBED_MODEL_NAME


class Judge:
    """Handles adjudication using Gemini API."""

    def __init__(self, api_key: str, model_id: str = JUDGE_MODEL_NAME):
        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id

    async def adjudicate_stream(self, context: str, response_schema: Dict[str, Any]):
        """Sends data to Gemini and yields a stream of tokens."""
        prompt = f"""
        You are the Judge of 'The People's Court'. Your task is to provide a final verdict in just 3-4 concise, authoritative sentences.
        
        Mandatory Instructions:
        1. Verdict: Must be one of YTA, NTA, ESH, NAH.
        2. Explanation: Provide a few sentences explaining your ruling. You MUST refer to the precedents below by their 'case_name'.
        3. Precedents: For each case provided in the context, create a very short (1 sentence) comparison and an amusing/descriptive 'case_name' (e.g., 'The Case of the Audacious Avocado'). 
        
        {context}
        
        Response MUST be valid JSON according to this schema:
        {json.dumps(response_schema)}
        """

        # Note: We use the async client and generate_content_stream for true streaming
        stream = self.client.models.generate_content_stream(
            model=self.model_id,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
            },
        )
        for chunk in stream:
            if chunk.text:
                yield chunk.text

    def adjudicate(self, context: str, response_schema: Dict[str, Any]) -> str:
        """Sends data to Gemini and returns a structured response."""
        # This remains for backward compatibility with existing CLI if needed
        prompt = f"""
        You are the Judge of 'The People's Court'. Your task is to provide a final verdict in just 3-4 concise, authoritative sentences.
        
        Mandatory Instructions:
        1. Verdict: Must be one of YTA, NTA, ESH, NAH.
        2. Explanation: Provide a few sentences explaining your ruling. You MUST refer to the precedents below by their 'case_name'.
        3. Precedents: For each case provided in the context, create a very short (1 sentence) comparison and an amusing/descriptive 'case_name' (e.g., 'The Case of the Audacious Avocado'). 
        
        {context}
        
        Response MUST be valid JSON according to this schema:
        {json.dumps(response_schema)}
        """
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
            },
        )
        return response.text


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
