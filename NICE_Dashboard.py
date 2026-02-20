
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io

# =========================
# Session State Initialization
# =========================
if "dfs" not in st.session_state:
    st.session_state.dfs = {}

if "master_contact_df" not in st.session_state:
    st.session_state.master_contact_df = pd.DataFrame()

if "total_calls" not in st.session_state:
    st.session_state.total_calls = pd.DataFrame()

if "spam_calls_df" not in st.session_state:
    st.session_state.spam_calls_df = pd.DataFrame()

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



st.header("Data Legend")

# Contact & Identification
st.subheader("Contact & Identification")
st.text("""
contact_id: Unique identifier for the individual interaction
master_contact_id: Identifier linking related interactions (transfers, callbacks)
media_name: Interaction channel (Voice, Chat, Email, SMS)
contact_name: Friendly name or label for the interaction
ANI: Caller phone number (Automatic Number Identification)
DNIS: Dialed phone number (Dialed Number Identification Service)
""")

# Skill & Routing
st.subheader("Skill & Routing")
st.text("""
skill_no: Numeric ID of the routing skill
skill_name: Name of the routing skill
campaign_no: Campaign identifier
campaign_name: Campaign name
""")

# Agent & Team
st.subheader("Agent & Team")
st.text("""
agent_no: Agent system ID
agent_name: Agent display name
team_no: Team identifier
team_name: Team name
""")

# Service Level
st.subheader("Service Level")
st.text("""
SLA: Service level indicator (met or not met)
""")

# Date & Time
st.subheader("Date & Time")
st.text("""
start_date: Date the interaction started
start_time: Time the interaction started
""")

# Queue & Handling Time
st.subheader("Queue & Handling Time")
st.text("""
PreQueue: Time spent in IVR or routing before entering queue
InQueue: Time spent waiting in queue
Agent_Time: Time agent actively handled the interaction
PostQueue: Time after leaving queue before wrap-up
Total_Time: Total duration of the interaction
Abandon_Time: Time elapsed before customer abandoned
abandon: Abandon flag (1 = abandoned, 0 = handled)
""")

