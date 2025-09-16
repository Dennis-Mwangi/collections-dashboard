import pandas as pd
import streamlit as st
import os
from datetime import datetime

# ---- Page config ----
st.set_page_config(page_title="Officer Collection Dashboard", layout="wide")

# ---- Helper: load/normalize messages CSV ----
def load_messages_csv(path):
    """
    Load messages CSV and normalize column names to: Name, Message, Timestamp.
    Works even if older CSV used columns like 'officer','message','timestamp' etc.
    """
    if not os.path.exists(path):
        return pd.DataFrame(columns=["Name", "Message", "Timestamp"])

    df = pd.read_csv(path)
    # build mapping based on lowercase names
    lower_map = {c.lower(): c for c in df.columns}
    rename_map = {}

    # name variants
    if "officer" in lower_map:
        rename_map[lower_map["officer"]] = "Name"
    elif "name" in lower_map:
        rename_map[lower_map["name"]] = "Name"

    # message variants
    if "message" in lower_map:
        rename_map[lower_map["message"]] = "Message"
    elif "msg" in lower_map:
        rename_map[lower_map["msg"]] = "Message"

    # timestamp variants
    if "timestamp" in lower_map:
        rename_map[lower_map["timestamp"]] = "Timestamp"
    elif "time" in lower_map:
        rename_map[lower_map["time"]] = "Timestamp"
    elif "date" in lower_map:
        rename_map[lower_map["date"]] = "Timestamp"

    if rename_map:
        df = df.rename(columns=rename_map)

    # ensure canonical cols exist
    for col in ["Name", "Message", "Timestamp"]:
        if col not in df.columns:
            df[col] = ""

    # Keep canonical column order
    return df[["Name", "Message", "Timestamp"]]

# ---- Navigation ----
menu = st.sidebar.radio(
    "📌 Navigation",
    ["Dashboard", "💬 Team Sharing: What's Working"]
)

