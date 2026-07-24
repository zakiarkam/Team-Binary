import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import psycopg2

# ── Page Config ──────────────────────────────────────────
st.set_page_config(
    page_title = "Module 1 — Audience Segmentation",
    page_icon  = "🎯",
    layout     = "wide"
)

# ── Load Data Directly from CSV ───────────────────────────
@st.cache_data
def load_data():
    data = pd.read_csv("digital_marketing_campaign_dataset.csv")
    segments = pd.read_csv("user_segments.csv")
    data['rf_segment']    = segments['segment_name'].values
    data['rf_confidence'] = segments['segment_confidence'].values
    return data

data = load_data()

# ── Colors ────────────────────────────────────────────────
segment_colors = {
    'Low Engagement'  : '#e74c3c',
    'Loyal Customer'  : '#2ecc71',
    'High Intent'     : '#3498db',
    'Price Sensitive' : '#f39c12',
    'New Cold User'   : '#9b59b6'
}

# ── Header ────────────────────────────────────────────────
st.title("🎯 Module 1 — Audience Targeting & Personalization")
st.markdown("**Team Binary | University of Moratuwa | Sarah MMF — 215110N**")
st.divider()

# ── KPI Cards ─────────────────────────────────────────────
st.subheader("📊 Overview")
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Users",      f"{len(data):,}")
col2.metric("Total Segments",   "5")
col3.metric("Avg Confidence",   f"{data['rf_confidence'].mean()*100:.1f}%")
col4.metric("Model Accuracy",   "100%")
col5.metric("Cold Start Users", f"{(data['rf_segment'] == 'New Cold User').sum()}")

st.divider()

# ── Segment Distribution ──────────────────────────────────
st.subheader("👥 Segment Distribution — RF Hybrid")

col1, col2 = st.columns(2)

with col1:
    fig, ax = plt.subplots(figsize=(8, 5))
    counts  = data['rf_segment'].value_counts()
    colors  = [segment_colors[s] for s in counts.index]
    bars    = ax.bar(counts.index, counts.values, color=colors)
    ax.set_title('Segment Distribution', fontweight='bold')
    ax.set_xlabel('Segment')
    ax.set_ylabel('Number of Users')
    plt.xticks(rotation=15)
    for bar, v in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width()/2,
                v + 20, str(v), ha='center', fontweight='bold')
    plt.tight_layout()
    st.pyplot(fig)

with col2:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.pie(
        counts.values,
        labels     = counts.index,
        colors     = colors,
        autopct    = '%1.1f%%',
        startangle = 90
    )
    ax.set_title('Segment Percentage', fontweight='bold')
    plt.tight_layout()
    st.pyplot(fig)

st.divider()

# ── Confidence Scores ─────────────────────────────────────
st.subheader("🎯 Confidence Scores by Segment")

fig, ax = plt.subplots(figsize=(10, 4))
conf    = data.groupby('rf_segment')['rf_confidence'].mean()
colors  = [segment_colors[s] for s in conf.index]
bars    = ax.bar(conf.index, conf.values, color=colors)
ax.set_title('Average Confidence Score by Segment', fontweight='bold')
ax.set_xlabel('Segment')
ax.set_ylabel('Confidence Score')
ax.set_ylim(0.95, 1.0)
plt.xticks(rotation=15)
for bar, v in zip(bars, conf.values):
    ax.text(bar.get_x() + bar.get_width()/2,
            v + 0.0005, f'{v:.3f}', ha='center', fontweight='bold')
plt.tight_layout()
st.pyplot(fig)

st.divider()

# ── Conversion Rate Comparison ────────────────────────────
st.subheader("📈 Conversion Rate — All Methods Comparison")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**RF Hybrid — Conversion Rate by Segment**")
    conv = data.groupby('rf_segment')['Conversion'].mean().round(3)
    conv_df = pd.DataFrame({
        'Segment'         : conv.index,
        'Conversion Rate' : (conv.values * 100).round(1)
    }).sort_values('Conversion Rate', ascending=False)
    st.dataframe(conv_df, hide_index=True, use_container_width=True)

with col2:
    st.markdown("**Method Comparison Summary**")
    comparison_df = pd.DataFrame({
        'Method'      : ['Rule-Based', 'K-Means', 'Hierarchical', 'RF Hybrid'],
        'Conv Diff'   : ['38.3%', '7.0%', '3.5%', '38.3%'],
        'Stability'   : ['100%', '5.9%', '27%', '100%'],
        'Cold Start'  : ['126', '0', '0', '163'],
        'Confidence'  : ['N/A', 'N/A', 'N/A', '99.7%']
    })
    st.dataframe(comparison_df, hide_index=True, use_container_width=True)

