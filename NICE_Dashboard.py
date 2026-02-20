import streamlit as st
import pandas as pd
import numpy as np
import io

# =========================
# Session State Initialization
# =========================
if "dfs" not in st.session_state:
    st.session_state.dfs = {}

if "skill_dfs" not in st.session_state:
    st.session_state.skill_dfs = {}

if "master_contact_df" not in st.session_state:
    st.session_state.master_contact_df = pd.DataFrame()

if "total_calls" not in st.session_state:
    st.session_state.total_calls = pd.DataFrame()

if "spam_calls_df" not in st.session_state:
    st.session_state.spam_calls_df = pd.DataFrame()

st.set_page_config(page_title="Phone System Data Analysis", layout="wide")

# =========================
# Helper Functions
# =========================

def build_internal_external_dict(group):
    internal = pd.concat([
        group.loc[group["call_category"] == "Outbound", "ANI"],
        group.loc[group["call_category"] != "Outbound", "DNIS"],
    ]).dropna()

    external = pd.concat([
        group.loc[group["call_category"] == "Outbound", "DNIS"],
        group.loc[group["call_category"] != "Outbound", "ANI"],
    ]).dropna()

    return pd.Series({
        "internal_num_dict": internal.value_counts().to_dict(),
        "external_num_dict": external.value_counts().to_dict()
    })


def build_internal_external_list(group):
    internal = pd.concat([
        group.loc[group["call_category"] == "Outbound", "ANI"],
        group.loc[group["call_category"] != "Outbound", "DNIS"],
    ]).dropna().unique().tolist()

    external = pd.concat([
        group.loc[group["call_category"] == "Outbound", "DNIS"],
        group.loc[group["call_category"] != "Outbound", "ANI"],
    ]).dropna().unique().tolist()

    return pd.Series({
        "internal_num_list": internal,
        "external_num_list": external
    })


# =========================
# File Upload
# =========================

st.subheader("Phone System File Upload")

phonesystem_file = st.file_uploader(
    "Upload Phone System Data File",
    type=["xlsx", "xls"]
)

process_button = st.button("Process New Data")

if phonesystem_file is not None and process_button:

    with st.spinner("Processing data..."):

        total_calls = pd.read_excel(phonesystem_file)
        total_calls.drop(columns=["ACW_Time"], inplace=True, errors="ignore")

        total_calls["start_date"] = pd.to_datetime(total_calls["start_date"], errors="coerce")
        total_calls["start_time"] = pd.to_datetime(
            total_calls["start_date"].astype(str) + " " +
            total_calls["start_time"].astype(str),
            errors="coerce"
        )

        total_calls.sort_values("start_time", inplace=True)

        total_calls["Total_Time"] = total_calls["Total_Time"].fillna(0)
        total_calls["team_name"] = total_calls["team_name"].fillna("No Assigned Team")

        for col in ["master_contact_id", "contact_id", "contact_name"]:
            total_calls[col] = total_calls[col].astype(str)

        # =========================
        # Spam Filter
        # =========================
        excluded_mask = (total_calls["InQueue"] == 0) & (total_calls["PreQueue"] > 0)
        spam_calls_df = total_calls.loc[excluded_mask].copy()
        total_calls = total_calls.loc[~excluded_mask].copy()

        st.info(f"{len(spam_calls_df)} calls classified as spam and removed.")

        # =========================
        # Timeframe
        # =========================
        total_calls["Timeframe"] = total_calls["start_date"].dt.to_period("M").dt.to_timestamp()

        # =========================
        # Time Calculations
        # =========================
        total_calls["Agent_Work_Time"] = (
            total_calls["ACW_Seconds"].fillna(0) +
            total_calls["Agent_Time"].fillna(0)
        )

        time_cols = ["PreQueue", "InQueue", "Agent_Time", "PostQueue"]
        total_calls["customer_call_time"] = total_calls[time_cols].sum(axis=1)

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
            dep = row["department"]
            call_time = row["start_time"]
            if pd.isna(call_time):
                return 0

            start_h, start_m, end_h, end_m = business_hours.get(dep, (9, 0, 17, 0))
            start_dt = call_time.replace(hour=start_h, minute=start_m, second=0)
            end_dt = call_time.replace(hour=end_h, minute=end_m, second=0)

            return int(start_dt <= call_time <= end_dt)

        total_calls["Business_Hours"] = total_calls.apply(is_business_hours, axis=1)

        # =========================
        # Monthly Aggregation - Team View
        # =========================
        st.session_state.dfs = {}
        call_type_options = ["All Calls", "Inbound", "Outbound", "Voicemail", "After Hours", "No Agent"]

        for option in call_type_options:

            if option == "All Calls":
                df_filtered = total_calls.copy()
            else:
                df_filtered = total_calls[total_calls["call_category"] == option]

            if df_filtered.empty:
                st.session_state.dfs[option] = pd.DataFrame()
                continue

            monthly = (
                df_filtered
                .groupby(["team_name", "department", "Timeframe"])
                .agg(
                    call_volume=("master_contact_id", "count"),
                    total_customer_call_time=("customer_call_time", "sum"),
                    agent_total_time=("Agent_Work_Time", "sum"),
                    sla_missed=("SLA", lambda x: (x == -1).sum()),
                    sla_met=("SLA", lambda x: (x == 0).sum()),
                    sla_exceeded=("SLA", lambda x: (x == 1).sum()),
                )
                .reset_index()
            )

            # Add internal/external dict
            num_df = (
                df_filtered
                .groupby(["team_name", "department", "Timeframe"])
                .apply(build_internal_external_dict)
                .reset_index()
            )

            monthly = monthly.merge(
                num_df,
                on=["team_name", "department", "Timeframe"],
                how="left"
            )

            st.session_state.dfs[option] = monthly

        # =========================
        # Master Contact View
        # =========================
        master_contact_df = (
            total_calls
            .groupby("master_contact_id")
            .agg(
                contact_id=("contact_id", lambda x: list(x.unique())),
                team_name=("team_name", lambda x: list(x.unique())),
                department=("department", lambda x: list(x.unique())),
                call_category=("call_category", lambda x: list(x.unique())),
                start_time=("start_time", lambda x: list(x.dt.strftime("%Y-%m-%d %H:%M:%S"))),
            )
            .reset_index()
        )

        num_master = (
            total_calls
            .groupby("master_contact_id")
            .apply(build_internal_external_list)
            .reset_index()
        )

        master_contact_df = master_contact_df.merge(
            num_master,
            on="master_contact_id",
            how="left"
        )

        st.session_state.master_contact_df = master_contact_df
        st.session_state.total_calls = total_calls
        st.session_state.spam_calls_df = spam_calls_df

        # =========================
        # Excel Export
        # =========================
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

            for option, df in st.session_state.dfs.items():
                sheet = f"Team - {option}"[:31]
                df.to_excel(writer, sheet_name=sheet, index=False)

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


