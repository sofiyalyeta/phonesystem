import streamlit as st 
import pandas as pd 
import plotly.express as px 
import numpy as np 
import io


# =========================
# File Upload
# =========================
st.subheader("Phone System File Upload")

phonesystem_file = st.file_uploader(
    "Upload Phone System Data File",
    type=["xlsx", "xls"]
)

if phonesystem_file is not None and "processed" not in st.session_state:

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
        # Spam Filter (Vectorized)
        # =========================
        excluded_mask = (total_calls["InQueue"] == 0) & (total_calls["PreQueue"] > 0)
        spam_calls_df = total_calls.loc[excluded_mask].copy()
        total_calls = total_calls.loc[~excluded_mask].copy()

        st.info(f"{len(spam_calls_df)} calls classified as spam and removed.")

        # =========================
        # Timeframe
        # =========================
        total_calls["Timeframe"] = (
            total_calls["start_date"]
            .dt.to_period("M")
            .dt.to_timestamp()
        )

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
        # Call Category (Vectorized)
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
        # Precompute Indicator Columns (FAST)
        # =========================
        total_calls["sla_missed"] = (total_calls["SLA"] == -1).astype(int)
        total_calls["sla_met"] = (total_calls["SLA"] == 0).astype(int)
        total_calls["sla_exceeded"] = (total_calls["SLA"] == 1).astype(int)

        total_calls["is_inbound"] = (total_calls["call_category"] == "Inbound").astype(int)
        total_calls["is_outbound"] = (total_calls["call_category"] == "Outbound").astype(int)
        total_calls["is_voicemail"] = (total_calls["call_category"] == "Voicemail").astype(int)
        total_calls["is_afterhours"] = (total_calls["call_category"] == "After Hours").astype(int)
        total_calls["is_noagent"] = (total_calls["call_category"] == "No Agent").astype(int)

        # =========================
        # Department Mapping
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

        # =========================
        # Business Hours (Vectorized)
        # =========================
        total_calls["hour"] = total_calls["start_time"].dt.hour
        total_calls["minute"] = total_calls["start_time"].dt.minute

        total_calls["Business_Hours"] = 0

        # Customer Support
        mask = (total_calls["department"] == "Customer Support")
        total_calls.loc[mask & 
            ((total_calls["hour"] > 7) |
            ((total_calls["hour"] == 7) & (total_calls["minute"] >= 0))) &
            ((total_calls["hour"] < 18) |
            ((total_calls["hour"] == 18) & (total_calls["minute"] <= 30))),
            "Business_Hours"] = 1

        # All other departments (8–5)
        mask = total_calls["department"] != "Customer Support"
        total_calls.loc[mask &
            (total_calls["hour"] >= 8) &
            (total_calls["hour"] < 17),
            "Business_Hours"] = 1

        # =========================
        # Monthly Aggregation (FAST GROUPBY)
        # =========================
        dfs = {}

        call_type_filters = {
            "All Calls": total_calls,
            "All Calls Business Hours": total_calls[total_calls["Business_Hours"] == 1],
            "Inbound": total_calls[total_calls["is_inbound"] == 1],
            "Inbound Business Hours": total_calls[(total_calls["is_inbound"] == 1) & (total_calls["Business_Hours"] == 1)],
            "Voicemail": total_calls[total_calls["is_voicemail"] == 1],
            "After Hours": total_calls[total_calls["is_afterhours"] == 1],
            "No Agent": total_calls[total_calls["is_noagent"] == 1],
        }

        for name, df_filtered in call_type_filters.items():

            if df_filtered.empty:
                dfs[name] = pd.DataFrame()
                continue

            monthly = (
                df_filtered
                .groupby(["team_name", "department", "Timeframe"], observed=True)
                .agg(
                    call_volume=("master_contact_id", "count"),
                    total_customer_call_time=("customer_call_time", "sum"),
                    agent_total_time=("Agent_Work_Time", "sum"),
                    abandon_time=("Abandon_Time", "sum"),
                    sla_missed=("sla_missed", "sum"),
                    sla_met=("sla_met", "sum"),
                    sla_exceeded=("sla_exceeded", "sum"),
                    inbound_calls=("is_inbound", "sum"),
                    outbound_calls=("is_outbound", "sum"),
                    voicemail_calls=("is_voicemail", "sum"),
                    afterhours_calls=("is_afterhours", "sum"),
                    noagent_calls=("is_noagent", "sum"),
                    unique_agents=("agent_name", "nunique"),
                )
                .reset_index()
            )

            monthly["Timeframe"] = monthly["Timeframe"].dt.strftime("%-m-%Y")
            dfs[name] = monthly

        # =========================
        # Master Contact View
        # =========================
        master_contact_df = (
            total_calls
            .groupby("master_contact_id", observed=True)
            .agg(
                call_count=("contact_id", "count"),
                first_call=("start_time", "min"),
                last_call=("start_time", "max"),
                total_time=("customer_call_time", "sum"),
            )
            .reset_index()
        )

        # =========================
        # Store in Session State
        # =========================
        st.session_state["dfs"] = dfs
        st.session_state["master_contact_df"] = master_contact_df
        st.session_state["total_calls"] = total_calls
        st.session_state["spam_calls_df"] = spam_calls_df
        st.session_state["processed"] = True

        st.success("Processing complete!")

# =========================
# Excel Download
# =========================
st.subheader("Export All Data to Excel")

if "dfs" not in st.session_state:
    st.warning("⚠️ Please upload a file to process first.")
else:

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

        for option, df in st.session_state["dfs"].items():
            sheet_name = option[:31]
            if df.empty:
                pd.DataFrame({"No Data": []}).to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        st.session_state["master_contact_df"].to_excel(writer, sheet_name="Master_Contacts", index=False)
        st.session_state["total_calls"].to_excel(writer, sheet_name="Total_Calls", index=False)
        st.session_state["spam_calls_df"].to_excel(writer, sheet_name="Spam_Calls", index=False)

    output.seek(0)

    st.download_button(
        label="Download Complete Excel Workbook",
        data=output,
        file_name="Phone_System_Analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