st.divider()

# ── Feature Importance ────────────────────────────────────
st.subheader("🔍 Feature Importance — Random Forest")

importance_data = {
    'Feature'   : ['rule_encoded', 'WebsiteVisits', 'PreviousPurchases',
                   'LoyaltyPoints', 'EmailClicks', 'ml_encoded',
                   'hier_encoded', 'SocialShares', 'PagesPerVisit',
                   'TimeOnSite', 'EmailOpens'],
    'Importance': [0.4904, 0.1691, 0.1505, 0.0820, 0.0793,
                   0.0086, 0.0079, 0.0037, 0.0036, 0.0029, 0.0020]
}

imp_df = pd.DataFrame(importance_data).sort_values(
    'Importance', ascending=True)

fig, ax = plt.subplots(figsize=(10, 6))
colors  = ['#e74c3c' if i >= len(imp_df) - 3 else '#3498db'
           for i in range(len(imp_df))]
ax.barh(imp_df['Feature'], imp_df['Importance'], color=colors)
ax.set_title('Random Forest Feature Importance', fontweight='bold')
ax.set_xlabel('Importance Score')
plt.tight_layout()
st.pyplot(fig)

st.divider()

# ── Conversion Rate Chart ─────────────────────────────────
st.subheader("📊 Conversion Rate by Segment — Visual")

fig, ax = plt.subplots(figsize=(10, 5))
conv_sorted = conv.sort_values(ascending=False)
colors = [segment_colors[s] for s in conv_sorted.index]
bars = ax.bar(conv_sorted.index,
              conv_sorted.values * 100, color=colors)
ax.set_title('Conversion Rate by Segment — RF Hybrid',
             fontweight='bold')
ax.set_xlabel('Segment')
ax.set_ylabel('Conversion Rate (%)')
ax.set_ylim(0, 110)
plt.xticks(rotation=15)
for bar, v in zip(bars, conv_sorted.values * 100):
    ax.text(bar.get_x() + bar.get_width()/2,
            v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
plt.tight_layout()
st.pyplot(fig)

st.divider()

# ── User Lookup ───────────────────────────────────────────
st.subheader("🔎 User Segment Lookup")

customer_id = st.number_input(
    "Enter Customer ID:",
    min_value = int(data['CustomerID'].min()),
    max_value = int(data['CustomerID'].max()),
    value     = int(data['CustomerID'].min())
)

if st.button("Search"):
    user = data[data['CustomerID'] == customer_id]
    if len(user) > 0:
        row = user.iloc[0]
        st.success("✅ Customer Found!")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Customer ID",  row['CustomerID'])
        col2.metric("Segment",      row['rf_segment'])
        col3.metric("Confidence",   f"{row['rf_confidence']*100:.1f}%")
        col4.metric("Converted",    "Yes" if row['Conversion'] == 1 else "No")
    else:
        st.error("Customer not found!")

st.divider()

# ── Cross Dataset Summary ─────────────────────────────────
st.subheader("🌍 Cross Dataset Validation")

cross_df = pd.DataFrame({
    'Metric'      : ['Accuracy', 'Confidence', 'Cold Start', 'Stability'],
    'Dataset 1'   : ['100%', '99.7%', '163 users', '100%'],
    'Dataset 2'   : ['100%', '99.7%', '1,626 users', '100%']
})
st.dataframe(cross_df, hide_index=True, use_container_width=True)

st.divider()

# ── Database Info ─────────────────────────────────────────
st.subheader("🗄️ System Information")
col1, col2, col3 = st.columns(3)
col1.info("**Database:** PostgreSQL\n\n**Name:** marketing_db\n\n**Tables:** user_segments, segmentation_summary")
col2.info("**Method:** Hybrid Random Forest\n\n**Accuracy:** 100%\n\n**Confidence:** 99.7%")
col3.info("**Dataset 1:** 8,000 users\n\n**Dataset 2:** 10,000 users\n\n**Total Evaluated:** 18,000 users")

# ── Footer ────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style='text-align:center; color:gray;'>
Module 1 — Audience Targeting & Personalization Engine |
Team Binary | University of Moratuwa | 2026
</div>
""", unsafe_allow_html=True)