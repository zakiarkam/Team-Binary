"""Lazy-loaded ML models. Each model loads only when first accessed.

Device / dtype policy
---------------------
Every heavyweight model is placed on the best available accelerator and loaded
in a dtype that actually fits in memory. This is not a micro-optimisation: on a
16 GB Apple Silicon machine Phi-3-mini in float32 needs ~15.2 GB of weights
alone, so the OS swaps continuously and a four-platform generation run takes
hours. In float16 on the MPS backend the same weights need ~7.6 GB and the run
completes in minutes.

Override with environment variables when a backend misbehaves:
    PIPELINE_DEVICE=cpu          force everything onto CPU
    PIPELINE_DTYPE=float32       force a dtype
"""

import os
import time
import warnings

# Import config before torch: config sets the OpenMP/thread environment guards,
# which must be in place before torch initializes its native runtime.
import config  # noqa: F401  (imported for its import-time side effects too)

import torch

warnings.filterwarnings("ignore")


def _select_device() -> str:
    """Preferred accelerator. Apple Silicon is the primary dev target here."""
    forced = os.environ.get("PIPELINE_DEVICE", "").strip().lower()
    if forced in {"cpu", "mps", "cuda"}:
        return forced
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


DEVICE = _select_device()


def _select_dtype(device: str):
    """Weight dtype for the large generative models.

    float16 on cuda/mps halves the memory footprint and is the difference
    between fitting in unified memory and swapping. CPU stays float32 because
    torch's CPU float16 kernels are slower than float32, not faster.
    """
    forced = os.environ.get("PIPELINE_DTYPE", "").strip().lower()
    if forced:
        return {"float16": torch.float16,
                "bfloat16": torch.bfloat16,
                "float32": torch.float32}.get(forced, torch.float32)
    if device in {"cuda", "mps"}:
        return torch.float16
    return torch.float32


DTYPE = _select_dtype(DEVICE)

_summarizer = None
_phi_tokenizer = None
_phi_model = None
_semantic_model = None


def describe_runtime() -> str:
    return f"device={DEVICE} dtype={str(DTYPE).replace('torch.', '')} threads={torch.get_num_threads()}"


def get_summarizer():
    global _summarizer
    if _summarizer is None:
        from transformers import pipeline
        started = time.perf_counter()
        _summarizer = pipeline(
            "summarization",
            model=config.SUMMARIZATION_MODEL_NAME,
            device=DEVICE,
            torch_dtype=DTYPE,
        )
        print(f"[models] BART summarizer ready on {DEVICE} "
              f"({time.perf_counter() - started:.1f}s)")
    return _summarizer


def _load_phi3():
    global _phi_tokenizer, _phi_model
    if _phi_model is not None:
        return

    from transformers import AutoTokenizer, AutoModelForCausalLM

    started = time.perf_counter()
    print(f"[models] loading {config.GENERATION_MODEL_NAME} ({describe_runtime()})...")

    _phi_tokenizer = AutoTokenizer.from_pretrained(
        config.GENERATION_MODEL_NAME, trust_remote_code=True
    )
    if _phi_tokenizer.pad_token_id is None:
        _phi_tokenizer.pad_token = _phi_tokenizer.eos_token
    # Batched generation on a decoder-only model requires left padding, or the
    # padding sits between the prompt and the first generated token.
    _phi_tokenizer.padding_side = "left"

    load_kwargs = {
        "torch_dtype": DTYPE,
        "trust_remote_code": True,
        # Stream weights shard-by-shard instead of materialising a full float32
        # copy alongside the final one. On a 16 GB machine the naive path peaks
        # above physical memory before the first token is ever generated.
        "low_cpu_mem_usage": True,
    }
    if DEVICE == "cuda":
        # Only cuda benefits from accelerate's sharding; elsewhere "auto"
        # silently parks the model on CPU regardless of what DEVICE says.
        load_kwargs["device_map"] = "auto"

    _phi_model = AutoModelForCausalLM.from_pretrained(
        config.GENERATION_MODEL_NAME, **load_kwargs
    )
    if DEVICE != "cuda":
        _phi_model = _phi_model.to(DEVICE)
    _phi_model.eval()

    print(f"[models] Phi-3 ready on {_phi_model.device} "
          f"({time.perf_counter() - started:.1f}s)")


