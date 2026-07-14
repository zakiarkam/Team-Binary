# """Build a labeled marketing dataset from RafaM97/marketing_social_media using Phi-3."""

# import pandas as pd
# from datasets import load_dataset

# import config
# from models import get_summarizer, get_phi3_generator

# GOAL_LABELS = ["awareness", "conversion", "engagement", "lead_generation", "retention"]
# TONE_LABELS = ["friendly", "professional", "luxury", "emotional", "persuasive", "humorous"]


# def _summarize_context(text: str, summarizer) -> str:
#     text = str(text)
#     if len(text.split()) < 30:
#         return text
#     try:
#         return summarizer(text, max_length=60, min_length=15, do_sample=False)[0][
#             "summary_text"
#         ]
#     except Exception:
#         return text


# def _infer_campaign_goal(instruction: str, summary: str, generator) -> str:
#     prompt = f"""
# You are a marketing strategist.

# Classify the campaign goal into ONLY ONE label.

# Allowed labels:
# awareness
# conversion
# engagement
# lead_generation
# retention

# Instruction:
# {instruction}

# Business Summary:
# {summary}

# Answer:
# """
#     try:
#         out = generator(prompt, max_new_tokens=5, do_sample=False, return_full_text=False)
#         generated = out[0]["generated_text"].strip().lower().replace("-", "_").replace(" ", "_")
#         for label in GOAL_LABELS:
#             if generated.startswith(label):
#                 return label
#         return "awareness"
#     except Exception as e:
#         print("Goal inference error:", e)
#         return "awareness"


# def _infer_tone(text: str, generator) -> str:
#     prompt = f"""
# You are a marketing tone classifier.

# Classify the tone into ONLY ONE label.

# Allowed labels:
# friendly
# professional
# luxury
# emotional
# persuasive
# humorous

# Marketing Content:
# {text}

# Answer:
# """
#     try:
#         out = generator(prompt, max_new_tokens=5, do_sample=False, return_full_text=False)
#         generated = out[0]["generated_text"].strip().lower()
#         for label in TONE_LABELS:
#             if generated.startswith(label):
#                 return label
#         return "professional"
#     except Exception as e:
#         print("Tone inference error:", e)
#         return "professional"


# def run() -> pd.DataFrame:
#     ds = load_dataset("RafaM97/marketing_social_media")
#     df = ds["train"].to_pandas()

#     summarizer = get_summarizer()
#     generator = get_phi3_generator()

#     df["summary"] = df["input"].apply(lambda t: _summarize_context(t, summarizer))
#     df["campaign_goal"] = df.apply(
#         lambda r: _infer_campaign_goal(r["instruction"], r["summary"], generator), axis=1
#     )
#     df["tone"] = df["response"].apply(lambda t: _infer_tone(t, generator))

#     final = pd.DataFrame(
#         {
#             "text": df["response"],
#             "campaign_goal": df["campaign_goal"],
#             "tone": df["tone"],
#             "summary": df["summary"],
#         }
#     )
#     final.to_csv(config.LABELED_DATASET_CSV, index=False)
#     print(f"Labeled dataset saved → {config.LABELED_DATASET_CSV} ({len(final)} rows).")
#     return final
