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
# Map sheet names to their gid
# ----------------------------
SHEETS = {
    "Total weekly collections per officer": "38531809",
    "Total Daily Collections-officer": "1260817389",
    "Pochi": "421148399"
}

# ----------------------------
# Sidebar Navigation
# ----------------------------
st.sidebar.title("Dashboard")
page = st.sidebar.radio("Go to", ["Overview", "Officer Data", "Graphs"])
sheet_choice = st.sidebar.selectbox("Select sheet", list(SHEETS.keys()))

# ----------------------------
# Load Google Sheet Data
# ----------------------------
@st.cache_data(ttl=30)
def load_data(gid, sheet_choice):
    url = f"https://docs.google.com/spreadsheets/d/1r6RdJKrcQbDu219vobz6cnUMe8Bt_fvODLbUJG739NQ/export?format=csv&gid={gid}"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    # ---- Special handling for POCHI ----
    if sheet_choice == "Pochi":
        # Normalize officer column
        if "officer" in df.columns:
            df.rename(columns={"officer": "Officer"}, inplace=True)
        else:
            df.rename(columns={df.columns[0]: "Officer"}, inplace=True)

        # Ensure numeric conversions
        for col in ["days_late", "total_due", "repaid_amounts"]:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].apply(lambda x: str(x).replace(",", "").strip()),
                    errors="coerce"
                )

        # Compute Amount Collected = total_due - repaid_amounts
        if "total_due" in df.columns and "repaid_amounts" in df.columns:
            df["Amount Collected"] = df["total_due"] - df["repaid_amounts"]
        else:
            df["Amount Collected"] = pd.to_numeric(0, errors="coerce")

        # Define buckets from days_late
        bins = [0, 30, 60, 90, float("inf")]
        labels = ["1-30", "31-60", "61-90", "90+"]
        if "days_late" in df.columns:
            df["Bucket"] = pd.cut(df["days_late"], bins=bins, labels=labels, right=True)
        else:
            df["Bucket"] = "Unknown"

        # Group by Officer + Bucket
        df = df.groupby(["Officer", "Bucket"], as_index=False)[["Amount Collected"]].sum()

    else:
        # Standard officer collection sheets
        df.rename(columns={df.columns[0]: "Officer"}, inplace=True)
        numeric_cols = [c for c in df.columns if c != "Officer"]

        for col in numeric_cols:
            df[col] = pd.to_numeric(
                df[col].apply(lambda x: str(x).replace(",", "").strip()), errors="coerce"
            )

        df["Amount Collected"] = df[numeric_cols].sum(axis=1)
        df = df.groupby("Officer", as_index=False)[["Amount Collected"]].sum()
        df["Bucket"] = "All"  # placeholder for consistency

    return df

# ----------------------------
# Load selected sheet
# ----------------------------
df = load_data(SHEETS[sheet_choice], sheet_choice)

# ----------------------------
# Sidebar Filters
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
# Page Views
# ----------------------------
if page == "Overview":
    st.subheader("📌 Overview")

    officer_count = int(filtered_df["Officer"].astype(str).nunique())
    st.metric("Number of Officers", officer_count)

    total_collections = filtered_df["Amount Collected"].sum()
    st.metric("Total Collections (Ksh)", f"{total_collections:,.0f}")

    if not filtered_df.empty:
        top_officer = filtered_df.loc[filtered_df["Amount Collected"].idxmax()]
        low_officer = filtered_df.loc[filtered_df["Amount Collected"].idxmin()]

        st.write(f"🏆 **Top Officer:** {top_officer['Officer']} — Ksh {top_officer['Amount Collected']:,.0f} 🎉")
        st.write(f"📉 **Lowest Officer:** {low_officer['Officer']} — Ksh {low_officer['Amount Collected']:,.0f}")

elif page == "Officer Data":
    st.subheader(f"📑 Data – {sheet_choice}")
    st.dataframe(filtered_df, use_container_width=True)

elif page == "Graphs":
    st.subheader(f"📊 Graphs – {sheet_choice}")

    if not filtered_df.empty:
        if sheet_choice == "Pochi":
            # Pivot buckets by officer for stacked bar chart
            pivot_df = filtered_df.pivot(index="Officer", columns="Bucket", values="Amount Collected").fillna(0)

            fig, ax = plt.subplots(figsize=(12, 6))
            pivot_df.plot(kind="bar", stacked=True, ax=ax)
            ax.set_ylabel("Amount Collected (Ksh)")
            ax.set_title("Pochi Collections by Officer and Days Late Bucket")
            plt.xticks(rotation=45, ha="right")
            st.pyplot(fig)

        else:
            fig, ax = plt.subplots(figsize=(12, 6))
            bars = ax.bar(filtered_df["Officer"], filtered_df["Amount Collected"], color="lightblue", edgecolor="black")
            for bar, total in zip(bars, filtered_df["Amount Collected"]):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2, f"{int(total):,}",
                        ha="center", va="center", fontsize=9, fontweight="bold")
            ax.set_ylabel("Amount Collected (Ksh)")
            ax.set_title(f"Total Amount Collected per Officer – {sheet_choice}")
            plt.xticks(rotation=45, ha="right")
            st.pyplot(fig)
    else:
        st.warning("⚠️ No data available for selected officer(s).")