# After Call Work
st.subheader("After Call Work (ACW)")
st.text("""
ACW_Seconds: After Call Work duration in seconds
ACW_Time: After Call Work duration formatted as time
""")




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
        st.session_state.dfs = {}

        call_type_options = [
            "All Calls",
            "All Calls Business Hours",
            "Inbound",
            "Inbound Business Hours",
            "Outbound",
            "Outbound Business Hours",
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
                st.session_state.dfs[option] = pd.DataFrame()
                continue
            monthly_team_calls = (
                df_filtered
                .groupby(["team_name", "department", "Timeframe"])
                .agg(
                    call_volume=("master_contact_id", "count"),

                    # Time Sums
                    total_customer_call_time=("customer_call_time", "sum"),
                    prequeue_time=("PreQueue", "sum"),
                    inqueue_time=("InQueue", "sum"),
                    agent_time=("Agent_Time", "sum"),
                    postqueue_time=("PostQueue", "sum"),
                    acw_time=("ACW_Seconds", "sum"),
                    agent_total_time=("Agent_Work_Time", "sum"),
                    abandon_time=("Abandon_Time", "sum"),

                    # SLA Counts
                    sla_missed=("SLA", lambda x: (x == -1).sum()),
                    sla_met=("SLA", lambda x: (x == 0).sum()),
                    sla_exceeded=("SLA", lambda x: (x == 1).sum()),

                    # Business Hours Counts
                    business_hours_calls=("Business_Hours", lambda x: (x == 1).sum()),
                    after_hours_calls=("Business_Hours", lambda x: (x == 0).sum()),

                    # Unique Counts
                    unique_agents_count=("agent_name", "nunique"),
                    unique_skills_count=("skill_name", "nunique"),
                    unique_campaigns_count=("campaign_name", "nunique"),

                    # Lists and dicts
                    agents_list=("agent_name", lambda x: list(x.dropna().unique())),
                    skills_list=("skill_name", lambda x: list(x.dropna().unique())),
                    campaigns_list=("campaign_name", lambda x: list(x.dropna().unique())),
                    internal_num_dict=(
                        ["ANI", "DNIS", "call_category"],
                        lambda x: (
                            pd.concat([
                                # Outbound → ANI is internal
                                x.loc[x["call_category"] == "Outbound", "ANI"],
                                # Non-Outbound → DNIS is internal
                                x.loc[x["call_category"] != "Outbound", "DNIS"],
                            ])
                            .dropna()
                            .value_counts()
                            .to_dict()
                        )
                    ),

                    external_num_dict=(
                        ["ANI", "DNIS", "call_category"],
                        lambda x: (
                            pd.concat([
                                # Outbound → DNIS is external
                                x.loc[x["call_category"] == "Outbound", "DNIS"],
                                # Non-Outbound → ANI is external
                                x.loc[x["call_category"] != "Outbound", "ANI"],
                            ])
                            .dropna()
                            .value_counts()
                            .to_dict()
                        )
                    ),


                    # Call Category Counts
                    inbound_calls=("call_category", lambda x: (x == "Inbound").sum()),
                    outbound_calls=("call_category", lambda x: (x == "Outbound").sum()),
                    voicemail_calls=("call_category", lambda x: (x == "Voicemail").sum()),
                    afterhours_calls=("call_category", lambda x: (x == "After Hours").sum()),
                    noagent_calls=("call_category", lambda x: (x == "No Agent").sum()),
                    other_calls=("call_category", lambda x: (x == "Other").sum()),
                )
                .reset_index()
                .sort_values(["Timeframe", "team_name"])
            )

            monthly_team_calls["Timeframe"] = pd.to_datetime(
                monthly_team_calls["Timeframe"], errors="coerce"
            )

            monthly_team_calls["Timeframe"] = monthly_team_calls["Timeframe"].dt.strftime("%-m-%Y")

            st.session_state.dfs[option] = monthly_team_calls

        # =========================
        # Monthly Aggregation - Skill View
        # =========================
        st.session_state.skill_dfs = {}

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
                st.session_state.skill_dfs[option] = pd.DataFrame()
                continue

            monthly_skill_calls = (
                df_filtered
                .groupby(["skill_name", "department", "Timeframe"])
                .agg(
                    call_volume=("master_contact_id", "count"),

                    total_customer_call_time=("customer_call_time", "sum"),
                    prequeue_time=("PreQueue", "sum"),
                    inqueue_time=("InQueue", "sum"),
                    agent_time=("Agent_Time", "sum"),
                    postqueue_time=("PostQueue", "sum"),
                    acw_time=("ACW_Seconds", "sum"),
                    agent_total_time=("Agent_Work_Time", "sum"),
                    abandon_time=("Abandon_Time", "sum"),

                    sla_missed=("SLA", lambda x: (x == -1).sum()),
                    sla_met=("SLA", lambda x: (x == 0).sum()),
                    sla_exceeded=("SLA", lambda x: (x == 1).sum()),

                    business_hours_calls=("Business_Hours", lambda x: (x == 1).sum()),
                    after_hours_calls=("Business_Hours", lambda x: (x == 0).sum()),

                    unique_agents_count=("agent_name", "nunique"),
                    unique_teams_count=("team_name", "nunique"),
                    unique_campaigns_count=("campaign_name", "nunique"),

                    agents_list=("agent_name", lambda x: list(x.dropna().unique())),
                    teams_list=("team_name", lambda x: list(x.dropna().unique())),
                    campaigns_dict=("campaign_name", lambda x: x.value_counts().to_dict()),
                    internal_num_dict=(
                        ["ANI", "DNIS", "call_category"],
                        lambda x: (
                            pd.concat([
                                x.loc[x["call_category"] == "Outbound", "ANI"],
                                x.loc[x["call_category"] != "Outbound", "DNIS"],
                            ])
                            .dropna()
                            .value_counts()
                            .to_dict()
                        )
                    ),

                    external_num_dict=(
                        ["ANI", "DNIS", "call_category"],
                        lambda x: (
                            pd.concat([
                                x.loc[x["call_category"] == "Outbound", "DNIS"],
                                x.loc[x["call_category"] != "Outbound", "ANI"],
                            ])
                            .dropna()
                            .value_counts()
                            .to_dict()
                        )
                    ),



                    inbound_calls=("call_category", lambda x: (x == "Inbound").sum()),
                    outbound_calls=("call_category", lambda x: (x == "Outbound").sum()),
                    voicemail_calls=("call_category", lambda x: (x == "Voicemail").sum()),
                    afterhours_calls=("call_category", lambda x: (x == "After Hours").sum()),
                    noagent_calls=("call_category", lambda x: (x == "No Agent").sum()),
                    other_calls=("call_category", lambda x: (x == "Other").sum()),
                )
                .reset_index()
                .sort_values(["Timeframe", "skill_name"])
            )

            monthly_skill_calls["Timeframe"] = pd.to_datetime(
                monthly_skill_calls["Timeframe"], errors="coerce"
            )

            monthly_skill_calls["Timeframe"] = monthly_skill_calls["Timeframe"].dt.strftime("%-m-%Y")

            st.session_state.skill_dfs[option] = monthly_skill_calls



        # =========================
        # Master Contact View
        # =========================
        master_contact_df = (
            total_calls
            .groupby("master_contact_id")
            .agg(
                # Identifiers
                contact_id=("contact_id", lambda x: list(x.dropna().unique())),
        
                # Timing Columns (as lists)
                PreQueue=("PreQueue", lambda x: list(x.fillna(0))),
                InQueue=("InQueue", lambda x: list(x.fillna(0))),
                Agent_Time=("Agent_Time", lambda x: list(x.fillna(0))),
                ACW_Seconds=("ACW_Seconds", lambda x: list(x.fillna(0))),
                PostQueue=("PostQueue", lambda x: list(x.fillna(0))),
        
                # Call Info
                skill_name=("skill_name", lambda x: list(x.dropna().unique())),
                team_name=("team_name", lambda x: list(x.dropna().unique())),
                department=("department", lambda x: list(x.dropna().unique())),
                agent_name=("agent_name", lambda x: list(x.dropna().unique())),
                call_category=("call_category", lambda x: list(x.dropna().unique())),
        
                # Phone Info
                internal_num_list=(
                    ["ANI", "DNIS", "call_category"],
                    lambda x: (
                        pd.concat([
                            # Outbound → ANI is internal
                            x.loc[x["call_category"] == "Outbound", "ANI"],

                            # Non-Outbound → DNIS is internal
                            x.loc[x["call_category"] != "Outbound", "DNIS"],
                        ])
                        .dropna()
                        .unique()
                        .tolist()
                    )
                ),

                external_num_list=(
                    ["ANI", "DNIS", "call_category"],
                    lambda x: (
                        pd.concat([
                            # Outbound → DNIS is external
                            x.loc[x["call_category"] == "Outbound", "DNIS"],

                            # Non-Outbound → ANI is external
                            x.loc[x["call_category"] != "Outbound", "ANI"],
                        ])
                        .dropna()
                        .unique()
                        .tolist()
                    )
                ),
        
                # SLA Counts
                sla_missed=("SLA", lambda x: (x == -1).sum()),
                sla_met=("SLA", lambda x: (x == 0).sum()),
                sla_exceeded=("SLA", lambda x: (x == 1).sum()),

                # Business Hours
                business_hours_flag=("Business_Hours", lambda x: int((x == 1).any())),
                business_hours_list=("Business_Hours", lambda x: list(x.fillna(0))),
        
                # Dates
                start_time=("start_time", lambda x: list(x.dt.strftime("%Y-%m-%d %H:%M:%S"))),
                Timeframe=("Timeframe", "first"),
        
                # Optional: total customer time per interaction
                customer_call_time=("customer_call_time", lambda x: list(x.fillna(0))),
                agent_total_time = ('Agent_Work_Time', lambda x: list(x.fillna(0))),
            )
            .reset_index()
        )


        master_contact_df["Timeframe"] = pd.to_datetime(
            master_contact_df["Timeframe"], errors="coerce"
        )
        master_contact_df["Timeframe"] = master_contact_df["Timeframe"].dt.strftime("%-m-%Y")




        st.session_state.master_contact_df = master_contact_df
        st.session_state.total_calls = total_calls
        st.session_state.spam_calls_df = spam_calls_df


        # =========================
        # Excel Download Section
        # =========================
        st.subheader("Export All Data to Excel")

        output = io.BytesIO()
        # =========================
        # Dynamic File Name
        # =========================
        if not st.session_state.total_calls.empty:

            first_month = (
                st.session_state.total_calls["start_date"]
                .min()
                .strftime("%b-%Y")
            )

            last_month = (
                st.session_state.total_calls["start_date"]
                .max()
                .strftime("%b-%Y")
            )

            dynamic_filename = f"Phone_System_Analysis_{first_month}_to_{last_month}.xlsx"

        else:
            dynamic_filename = "Phone_System_Analysis.xlsx"

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

            # =========================
            # TEAM VIEW SHEETS
            # =========================
            for option, df in st.session_state.dfs.items():
                sheet_name = f"Team - {option}"[:31]
                if df.empty:
                    pd.DataFrame({"No Data": []}).to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            # =========================
            # SKILL VIEW SHEETS
            # =========================
            for option, df in st.session_state.skill_dfs.items():
                sheet_name = f"Skill - {option}"[:31]
                if df.empty:
                    pd.DataFrame({"No Data": []}).to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            # =========================
            # DETAIL SHEETS
            # =========================
            st.session_state.master_contact_df.to_excel(writer, sheet_name="Master_Contacts", index=False)
            st.session_state.total_calls.to_excel(writer, sheet_name="Total_Calls", index=False)
            st.session_state.spam_calls_df.to_excel(writer, sheet_name="Spam_Calls", index=False)


        output.seek(0)

        st.download_button(
            label="Download Complete Excel Workbook",
            data=output,
            file_name=dynamic_filename,
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