class _StopOnCompleteJson:
    """Stop generation once the first top-level {...} object closes.

    Every caller in this pipeline asks Phi-3 for a single JSON object and then
    discards whatever follows it. Without this the model spends the remaining
    budget writing commentary nobody reads, which on a small instruct model is
    routinely half the tokens of the call.
    """

    def __init__(self, tokenizer, prompt_length: int):
        self.tokenizer = tokenizer
        self.prompt_length = prompt_length
        self.seen = prompt_length
        self.depth = 0
        self.opened = False

    def __call__(self, input_ids, scores, **kwargs) -> bool:
        # Decode only the tokens added since the last step. Re-decoding the whole
        # completion every step would make this quadratic in the token budget.
        row = input_ids[0]
        fresh = self.tokenizer.decode(
            row[self.seen:], skip_special_tokens=True
        )
        self.seen = row.shape[-1]

        for char in fresh:
            if char == "{":
                self.depth += 1
                self.opened = True
            elif char == "}" and self.opened:
                self.depth -= 1
                if self.depth <= 0:
                    return True
        return False


def _sampling_kwargs(deterministic: bool) -> dict:
    if deterministic:
        return {"do_sample": False}
    return {"do_sample": True, "temperature": 0.7, "top_p": 0.9}


def _decode_completions(outputs, prompt_length: int) -> list[str]:
    return [
        _phi_tokenizer.decode(row[prompt_length:], skip_special_tokens=True).strip()
        for row in outputs
    ]


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
    return generate_batch_with_phi3(
        [prompt], max_new_tokens=max_new_tokens, deterministic=deterministic
    )[0]


def generate_batch_with_phi3(
    prompts: list[str],
    max_new_tokens: int = 450,
    deterministic: bool = False,
) -> list[str]:
    """Generate for several prompts in one forward pass.

    The per-platform asset calls are independent, so running them as a batch
    amortises the model's fixed per-step cost across all of them instead of
    paying it once per platform. Falls back to sequential generation if the
    batch does not fit in memory.
    """
    if not prompts:
        return []

    _load_phi3()

    from transformers import StoppingCriteriaList

    texts = [
        _phi_tokenizer.apply_chat_template(
            [{"role": "user", "content": p}],
            tokenize=False,
            add_generation_prompt=True,
        )
        for p in prompts
    ]

    inputs = _phi_tokenizer(
        texts, return_tensors="pt", padding=True
    ).to(_phi_model.device)
    prompt_length = inputs["input_ids"].shape[-1]

    generate_kwargs = {
        **inputs,
        "max_new_tokens": max_new_tokens,
        "pad_token_id": _phi_tokenizer.pad_token_id,
        "use_cache": True,
        **_sampling_kwargs(deterministic),
    }
    if len(prompts) == 1:
        # The stop criterion inspects row 0 only, so it is correct for a single
        # sequence but would cut a batch short at its fastest member.
        generate_kwargs["stopping_criteria"] = StoppingCriteriaList(
            [_StopOnCompleteJson(_phi_tokenizer, prompt_length)]
        )

    started = time.perf_counter()
    try:
        with torch.inference_mode():
            outputs = _phi_model.generate(**generate_kwargs)
    except RuntimeError:  # OOM and MPS allocation failures both land here
        if len(prompts) == 1:
            raise
        print(f"[models] batch of {len(prompts)} failed, retrying sequentially")
        return [
            generate_with_phi3(p, max_new_tokens, deterministic) for p in prompts
        ]

    generated = int(outputs.shape[-1] - prompt_length)
    elapsed = time.perf_counter() - started
    print(f"[models] {len(prompts)} completion(s), {generated} new tokens "
          f"in {elapsed:.1f}s ({generated / max(elapsed, 1e-6):.1f} tok/s)")

    return _decode_completions(outputs, prompt_length)


def get_semantic_model():
    global _semantic_model
    if _semantic_model is None:
        from sentence_transformers import SentenceTransformer
        started = time.perf_counter()
        _semantic_model = SentenceTransformer(
            config.SEMANTIC_MODEL_NAME,
            device=DEVICE,
        )
        print(f"[models] Sentence-BERT ready on {DEVICE} "
              f"({time.perf_counter() - started:.1f}s)")
    return _semantic_model
