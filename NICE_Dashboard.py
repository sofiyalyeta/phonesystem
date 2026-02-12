import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Phone System Data Analysis", layout="wide")

custom_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans&display=swap');

        body {
            font-family: 'Arial', 'Open Sans', sans-serif;
        }

        .custom-markdown {
            font-size: 20px;
            line-height: 1.3;
            max-width: 800px;
            width: 100%;
        }
        
        .custom-text-area {
            font-family: 'Arial', 'Open Sans', sans-serif;
            font-size: 20;
            line-height: 1.3;
            padding: 10px;
            width: 100%;
            box-sizing: border-box;
            white-space: pre-wrap;
        }
        .largish-font {
            font-size: 20px;
            font-weight: bold;
        } 

        .large-font {
            font-size: 24px;
            font-weight: bold;
        }
        
        
        .larger-font {
            font-size: 30px;
            font-weight: bold;
        }
        
        .largest-font {
            font-size: 38px;
            font-weight: bold;
        }
        
        .title {
            font-family: 'Arial', 'Open Sans', sans-serif;
            font-size: 56px;
            font-weight: bold;

        }
        .custom-text-area ul {
            margin-left: 1.2em;
            padding-left: 0;
            line-height: .95; 
        }

        .custom-text-area li {
            margin-bottom: 0.4em;
        }      
    </style>
