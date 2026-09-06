import pandas as pd

DATA_PATH = "data/raw/digital_marketing_conversion.csv"


def main():
    df = pd.read_csv(DATA_PATH)

    print("=== Shape ===")
    print(f"Total rows: {len(df)}")

    print("\n=== Columns ===")
    print(df.columns.tolist())

    print("\n=== Dtypes ===")
    print(df.dtypes)

    print("\n=== Conversion base rate ===")
    print(df["Conversion"].mean())

    print("\n=== Nunique: AdvertisingPlatform ===")
    print(df["AdvertisingPlatform"].nunique())

    print("\n=== Nunique: AdvertisingTool ===")
    print(df["AdvertisingTool"].nunique())

    print("\n=== Sample rows ===")
    print(df.sample(5))


    print("=== Correlation: ConversionRate vs Conversion ===")
    print(df['ConversionRate'].corr(df['Conversion']))

    print("=== Correlation: ClickThroughRate vs Conversion ===")
    print(df['ClickThroughRate'].corr(df['Conversion']))
    

    print("\n=== Nulls per column ===")
    print(df.isnull().sum())


if __name__ == "__main__":
    main()