# =========================
# File Upload
# =========================
st.subheader("Processed Phone System File Upload")

processed_file = st.file_uploader(
    "Upload Processed Phone System Data File",
    type=["xlsx", "xls"]
)

if processed_file:

    # Load ALL sheets into dictionary
    all_sheets = pd.read_excel(processed_file, sheet_name=None)

    # Store original sheets
    st.session_state.processed_sheets = all_sheets

    # =========================
    # Collect Departments From NON-Master Sheets
    # =========================
    department_set = set()

    for sheet_name, df in all_sheets.items():

        # Skip Master_Contacts (department is a list there)
        if sheet_name == "Master_Contacts":
            continue

        if "department" in df.columns:

            valid_departments = df["department"].dropna()

            # Only keep scalar string values (ignore lists)
            valid_departments = valid_departments[
                valid_departments.apply(lambda x: isinstance(x, str))
            ]

            department_set.update(valid_departments.unique())

    department_list = sorted(list(department_set))

    # Add "All" option
    department_options = ["All"] + department_list

    # =========================
    # Department Selector
    # =========================
    selected_department = st.selectbox(
        "Select Department",
        options=department_options,
        index=None,
        placeholder="Choose a department..."
    )

    exclude_outside_hours = st.toggle(
        "Exclude calls outside business hours?",
        value=False
    )

    process_filtered_button = st.button("Process Selection")

    if selected_department and process_filtered_button:

        filtered_sheets = {}

        for sheet_name, df in all_sheets.items():

            temp_df = df.copy()

            # =========================
            # Department Filtering
            # =========================
            if selected_department != "All":

                if sheet_name == "Master_Contacts" and "department" in temp_df.columns:

                    # Excel may store list column as string → convert safely
                    def contains_department(value):
                        if isinstance(value, list):
                            return selected_department in value
                        if isinstance(value, str):
                            # Handle stringified list from Excel
                            try:
                                parsed = eval(value)
                                if isinstance(parsed, list):
                                    return selected_department in parsed
                            except:
                                return value == selected_department
                        return False

                    temp_df = temp_df[
                        temp_df["department"].apply(contains_department)
                    ]

                elif "department" in temp_df.columns:
                    temp_df = temp_df[
                        temp_df["department"] == selected_department
                    ]

            # =========================
            # Business Hours Filtering
            # =========================
            if exclude_outside_hours:

                # TEAM & SKILL SHEETS → only keep Business Hours versions
                if sheet_name.startswith("Team") or sheet_name.startswith("Skill"):
                    if "Business Hours" not in sheet_name:
                        continue

                # TOTAL CALLS → row-level filter
                if sheet_name == "Total_Calls" and "Business_Hours" in temp_df.columns:
                    temp_df = temp_df[temp_df["Business_Hours"] == 1]

                # MASTER CONTACTS → use aggregated flag
                if sheet_name == "Master_Contacts" and "business_hours_flag" in temp_df.columns:
                    temp_df = temp_df[temp_df["business_hours_flag"] == 1]

            filtered_sheets[sheet_name] = temp_df

        st.session_state.filtered_sheets = filtered_sheets

        tab1, tab2, tab3, tab4 = st.tabs(["Team", "Skill", "Customer", "Phone Numbers"])

        # =========================
        # TEAM TAB
        # =========================
        with tab1:
            team_sheets = {
                name: df for name, df in filtered_sheets.items()
                if name.startswith("Team")
            }

            for name, df in team_sheets.items():
                st.subheader(name)
                st.dataframe(df, use_container_width=True)


        # =========================
        # SKILL TAB
        # =========================
        with tab2:
            skill_sheets = {
                name: df for name, df in filtered_sheets.items()
                if name.startswith("Skill")
            }

            for name, df in skill_sheets.items():
                st.subheader(name)
                st.dataframe(df, use_container_width=True)

        # =========================
        # CUSTOMER TAB
        # =========================
        with tab3:
            customer_sheets = {
                name: df for name, df in filtered_sheets.items()
                if name in ["Master_Contacts", "Total_Calls"]
            }

            for name, df in customer_sheets.items():
                st.subheader(name)
                st.dataframe(df, use_container_width=True)

        # =========================
        # PHONE NUMBER TAB
        # =========================
        with tab4:
            st.write("Phone Numbers will appear here")