"""


st.markdown(custom_css, unsafe_allow_html=True)


#add the Michelin banner to the top of the application, if the image link breaks you can correct this by copying and
#pasting an alternative image url in the ()
st.markdown(
    """
    <div style='text-align: center;'>
        <img src='https://www.tdtyres.com/wp-content/uploads/2018/12/kisspng-car-michelin-man-tire-logo-michelin-logo-5b4c286206fa03.5353854915317177300286.png' width='1000'/>
    </div>
    """,
    unsafe_allow_html=True
)

#set the application title to 'Phone System Data Analysis'
st.markdown('<div class="custom-text-area title">{}</div>'.format('Phone System Data Analysis'), unsafe_allow_html=True)

import streamlit as st

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



st.markdown('''<div class="custom-text-area">Insert Text Here</br> </div>
''', unsafe_allow_html=True)


st.subheader("Phone System File Upload")
phonesystem_file = st.file_uploader("Upload Phone System Data File", type=["xlsx", "xls"])



if phonesystem_file:
    with st.spinner("Processing data... Please be patient."):

        #Load data
        total_calls = pd.read_excel(phonesystem_file)


        
        #remove milliseconds after case work column
        total_calls.drop(columns =['ACW_Time'], inplace = True)
        #total_calls['Agent_Time_Mins'] = total_calls['Agent_Time'] / 60

        total_calls.sort_values("start_time", inplace=True)

        total_calls['Total_Time'] = total_calls['Total_Time'].fillna(0)
        total_calls['team_name'] = total_calls['team_name'].fillna('No Assigned Team')

        total_calls["master_contact_id"] = total_calls["master_contact_id"].astype(str)
        total_calls["contact_id"] = total_calls["contact_id"].astype(str)
        total_calls["contact_name"] = total_calls["contact_name"].astype(str)

        #filter spam
        excluded_mask = (total_calls["InQueue"] == 0) & (total_calls["PreQueue"] > 0)
        excluded_calls = excluded_mask.sum()
        total_calls = total_calls.loc[~excluded_mask]
        st.text(f"{excluded_calls} calls have been classified as spam and removed from the analysis.")


        total_calls["Timeframe"] = pd.to_datetime(
            total_calls["start_date"],
            errors="coerce")

        total_calls["Timeframe"] = total_calls["Timeframe"].dt.strftime("%b-%Y")
        #total_calls['Abandon_Mins']= total_calls['Abandon_Time'] / 60
        #total_calls['ACW_Mins'] = total_calls['ACW_Seconds'] / 60
        total_calls['Agent_Work_Time'] = pd.to_numeric(
        total_calls['ACW_Seconds'].fillna(0) + total_calls['Agent_Time'].fillna(0),
        errors='coerce'
        )


        #total_calls['Agent_Work_Mins'] = total_calls['Agent_Work_Seconds'] / 60

        total_calls["month"] = total_calls["start_date"].dt.to_period("M")
        total_calls["timeframe_period"] = pd.to_datetime(
            total_calls["Timeframe"], format="%b-%Y"
        ).dt.to_period("M")

        # Combining 'Edit Date' and 'Time' using str functions to make it a proper date/time data type
        total_calls['start_time'] = pd.to_datetime(
            total_calls['start_date'].astype(str) + " " + total_calls['start_time']. astype(str),
            format = '%Y-%m-%d %H:%M:%S'
        )# tweak this based on your actual data
 

        total_calls['customer_call_time'] = total_calls[time_cols].sum(axis=1)

        # normalize skill name and create categories for the type of call
        skill_clean = (
            total_calls["skill_name"]
                .astype(str)
                .str.lower()
                .str.replace(" ", "", regex=False)
        )
        total_calls["call_category"] = np.select(
            [   skill_clean.str.contains("afterhours", na=False),
                skill_clean.str.contains("noagent", na=False),
                skill_clean.str.contains("ib", na=False),
                skill_clean.str.contains("ob", na=False),
                skill_clean.str.contains("vm", na=False),
            ],
            [   "After Hours",
                "No Agent",
                "Inbound",
                "Outbound",
                "Voicemail",
            ],
            default="Other"
        )
        



        # Map of teams → department
        team_to_dept = {
            'Field Services': 'Deployment',
            'Comissioning': 'Deployment',

            'SB-AM': 'Sales',
            'SDR Team': 'Sales',
            'Account Manager': 'Sales',
            'Inside Sales': 'Sales',

            'Billing': 'Billing and Collections',
            'Collections': 'Billing and Collections',
            'Business Support' : 'Billing and Collections',

            'MCF Support' : 'Customer Support',
            'Customer Support ATL' : 'Customer Support',
            'Solutions' : 'Customer Support',
            'Level 2 Support' : 'Customer Support',

            'Admin' : 'Technical Team',
            'Test' : 'Technical Team',

            'No Assigned Team' : 'Other',
            'Default Team' : 'Other'
        }


        # Create new column
        total_calls['department'] = total_calls['team_name'].map(team_to_dept)

        # Example options
        teams = ["Customer Support", "Deployment", "Sales", "Billing and Collections", "Technical Team", "Other"]

        # Define static business hours for other teams
        business_hours = {
            "Customer Support": (7, 0, 18, 30),   # 7:00 AM - 6:30 PM
            "Sales": (8, 0, 17, 0),   # 8:00 AM - 5:00 PM
            "Billing and Collections": (8, 0, 17, 0),    # 8:00 AM - 5:00 PM
            'Admin' : (9, 0, 17, 0), # 9-5
            'Other' : (9, 0, 17, 0) # 9-5    
        }

        # Function to check business hours with Team A special case
        def is_business_hours(row):
            dep = row['department']
            call_time = row['start_time']

            if pd.isna(call_time):
                return 0

            # Default hours for most teams
            default_hours = (9, 0, 17, 0)  # 9:00-17:00

            if dep == "Deployment":
                cutoff_date = pd.Timestamp("2025-05-01")
                if call_time < cutoff_date:
                    if call_time.weekday() <= 4:  # Mon-Fri
                        start_h, start_m, end_h, end_m = 7, 0, 19, 0
                    elif call_time.weekday() == 5:  # Sat
                        start_h, start_m, end_h, end_m = 8, 0, 16, 0
                    else:  # Sunday
                        return 0
                else:
                    if call_time.weekday() <= 4:
                        start_h, start_m, end_h, end_m = 7, 0, 19, 0
                    else:
                        return 0
            else:
                # Use business_hours dict if available, else default
                if dep in business_hours:
                    start_h, start_m, end_h, end_m = business_hours[dep]
                else:
                    start_h, start_m, end_h, end_m = default_hours

            # Construct start and end datetime for that day
            start_dt = call_time.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
            end_dt = call_time.replace(hour=end_h, minute=end_m, second=0, microsecond=0)

            # Return 1 if inside business hours, else 0
            return int(start_dt <= call_time <= end_dt)


        # Apply the function
        total_calls['Business_Hours'] = total_calls.apply(is_business_hours, axis=1)
        st.dataframe(total_calls)

        exclude_outside_hours = st.toggle(
            "Exclude calls outside business hours?",
            value=False  # default = No
        ) 



        if exclude_outside_hours:
            original_count = len(total_calls)
            total_calls = total_calls[total_calls['Business_Hours'] == 1].copy()
            filtered_count = len(total_calls)
            excluded_count = original_count - filtered_count
            st.metric(
                label="Calls Excluded",
                value=excluded_count
            )       



        # Initialize empty dict to store results
        dfs = {
            "monthly_ib_calls": pd.DataFrame(),
            "monthly_ob_calls": pd.DataFrame(),
            "monthly_vm_calls": pd.DataFrame(),
            "monthly_ah_calls": pd.DataFrame(),
            "monthly_na_calls": pd.DataFrame()
        }

        # Map call category to dataframe name
        call_category_map = {
            "Inbound": "monthly_ib_calls",
            "Outbound": "monthly_ob_calls",
            "Voicemail": "monthly_vm_calls",
            "After Hours": "monthly_ah_calls",
            "No Agent": "monthly_na_calls"
        }

        # Loop through each category
        for category, df_name in call_category_map.items():
            df_filtered = total_calls[total_calls["call_category"] == category].copy()

            if df_filtered.empty:
                dfs[df_name] = pd.DataFrame()
                continue

            monthly_team_calls = (
                df_filtered
                .groupby(["team_name", "Timeframe"])
                .apply(lambda df: pd.Series({
                    # counts
                    "call_volume": df["master_contact_id"].count(),
                    "total_customer_call_time": df["customer_call_time"].sum(),
                    "prequeue_time": df["PreQueue"].sum(),
                    "inqueue_time": df["InQueue"].sum(),
                    "agent_time": df["Agent_Time"].sum(),
                    "acw_time": df["ACW_Seconds"].sum(),
                    "agent_total_time": df["Agent_Work_Time"].sum(),
                    "abandon_time": df["Abandon_Time"].sum(),
                    # uniques
                    "unique_agents_count": df["agent_name"].nunique(),
                    "unique_skills_count": df["skill_name"].nunique(),
                    "unique_campaigns_count": df["campaign_name"].nunique(),
                    # lists
                    "agent_list": list(df["agent_name"].dropna().unique()),
                    "skill_list": list(df["skill_name"].dropna().unique()),
                    "campaign_list": list(df["campaign_name"].dropna().unique()),
                    # case interactions
                    "case_interactions": df.groupby("master_contact_id")["contact_id"].apply(list).to_dict(),
                    # engagement time
                    "master_contact_id_start_times": df.groupby("master_contact_id")["start_time"].apply(list).to_dict(),
                    # customer contacts
                    "customer_contacts": df.groupby("contact_name").apply(lambda x: list(zip(x["DNIS"], x["start_time"]))).to_dict()
                }))
                .reset_index()
            )

            dfs[df_name] = monthly_team_calls


