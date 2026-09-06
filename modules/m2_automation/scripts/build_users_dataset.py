import pandas as pd

RAW_PATH = "data/raw/digital_marketing_conversion.csv"
SEGMENTS_PATH = "data/processed/user_segments.csv"
OUTPUT_PATH = "data/processed/users_merged.csv"

ENGAGEMENT_COLS = [
    "EmailOpens",
    "EmailClicks",
    "PagesPerVisit",
    "WebsiteVisits",
    "TimeOnSite",
]

EXPECTED_SEGMENTS = {
    "High Intent",
    "Low Engagement",
    "Price Sensitive",
    "Loyal Customer",
    "New Cold User",
}

RAW_FEATURE_COLS = [
    "Age",
    "Gender",
    "Income",
    "CampaignChannel",
    "CampaignType",
    "AdSpend",
    "ClickThroughRate",
    "ConversionRate",
    "WebsiteVisits",
    "PagesPerVisit",
    "TimeOnSite",
    "SocialShares",
    "EmailOpens",
    "EmailClicks",
    "PreviousPurchases",
    "LoyaltyPoints",
]


def main():
    raw_df = pd.read_csv(RAW_PATH)
    seg_df = pd.read_csv(SEGMENTS_PATH)

    merged = raw_df.merge(seg_df, on="CustomerID", how="inner")

    assert len(merged) == 8000, (
        f"Expected 8000 rows after merge, got {len(merged)}"
    )
    assert merged["segment_name"].isnull().sum() == 0, (
        "Found nulls in segment_name after merge"
    )
    found_segments = set(merged["segment_name"].unique())
    missing_segments = EXPECTED_SEGMENTS - found_segments
    assert not missing_segments, (
        f"Missing expected segment names: {missing_segments}"
    )

    normalized = (merged[ENGAGEMENT_COLS] - merged[ENGAGEMENT_COLS].min()) / (
        merged[ENGAGEMENT_COLS].max() - merged[ENGAGEMENT_COLS].min()
    )
    merged["engagement_score"] = normalized.mean(axis=1)

    print("=== Merged shape ===")
    print(merged.shape)

    print("\n=== Segment counts ===")
    print(merged["segment_name"].value_counts())

    print("\n=== engagement_score.describe() (overall) ===")
    print(merged["engagement_score"].describe())

    print("\n=== engagement_score.describe() (by segment_name) ===")
    print(merged.groupby("segment_name")["engagement_score"].describe())

    print("\n=== Conversion base rate by segment_name ===")
    print(merged.groupby("segment_name")["Conversion"].mean())

    output_cols = ["CustomerID", "segment_name", "engagement_score", "Conversion"] + RAW_FEATURE_COLS
    merged[output_cols].to_csv(OUTPUT_PATH, index=False)


if __name__ == "__main__":
    main()
