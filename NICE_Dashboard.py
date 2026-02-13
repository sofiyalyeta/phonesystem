import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io


st.set_page_config(page_title="Phone System Data Analysis", layout="wide")

# =========================
# Custom CSS
# =========================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans&display=swap');

    body {
        font-family: 'Arial', 'Open Sans', sans-serif;
    }

    .custom-text-area {
        font-size: 20px;
        line-height: 1.3;
        max-width: 800px;
        width: 100%;
    }

    .title {
        font-size: 56px;
        font-weight: bold;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# =========================
# Header Image
# =========================
st.markdown(
    """
    <div style='text-align: center;'>
        <img src='https://www.tdtyres.com/wp-content/uploads/2018/12/kisspng-car-michelin-man-tire-logo-michelin-logo-5b4c286206fa03.5353854915317177300286.png' width='900'/>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    '<div class="custom-text-area title">Phone System Data Analysis</div>',
    unsafe_allow_html=True
)

# =========================
# File Upload
# =========================
st.subheader("Phone System File Upload")
phonesystem_file = st.file_uploader("Upload Phone System Data File", type=["xlsx", "xls"])

if phonesystem_file:

    with st.spinner("Processing data... Please wait."):

        # =========================
        # Load Data
        # =========================
        total_calls = pd.read_excel(phonesystem_file)
        total_calls.drop(columns=['ACW_Time'], inplace=True, errors='ignore')

        total_calls["start_date"] = pd.to_datetime(total_calls["start_date"], errors="coerce")

        total_calls["start_time"] = pd.to_datetime(
            total_calls["start_date"].astype(str) + " " +
            total_calls["start_time"].astype(str),
            errors="coerce"
        )

        total_calls.sort_values("start_time", inplace=True)

        total_calls['Total_Time'] = total_calls['Total_Time'].fillna(0)
        total_calls['team_name'] = total_calls['team_name'].fillna('No Assigned Team')

        for col in ["master_contact_id", "contact_id", "contact_name"]:
            total_calls[col] = total_calls[col].astype(str)

        # =========================
        # Spam Filter
        # =========================
        excluded_mask = (total_calls["InQueue"] == 0) & (total_calls["PreQueue"] > 0)
        spam_calls_df = total_calls.loc[excluded_mask].copy()
        excluded_calls = len(spam_calls_df)

        total_calls = total_calls.loc[~excluded_mask].copy()

        st.info(f"{excluded_calls} calls classified as spam and removed.")

        # =========================
        # Timeframe
        # =========================
        total_calls["Timeframe"] = total_calls["start_date"].dt.to_period("M").dt.to_timestamp()

        # =========================
        # Time Calculations
        # =========================
        total_calls['Agent_Work_Time'] = (
            total_calls['ACW_Seconds'].fillna(0) +
            total_calls['Agent_Time'].fillna(0)
        )

        time_cols = ['PreQueue', 'InQueue', 'Agent_Time', 'PostQueue']
        total_calls['customer_call_time'] = total_calls[time_cols].sum(axis=1)

        # =========================
        # Call Category
        # =========================
        skill_clean = (
            total_calls["skill_name"]
            .astype(str)
            .str.lower()
            .str.replace(" ", "", regex=False)
        )

        total_calls["call_category"] = np.select(
            [
                skill_clean.str.contains("afterhours", na=False),
                skill_clean.str.contains("noagent", na=False),
                skill_clean.str.contains("ib", na=False),
                skill_clean.str.contains("ob", na=False),
                skill_clean.str.contains("vm", na=False),
            ],
            [
                "After Hours",
                "No Agent",
                "Inbound",
                "Outbound",
                "Voicemail",
            ],
            default="Other"
        )

        # =========================
        # Team → Department Mapping
        # =========================
        team_to_dept = {
            'Field Services': 'Deployment',
            'Comissioning': 'Deployment',
            'SB-AM': 'Sales',
            'SDR Team': 'Sales',
            'Account Manager': 'Sales',
            'Inside Sales': 'Sales',
            'Billing': 'Billing and Collections',
            'Collections': 'Billing and Collections',
            'Business Support': 'Billing and Collections',
            'MCF Support': 'Customer Support',
            'Customer Support ATL': 'Customer Support',
            'Solutions': 'Customer Support',
            'Level 2 Support': 'Customer Support',
            'Admin': 'Technical Team',
            'Test': 'Technical Team',
            'No Assigned Team': 'Other',
            'Default Team': 'Other'
        }

        total_calls["department"] = total_calls["team_name"].map(team_to_dept).fillna("Other")

        # =========================
        # Business Hours
        # =========================
        business_hours = {
            "Customer Support": (7, 0, 18, 30),
            "Sales": (8, 0, 17, 0),
            "Billing and Collections": (8, 0, 17, 0),
            "Technical Team": (9, 0, 17, 0),
            "Other": (9, 0, 17, 0)
        }

        def is_business_hours(row):
            dep = row['department']
            call_time = row['start_time']

            if pd.isna(call_time):
                return 0

            start_h, start_m, end_h, end_m = business_hours.get(dep, (9, 0, 17, 0))

            start_dt = call_time.replace(hour=start_h, minute=start_m, second=0)
            end_dt = call_time.replace(hour=end_h, minute=end_m, second=0)

            return int(start_dt <= call_time <= end_dt)

        total_calls['Business_Hours'] = total_calls.apply(is_business_hours, axis=1)

        # =========================
        # Monthly Aggregation
        # =========================
        dfs = {}

        call_type_options = [
            "All Calls",
            "All Calls Business Hours",
            "Inbound",
            "Inbound Business Hours",
            "Voicemail",
            "Voicemail Business Hours",
            "After Hours",
            "After Hours Business Hours",
            "No Agent",
            "No Agent Business Hours"
        ]

        for option in call_type_options:

            if option == "All Calls":
                df_filtered = total_calls.copy()
            elif option == "All Calls Business Hours":
                df_filtered = total_calls[total_calls["Business_Hours"] == 1]
            elif option.endswith("Business Hours"):
                base_category = option.replace(" Business Hours", "")
                df_filtered = total_calls[
                    (total_calls["call_category"] == base_category) &
                    (total_calls["Business_Hours"] == 1)
                ]
            else:
                df_filtered = total_calls[total_calls["call_category"] == option]

            if df_filtered.empty:
                dfs[option] = pd.DataFrame()
                continue

            monthly_team_calls = (
                df_filtered
                .groupby(["team_name", "Timeframe"])
                .agg(
                    call_volume=("master_contact_id", "count"),
                    total_customer_call_time=("customer_call_time", "sum"),
                    prequeue_time=("PreQueue", "sum"),
                    inqueue_time=("InQueue", "sum"),
                    agent_time=("Agent_Time", "sum"),
                    acw_time=("ACW_Seconds", "sum"),
                    agent_total_time=("Agent_Work_Time", "sum"),
                    abandon_time=("Abandon_Time", "sum"),
                    unique_agents_count=("agent_name", "nunique"),
                    unique_skills_count=("skill_name", "nunique"),
                    unique_campaigns_count=("campaign_name", "nunique"),
                )
                .reset_index()
                .sort_values(["Timeframe", "team_name"])
            )

            dfs[option] = monthly_team_calls

        # =========================
        # Master Contact View
        # =========================
        master_contact_df = (
            total_calls
            .groupby("master_contact_id")
            .agg({
                "skill_name": lambda x: list(x.dropna().unique()),
                "contact_id": lambda x: list(x.dropna().unique()),
                "start_time": lambda x: list(x.dt.strftime("%Y-%m-%d %H:%M:%S")),
                "Timeframe": "first",
                "team_name": lambda x: list(x),
                "customer_call_time": lambda x: list(x),
            })
            .reset_index()
        )

        master_contact_df["Timeframe"] = pd.to_datetime(master_contact_df["Timeframe"], errors='coerce')
        master_contact_df["Timeframe"] = master_contact_df["Timeframe"].dt.strftime("%-m-%Y")

 # =========================
# Excel Download Section
# =========================
st.subheader("Export All Data to Excel")

if phonesystem_file is None:
    st.warning("⚠️ No data has been processed yet. Please upload a file first.")
else:
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

        for option, df in dfs.items():
            sheet_name = option[:31]
            if df.empty:
                pd.DataFrame({"No Data": []}).to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        master_contact_df.to_excel(writer, sheet_name="Master_Contacts", index=False)
        total_calls.to_excel(writer, sheet_name="Total_Calls", index=False)
        spam_calls_df.to_excel(writer, sheet_name="Spam_Calls", index=False)

    output.seek(0)

    st.download_button(
        label="Download Complete Excel Workbook",
        data=output,
        file_name="Phone_System_Analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
