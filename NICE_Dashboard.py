import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

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

        # Safe column drop
        total_calls.drop(columns=['ACW_Time'], inplace=True, errors='ignore')

        # Ensure datetime format
        total_calls["start_date"] = pd.to_datetime(
            total_calls["start_date"], errors="coerce"
        )

        # Combine start_date + start_time safely
        total_calls["start_time"] = pd.to_datetime(
            total_calls["start_date"].astype(str) + " " +
            total_calls["start_time"].astype(str),
            errors="coerce"
        )

        total_calls.sort_values("start_time", inplace=True)

        # Fill missing values
        total_calls['Total_Time'] = total_calls['Total_Time'].fillna(0)
        total_calls['team_name'] = total_calls['team_name'].fillna('No Assigned Team')

        # Convert IDs to string
        for col in ["master_contact_id", "contact_id", "contact_name"]:
            total_calls[col] = total_calls[col].astype(str)

        # =========================
        # Spam Filter
        # =========================
        excluded_mask = (total_calls["InQueue"] == 0) & (total_calls["PreQueue"] > 0)
        excluded_calls = excluded_mask.sum()
        total_calls = total_calls.loc[~excluded_mask]

        st.info(f"{excluded_calls} calls classified as spam and removed.")

        # =========================
        # Timeframe (Clean Version)
        # =========================
        total_calls["Timeframe"] = total_calls["start_date"].dt.to_period("M")

        # =========================
        # Agent Work Time
        # =========================
        total_calls['Agent_Work_Time'] = (
            total_calls['ACW_Seconds'].fillna(0) +
            total_calls['Agent_Time'].fillna(0)
        )

        # =========================
        # Customer Call Time
        # =========================
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

        total_calls["department"] = (
            total_calls["team_name"]
            .map(team_to_dept)
            .fillna("Other")
        )
        total_calls["Timeframe"] = (
            total_calls["start_date"].dt.month.astype(str)
            + "-"
            + total_calls["start_date"].dt.year.astype(str)
        )

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

            if dep in business_hours:
                start_h, start_m, end_h, end_m = business_hours[dep]
            else:
                start_h, start_m, end_h, end_m = (9, 0, 17, 0)

            start_dt = call_time.replace(hour=start_h, minute=start_m, second=0)
            end_dt = call_time.replace(hour=end_h, minute=end_m, second=0)

            return int(start_dt <= call_time <= end_dt)

        total_calls['Business_Hours'] = total_calls.apply(is_business_hours, axis=1)

        # =========================
        # Toggle Filter
        # =========================
        exclude_outside_hours = st.toggle(
            "Exclude calls outside business hours?",
            value=False
        )

        if exclude_outside_hours:
            total_calls = total_calls[total_calls['Business_Hours'] == 1]

        # =========================
        # Monthly Aggregation by Category
        # =========================
        dfs = {}
        call_category_map = {
            "Inbound": "monthly_ib_calls",
            "Outbound": "monthly_ob_calls",
            "Voicemail": "monthly_vm_calls",
            "After Hours": "monthly_ah_calls",
            "No Agent": "monthly_na_calls"
        }

        for category, df_name in call_category_map.items():

            df_filtered = total_calls[
                total_calls["call_category"] == category
            ].copy()

            if df_filtered.empty:
                dfs[df_name] = pd.DataFrame()
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
        
                #Lists of unique values
                unique_agents_list=("agent_name", lambda x: list(x.unique())),
                unique_skills_list=("skill_name", lambda x: list(x.unique())),
                unique_campaigns_list=("campaign_name", lambda x: list(x.unique())),
            )
            .reset_index()
        )
        
        dfs[df_name] = monthly_team_calls

        # =========================
        # Display Results
        # =========================
        for category, df_name in call_category_map.items():
            st.subheader(f"{category} Calls")
            if dfs[df_name].empty:
                st.write("No data available.")
            else:
                st.dataframe(dfs[df_name])

        # =========================
        # Master Contact View
        # =========================
        master_contact_df = (
            total_calls
            .groupby("master_contact_id")
            .agg({
                "skill_name": lambda x: list(x.dropna().unique()),
                "contact_id": lambda x: list(x.dropna().unique()),
                "start_time": lambda x: list(
                    x.dt.strftime("%Y-%m-%d %H:%M:%S")
                ),
                "Timeframe": "first",
                "team_name": lambda x: list(x),
            })
            .reset_index()
            .rename(columns={
                "skill_name": "contacted_skills",
                "contact_id": "contact_ids",
                "start_time": "contact_times",
                "team_name": "contacted_teams",
            })
        )


        st.subheader("Master Contact View")
        st.dataframe(master_contact_df)




