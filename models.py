"""Lazy-loaded ML models. Each model loads only when first accessed."""

import warnings

# Import config before torch: config sets the OpenMP/thread environment guards,
# which must be in place before torch initializes its native runtime.
import config  # noqa: F401  (imported for its import-time side effects too)

import torch

warnings.filterwarnings("ignore")

def _select_device() -> str:
    """Preferred accelerator. Apple Silicon is the primary dev target here."""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


DEVICE = _select_device()

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


def generate_with_phi3(
    prompt: str,
    max_new_tokens: int = 450,
    deterministic: bool = False,
) -> str:
    """Chat-template generation with Phi-3.

    Returns only the model's completion. `generate` returns the prompt tokens
    followed by the completion, so decoding the whole sequence would echo the
    prompt back to the caller — which silently breaks any parser that scans the
    output for a keyword the prompt itself contains.

    Set deterministic=True for classification and label-verification calls,
    where sampling makes the same input produce different labels across runs.
    """
    _load_phi3()
    messages = [{"role": "user", "content": prompt}]
    input_text = _phi_tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = _phi_tokenizer(input_text, return_tensors="pt").to(_phi_model.device)

    sampling = (
        {"do_sample": False}
        if deterministic
        else {"do_sample": True, "temperature": 0.7, "top_p": 0.9}
    )

    outputs = _phi_model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        pad_token_id=_phi_tokenizer.eos_token_id,
        **sampling,
    )

    prompt_length = inputs["input_ids"].shape[-1]
    completion = outputs[0][prompt_length:]
    return _phi_tokenizer.decode(completion, skip_special_tokens=True).strip()


# def get_semantic_model():
#     global _semantic_model
#     if _semantic_model is None:
#         from sentence_transformers import SentenceTransformer
#         _semantic_model = SentenceTransformer(config.SEMANTIC_MODEL_NAME)
#     return _semantic_model

def get_semantic_model():
    global _semantic_model

    print("A")

    if _semantic_model is None:

        print("B")

        from sentence_transformers import SentenceTransformer

        print("C")

        _semantic_model = SentenceTransformer(
            config.SEMANTIC_MODEL_NAME,
            device="cpu"
        )

        print("D")

    print("E")

    return _semantic_model
