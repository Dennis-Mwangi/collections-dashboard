import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st


# ---- Page config ----
st.set_page_config(page_title="Officer Collection Dashboard", layout="wide")

# ---- Styled header ----
st.markdown(
    "<h1 style='text-align: center; color: darkblue;'>📊 Officer Collection Dashboard</h1>",
    unsafe_allow_html=True
)
# ----------------------------
# ✅ Map sheet names to their gid
# ----------------------------
SHEETS = {
    "Total weekly collections per officer": "38531809",
    "Total Daily Collections-officer": "1260817389",
}

# ----------------------------
# ✅ Sidebar Navigation
# ----------------------------
st.sidebar.title("Dashboard")
page = st.sidebar.radio("Go to", ["Overview", "Officer Data", "Graphs"])

# Sheet selector
sheet_choice = st.sidebar.selectbox("Select sheet", list(SHEETS.keys()))

# ----------------------------
# ✅ Load Google Sheet Data
# ----------------------------
@st.cache_data(ttl=30)
def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/1r6RdJKrcQbDu219vobz6cnUMe8Bt_fvODLbUJG739NQ/export?format=csv&gid={gid}"
    df = pd.read_csv(url)

    # Clean column names
    df.columns = df.columns.str.strip()
    officer_col = df.columns[0]
    df.rename(columns={officer_col: "Officer"}, inplace=True)

    # Convert all except "Officer" to numeric (remove commas/spaces first)
    numeric_cols = [c for c in df.columns if c != "Officer"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "").str.strip(), errors="coerce")

    # Compute total per officer
    df["Total"] = df[numeric_cols].sum(axis=1)
    return df, numeric_cols

# Load the selected sheet
df, numeric_cols = load_data(SHEETS[sheet_choice])

# ----------------------------
# ✅ Sidebar Filters
# ----------------------------
st.sidebar.subheader("Filters")

all_officers = df["Officer"].unique().tolist()
select_all = st.sidebar.checkbox("Select All Officers", value=True)

if select_all:
    officers = all_officers
else:
    officers = st.sidebar.multiselect(
        "Select officer(s)",
        options=all_officers,
        default=all_officers if not select_all else []
    )

filtered_df = df[df["Officer"].isin(officers)]

# ----------------------------
# ✅ Page Views
# ----------------------------
if page == "Overview":
    st.subheader("📌 Overview")

    officer_count = int(filtered_df["Officer"].astype(str).nunique())
    st.metric("Number of Officers", officer_count)

    total_collections = filtered_df["Total"].sum()
    st.metric("Total Collections (Ksh)", f"{total_collections:,.0f}")

    # Extra insights
    if not filtered_df.empty:
        top_officer = filtered_df.loc[filtered_df["Total"].idxmax()]
        low_officer = filtered_df.loc[filtered_df["Total"].idxmin()]

        st.write(f"🏆 **Top Officer:** {top_officer['Officer']} — Ksh {top_officer['Total']:,.0f}🎉 *Congratulations!*") 
        st.write(f"📉 **Lowest Officer:** {low_officer['Officer']} — Ksh {low_officer['Total']:,.0f}")

elif page == "Officer Data":
    st.subheader(f"📑 Raw Data – {sheet_choice}")
    st.dataframe(filtered_df, use_container_width=True)

elif page == "Graphs":
    st.subheader(f"📊 Graphs – {sheet_choice}")

    if not filtered_df.empty:
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(filtered_df["Officer"], filtered_df["Total"], color="lightblue", edgecolor="black")

        # Labels on bars
        for bar, total in zip(bars, filtered_df["Total"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() / 2,
                f"{int(total):,}",
                ha="center", va="center",
                fontsize=9, fontweight="bold"
            )

        ax.set_ylabel("Amount (Ksh)")
        ax.set_title(f"Amount per Officer – {sheet_choice}")
        plt.xticks(rotation=45, ha="right")

        st.pyplot(fig)
    else:
        st.warning("⚠️ No data available for selected officer(s).")
        plt.ylabel("Amount collected(ksh)")
        plt.title("Amount per Officer (Sept 1 - Sept 10, 2025)")
        plt.tight_layout()  
