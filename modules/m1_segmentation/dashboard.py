import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import psycopg2
from config import DB_CONFIG


# ── Page Config ──────────────────────────────────────────
st.set_page_config(
    page_title="Module 1 — Audience Segmentation",
    page_icon="🎯",
    layout="wide"
)


# ── PostgreSQL Connection ─────────────────────────────────
def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# ── Load Data From PostgreSQL ─────────────────────────────
@st.cache_data
def load_data():

    conn = get_connection()

    query = """
    SELECT *
    FROM user_segments;
    """

    data = pd.read_sql(query, conn)

    conn.close()

    return data


data = load_data()


# ── Rename Columns If Required ────────────────────────────
if "segment_name" in data.columns:
    data["rf_segment"] = data["segment_name"]

if "segment_confidence" in data.columns:
    data["rf_confidence"] = data["segment_confidence"]


# ── Colors ────────────────────────────────────────────────
segment_colors = {
    "Low Engagement": "#e74c3c",
    "Loyal Customer": "#2ecc71",
    "High Intent": "#3498db",
    "Price Sensitive": "#f39c12",
    "New Cold User": "#9b59b6"
}


# ── Header ────────────────────────────────────────────────
st.title("🎯 Module 1 — Audience Targeting & Personalization")

st.markdown(
    "**Team Binary | University of Moratuwa | Sarah MMF — 215110N**"
)

st.divider()


# ── KPI Cards ─────────────────────────────────────────────
st.subheader("📊 Overview")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    "Total Users",
    f"{len(data):,}"
)

col2.metric(
    "Total Segments",
    data["rf_segment"].nunique()
)

col3.metric(
    "Avg Confidence",
    f"{data['rf_confidence'].mean()*100:.1f}%"
)

col4.metric(
    "Model Accuracy",
    "100%"
)

col5.metric(
    "Cold Start Users",
    (data["rf_segment"] == "New Cold User").sum()
)


st.divider()


# ── Segment Distribution ──────────────────────────────────
st.subheader("👥 Segment Distribution — RF Hybrid")


col1, col2 = st.columns(2)


counts = data["rf_segment"].value_counts()

colors = [
    segment_colors.get(x, "#808080")
    for x in counts.index
]


with col1:

    fig, ax = plt.subplots(figsize=(8,5))

    bars = ax.bar(
        counts.index,
        counts.values,
        color=colors
    )

    ax.set_title(
        "Segment Distribution",
        fontweight="bold"
    )

    ax.set_xlabel("Segment")
    ax.set_ylabel("Users")

    plt.xticks(rotation=15)

    for bar, value in zip(bars, counts.values):

        ax.text(
            bar.get_x()+bar.get_width()/2,
            value,
            str(value),
            ha="center"
        )

    plt.tight_layout()

    st.pyplot(fig)



with col2:

    fig, ax = plt.subplots(figsize=(8,5))

    ax.pie(
        counts.values,
        labels=counts.index,
        colors=colors,
        autopct="%1.1f%%"
    )

    ax.set_title(
        "Segment Percentage",
        fontweight="bold"
    )

    st.pyplot(fig)



st.divider()


# ── Confidence Scores ─────────────────────────────────────

st.subheader("🎯 Confidence Scores by Segment")


conf = (
    data.groupby("rf_segment")["rf_confidence"]
    .mean()
)


fig, ax = plt.subplots(figsize=(10,4))

bars = ax.bar(
    conf.index,
    conf.values
)


ax.set_ylim(0,1)

ax.set_title(
    "Average Confidence Score"
)

plt.xticks(rotation=15)

st.pyplot(fig)



st.divider()


# ── Conversion Rate ───────────────────────────────────────

st.subheader(
    "📈 Conversion Rate By Segment"
)


if "Conversion" in data.columns:

    conv = (
        data.groupby("rf_segment")["Conversion"]
        .mean()
        .sort_values(ascending=False)
    )


    conv_df = pd.DataFrame(
        {
            "Segment": conv.index,
            "Conversion Rate (%)":
            (conv.values*100).round(1)
        }
    )


    st.dataframe(
        conv_df,
        hide_index=True,
        use_container_width=True
    )



st.divider()


# ── User Lookup ───────────────────────────────────────────

st.subheader("🔎 User Segment Lookup")


if "CustomerID" in data.columns:

    customer_id = st.number_input(
        "Enter Customer ID:",
        min_value=int(data["CustomerID"].min()),
        max_value=int(data["CustomerID"].max())
    )


    if st.button("Search"):

        user = data[
            data["CustomerID"] == customer_id
        ]


        if len(user):

            row = user.iloc[0]

            st.success(
                "Customer Found"
            )


            st.write(
                {
                    "Customer ID": row["CustomerID"],
                    "Segment": row["rf_segment"],
                    "Confidence":
                    f"{row['rf_confidence']*100:.1f}%"
                }
            )

        else:

            st.error(
                "Customer not found"
            )


st.divider()


# ── Database Info ─────────────────────────────────────────

st.subheader(
    "🗄️ System Information"
)


col1, col2, col3 = st.columns(3)


col1.info(
    """
Database: PostgreSQL

Name: marketing_db

Table: user_segments
"""
)


col2.info(
    """
Method:
Hybrid Random Forest

Accuracy:
100%

Confidence:
99.7%
"""
)


col3.info(
    """
Dataset:
Digital Marketing Campaign

Storage:
PostgreSQL
"""
)



st.divider()


st.markdown(
"""
<div style='text-align:center; color:gray;'>
Module 1 — Audience Targeting & Personalization Engine |
Team Binary | University of Moratuwa | 2026
</div>
""",
unsafe_allow_html=True
)