with tab4:
    # =============================
    # VIEW LEVEL SELECTOR
    # =============================
    view_level = st.radio(
        "Select View Level",
        options=["Department", "Team", "Skill"],
        horizontal=True
    )

    # =============================
    # Collect Relevant Sheets
    # =============================
    team_sheets = {
        name: df for name, df in filtered_sheets.items()
        if name.startswith("Team")
    }

    skill_sheets = {
        name: df for name, df in filtered_sheets.items()
        if name.startswith("Skill")
    }

    if not team_sheets:
        st.warning("No data available.")
        st.stop()

    combined_team_df = pd.concat(team_sheets.values(), ignore_index=True)

    if skill_sheets:
        combined_skill_df = pd.concat(skill_sheets.values(), ignore_index=True)
    else:
        combined_skill_df = pd.DataFrame()

    # =============================
    # FILTER BASED ON VIEW LEVEL
    # =============================
    if view_level == "Department":

        working_df = combined_team_df

    elif view_level == "Team":

        teams = sorted(combined_team_df["team_name"].dropna().unique())

        selected_team = st.selectbox(
            "Select Team",
            options=teams
        )

        working_df = combined_team_df[
            combined_team_df["team_name"] == selected_team
        ]

    elif view_level == "Skill":

        if combined_skill_df.empty:
            st.warning("No skill-level data available.")
            st.stop()

        skills = sorted(combined_skill_df["skill_name"].dropna().unique())

        selected_skill = st.selectbox(
            "Select Skill",
            options=skills
        )

        working_df = combined_skill_df[
            combined_skill_df["skill_name"] == selected_skill
        ]

    # =============================
    # SAFETY CHECK
    # =============================
    if "internal_num_dict" not in working_df.columns:
        st.warning("Phone number data not available for this selection.")
        st.stop()

    # =============================
    # FUNCTION TO BUILD TREND DF
    # =============================
    def build_trend_dataframe(df, column_name):

        records = []

        for _, row in df.iterrows():

            timeframe = row["Timeframe"]
            num_dict = row[column_name]

            if isinstance(num_dict, str):
                num_dict = eval(num_dict)

            if isinstance(num_dict, dict):
                for number, count in num_dict.items():
                    records.append({
                        "Timeframe": timeframe,
                        "Phone_Number": number,
                        "Count": count
                    })

        trend_df = pd.DataFrame(records)

        if trend_df.empty:
            return trend_df

        return (
            trend_df
            .groupby(["Timeframe", "Phone_Number"])
            .sum()
            .reset_index()
        )

    # =============================
    # BUILD INTERNAL + EXTERNAL
    # =============================
    internal_df = build_trend_dataframe(working_df, "internal_num_dict")
    external_df = build_trend_dataframe(working_df, "external_num_dict")

    # =============================
    # INTERNAL GRAPH
    # =============================
    if not internal_df.empty:

        st.markdown("### Internal Numbers")

        top_internal = (
            internal_df
            .groupby("Phone_Number")["Count"]
            .sum()
            .sort_values(ascending=False)
            .head(20)
            .index
        )

        selected_internal = st.multiselect(
            "Select Internal Numbers",
            options=top_internal,
            default=list(top_internal[:5])
        )

        if selected_internal:

            plot_internal = internal_df[
                internal_df["Phone_Number"].isin(selected_internal)
            ]

            st.line_chart(
                plot_internal.pivot(
                    index="Timeframe",
                    columns="Phone_Number",
                    values="Count"
                )
            )

    # =============================
    # EXTERNAL GRAPH
    # =============================
    if not external_df.empty:

        st.markdown("### External Numbers")

        top_external = (
            external_df
            .groupby("Phone_Number")["Count"]
            .sum()
            .sort_values(ascending=False)
            .head(20)
            .index
        )

        selected_external = st.multiselect(
            "Select External Numbers",
            options=top_external,
            default=list(top_external[:5])
        )

        if selected_external:

            plot_external = external_df[
                external_df["Phone_Number"].isin(selected_external)
            ]

            st.line_chart(
                plot_external.pivot(
                    index="Timeframe",
                    columns="Phone_Number",
                    values="Count"
                )
            )
