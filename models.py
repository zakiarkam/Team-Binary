"""Lazy-loaded ML models. Each model loads only when first accessed."""

import warnings
import torch

import config

warnings.filterwarnings("ignore")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_summarizer = None
_phi_tokenizer = None
_phi_model = None
_phi_generator = None
_semantic_model = None


def get_summarizer():
    global _summarizer
    if _summarizer is None:
        from transformers import pipeline
        _summarizer = pipeline(
            "summarization",
            model=config.SUMMARIZATION_MODEL_NAME,
            device=0 if torch.cuda.is_available() else -1,
        )
    return _summarizer


def _load_phi3():
    global _phi_tokenizer, _phi_model
    if _phi_model is None:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        _phi_tokenizer = AutoTokenizer.from_pretrained(
            config.GENERATION_MODEL_NAME, trust_remote_code=True
        )
        _phi_model = AutoModelForCausalLM.from_pretrained(
            config.GENERATION_MODEL_NAME,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto",
            trust_remote_code=True,
        )


def get_phi3_generator():
    global _phi_generator
    if _phi_generator is None:
        from transformers import pipeline
        _load_phi3()
        _phi_generator = pipeline(
            "text-generation", model=_phi_model, tokenizer=_phi_tokenizer
        )
    return _phi_generator


def generate_with_phi3(prompt: str, max_new_tokens: int = 450) -> str:
    """Chat-template generation with Phi-3."""
    _load_phi3()
    messages = [{"role": "user", "content": prompt}]
    input_text = _phi_tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = _phi_tokenizer(input_text, return_tensors="pt").to(_phi_model.device)
    outputs = _phi_model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        pad_token_id=_phi_tokenizer.eos_token_id,
    )
    return _phi_tokenizer.decode(outputs[0], skip_special_tokens=True).strip()


def get_semantic_model():
    global _semantic_model
    if _semantic_model is None:
        from sentence_transformers import SentenceTransformer
        _semantic_model = SentenceTransformer(config.SEMANTIC_MODEL_NAME)
    return _semantic_model