# =========================
# 📊 Dashboard Page
# =========================
if menu == "Dashboard":
    # ---- Styled header ----
    st.markdown(
        "<h1 style='text-align: center; color: darkblue;'>📊 Officer Collection Dashboard</h1>",
        unsafe_allow_html=True
    )

    # ---- Load Data ----
    DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR-21kv5EFe1-Vp9TiY1GxsazJcG2fZj6qQ-24Z9Cveco76E22SDRbAya9s8PMPYXb-IvR8LdcOIFgd/pub?gid=421148399&single=true&output=csv"
    df = pd.read_csv(DATA_URL)

    # ---- Clean officer names ----
    df["officer"] = df["officer"].astype(str).str.strip().str.title()

    # ---- Identify Repaid columns dynamically (exclude 'repaid_amounts') ----
    repaid_cols = [
        col for col in df.columns
        if col.lower().startswith("repaid") and col.lower() != "repaid_amounts"
    ]

    # ---- Convert repaid columns to numeric ----
    for col in repaid_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # ---- Total repaid per row ----
    df["total_repaid"] = df[repaid_cols].sum(axis=1)

    # ---- Auto-detect days_late column (exclude days_late_lastinstallment) ----
    days_late_col = None
    for col in df.columns:
        if "days" in col.lower() and "late" in col.lower() and col.lower() != "days_late_lastinstallment":
            days_late_col = col
            break

    if not days_late_col:
        st.error("No valid 'days_late' column found.")
        st.stop()

    # ---- Define bucket function ----
    def bucket_days_late(x):
        if pd.isna(x):
            return "Unknown"
        try:
            x = int(x)
        except Exception:
            return "Unknown"
        if x <= 30:
            return "1-30"
        elif x <= 60:
            return "31-60"
        elif x <= 90:
            return "61-90"
        else:
            return "90+"

    df["days_late_bucket"] = df[days_late_col].apply(bucket_days_late)

    # ---- Define officer-bucket mapping ----
    bucket_officers_raw = {
        "1-30": ["Dennis", "Moses", "Lydia"],
        "31-60": ["Josline", "Kennedy"],
        "61-90": ["Nyamisa", "Waswa"],
        "90+": []
    }
    bucket_officers = {b: [name.strip().title() for name in names] for b, names in bucket_officers_raw.items()}

    # ---- Sidebar Filters ----
    st.sidebar.header("Filters")
    chosen_bucket = st.sidebar.selectbox("Select Days Late Bucket", ["All", "1-30", "31-60", "61-90", "90+"])

    if chosen_bucket != "All":
        displayed_officers = bucket_officers.get(chosen_bucket, [])
    else:
        displayed_officers = sorted(df["officer"].dropna().unique())

    selected_officer = st.sidebar.selectbox("Select Officer", ["All"] + displayed_officers)

    # ---- Filter data ----
    if chosen_bucket == "All":
        filtered_df = df.copy()
    else:
        allowed_officers = bucket_officers.get(chosen_bucket, [])
        filtered_df = df[
            (df["days_late_bucket"] == chosen_bucket)
            & (df["officer"].isin(allowed_officers))
        ]

    # ============================
    # 📊 Officer Summary (Bucket Totals + Top/Lowest)
    # ============================
    officer_summary = (
        filtered_df.groupby(["officer", "days_late_bucket"])["total_repaid"]
        .sum()
        .reset_index()
    )

    st.subheader("Officer Summary (Assigned Officers Only, Bucket Totals)")
    if officer_summary.empty:
        st.warning("No data available for the selected filters.")
    else:
        summary_display = officer_summary.rename(
            columns={"officer": "Officer", "days_late_bucket": "Bucket", "total_repaid": "Total Repaid"}
        )
        summary_display["Total Repaid"] = summary_display["Total Repaid"].map("{:,.2f}".format)
        st.dataframe(summary_display, use_container_width=True)

        # ---- Bucket Totals (with Grand Total row) ----
        bucket_totals = officer_summary.groupby("days_late_bucket")["total_repaid"].sum().reset_index()
        grand_total = bucket_totals["total_repaid"].sum()
        bucket_totals = pd.concat(
            [bucket_totals, pd.DataFrame([{"days_late_bucket": "Grand Total", "total_repaid": grand_total}])]
        )
        bucket_totals["total_repaid"] = bucket_totals["total_repaid"].map("{:,.2f}".format)

        st.markdown("### 📦 Bucket Totals")
        st.dataframe(
            bucket_totals.rename(columns={"days_late_bucket": "Bucket", "total_repaid": "Total Collected"}),
            use_container_width=True
        )

        # ---- Top & Lowest Collector per Bucket ----
        st.markdown("### 🏆 Top & Lowest Collectors per Bucket")
        top_lowest_list = []
        for bucket, group in officer_summary.groupby("days_late_bucket"):
            assigned = bucket_officers.get(bucket, [])
            group = group[group["officer"].isin(assigned)]
            if not group.empty:
                top_row = group.loc[group["total_repaid"].idxmax()]
                low_row = group.loc[group["total_repaid"].idxmin()]
                top_lowest_list.append({
                    "Bucket": bucket,
                    "Top Collector": top_row["officer"],
                    "Top Amount": top_row["total_repaid"],
                    "Lowest Collector": low_row["officer"],
                    "Lowest Amount": low_row["total_repaid"]
                })

        if top_lowest_list:
            top_lowest_df = pd.DataFrame(top_lowest_list)
            st.dataframe(top_lowest_df.style.format({
                "Top Amount": "{:,.2f}",
                "Lowest Amount": "{:,.2f}"
            }), use_container_width=True)

    # ============================
    # 👤 Officer Drilldown
    # ============================
    if selected_officer != "All":
        st.subheader(f"Collections for {selected_officer}")
        officer_data = filtered_df[filtered_df["officer"] == selected_officer]

        if not officer_data.empty:
            # ---- Days Late Breakdown ----
            days_summary = (
                officer_data.groupby([days_late_col])["total_repaid"]
                .sum()
                .reset_index()
                .rename(columns={days_late_col: "Days Late", "total_repaid": "Total Repaid"})
                .sort_values("Days Late")
            )
            days_summary["Total Repaid"] = days_summary["Total Repaid"].map("{:,.2f}".format)
            st.markdown("### 📊 Officer Collections by Days Late")
            st.dataframe(days_summary, use_container_width=True)

            # ---- Customer Drilldown ----
            unique_days = sorted(officer_data[days_late_col].dropna().unique())
            chosen_day = st.selectbox(
                f"View {selected_officer}'s Accounts by Days Late",
                ["All"] + [str(int(d)) for d in unique_days]
            )
            officer_accounts = officer_data.copy()
            if chosen_day != "All":
                officer_accounts = officer_accounts[officer_accounts[days_late_col] == int(chosen_day)]
            if not officer_accounts.empty:
                st.markdown("### 👤 Customer-Level Breakdown")
                customer_view = officer_accounts[
                    ["customer_id", "customer_names", days_late_col, "total_repaid"] + repaid_cols
                ].sort_values(by=days_late_col)
                for col in ["total_repaid"] + repaid_cols:
                    if col in customer_view.columns:
                        customer_view[col] = customer_view[col].map("{:,.2f}".format)
                st.dataframe(customer_view, use_container_width=True)

            # ---- Officer Collections by Repaid Date ----
            repaid_date_totals = officer_data[["officer"] + repaid_cols].melt(
                id_vars="officer", var_name="Repaid Date", value_name="Amount"
            )
            repaid_date_totals = (
                repaid_date_totals.groupby(["officer", "Repaid Date"])["Amount"]
                .sum()
                .reset_index()
            )
            repaid_date_totals["Amount"] = repaid_date_totals["Amount"].map("{:,.2f}".format)
            st.markdown("### 📅 Officer Collections by Repaid Date")
            st.dataframe(repaid_date_totals, use_container_width=True)

# =========================
# 💬 Team Sharing Page
# =========================
elif menu == "💬 Team Sharing: What's Working":
    st.markdown("## 💬 Team Sharing: What's Working")

    CSV_FILE = "team_messages.csv"

    # Load and normalize messages
    messages = load_messages_csv(CSV_FILE)

    # Post form
    with st.form("message_form", clear_on_submit=True):
        name = st.text_input("Your Name")
        message = st.text_area("Share what's working")
        submitted = st.form_submit_button("Post")

    if submitted:
        if (not name) or (not message):
            st.warning("Please enter both your name and a message before posting.")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_msg = pd.DataFrame([{
                "Name": name.strip().title(),
                "Message": message.strip(),
                "Timestamp": timestamp
            }])
            messages = pd.concat([messages, new_msg], ignore_index=True)
            # ensure canonical order and save
            messages = messages[["Name", "Message", "Timestamp"]]
            messages.to_csv(CSV_FILE, index=False)
            st.success("✅ Message posted!")
            st.experimental_rerun()

    # Display latest messages (most recent first)
    if not messages.empty:
        # attempt to parse timestamps for sorting (silently ignore parse errors)
        try:
            messages["__ts"] = pd.to_datetime(messages["Timestamp"], errors="coerce")
            messages = messages.sort_values("__ts", ascending=False).drop(columns="__ts")
        except Exception:
            pass

        st.write("### 📌 Team Messages")
        for _, row in messages.iterrows():
            st.markdown(f"**{row['Name']}** ({row['Timestamp']}):  \n{row['Message']}")
    else:
        st.info("No messages yet — be the first to share what's working!")
