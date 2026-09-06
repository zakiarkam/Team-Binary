from datasets import load_dataset
import pandas as pd


dataset = load_dataset(
    "RafaM97/marketing_social_media"
)

df = dataset["train"].to_pandas()

df.to_csv(
    "data/raw/datasets/RafaM97_marketing_social_media_raw.csv",
    index=False
)

print(df.head())