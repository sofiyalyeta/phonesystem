import streamlit as st
import pandas as pd
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
        total_calls['Agent_Time_Mins'] = total_calls['Agent_Time'] / 60
        total_calls.sort_values("start_time", inplace=True)

        total_calls['Total_Time'] = total_calls['Total_Time'].fillna(0)
        total_calls['team_name'] = total_calls['team_name'].fillna('No Assigned Team')

        #filter spam
        excluded_mask = (total_calls["InQueue"] == 0) & (total_calls["PreQueue"] > 0)
        excluded_calls = excluded_mask.sum()
        total_calls = total_calls.loc[~excluded_mask]
        st.text(f"{excluded_calls} calls have been classified as spam and removed from the analysis.")

        total_calls['start_time'] = pd.to_datetime(total_calls['start_time'], errors='coerce')

        total_calls["Timeframe"] = pd.to_datetime(
            total_calls["start_date"],
            errors="coerce"
        )
        total_calls["Timeframe"] = total_calls["Timeframe"].dt.strftime("%b-%Y")
        total_calls['Abandon_Mins']= total_calls['Abandon_Time'] / 60
        total_calls['ACW_Mins'] = total_calls['ACW_Seconds'] / 60
        total_calls['Agent_Work_Seconds'] = total_calls['ACW_Seconds'] + total_calls['Agent_Time']
        total_calls['Agent_Work_Mins'] = total_calls['Agent_Work_Seconds'] / 60

        # normalize skill name and create categories for the type of call
        skill_clean = (
            total_calls["skill_name"]
                .astype(str)
                .str.lower()
                .str.replace(" ", "", regex=False)
        )
        total_calls["call_category"] = np.select(
            [
                skill_clean.str.contains("noagent", na=False),
                skill_clean.str.contains("ib", na=False),
                skill_clean.str.contains("ob", na=False),
                skill_clean.str.contains("vm", na=False),
            ],
            [
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
            ''
        }


        # Create new column
        total_calls['department'] = total_calls['team_name'].map(team_to_dept)


        # Example options
        teams = ["Customer Support", "Deployment", "Sales", "Billing and Collections", "Technical Team", "Other"]

        # Multi-select widget
        selected_teams = st.multiselect(
            "Select team to view calls for:",  # Label
            options=teams,                     # Options list
            default=["Customer Support", "Deployment", "Sales", "Billing and Collections", "Technical Team", "Other"]     # default selection
        )

        # Display the selection
        st.write("You selected:", selected_teams)


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
            
            # Team A special rules
            if dep == "Deployment":
                cutoff_date = pd.Timestamp("2025-05-01")
                if call_time < cutoff_date:
                    # Before May 2025
                    if call_time.weekday() <= 4:  # Monday-Friday
                        start_h, start_m, end_h, end_m = 7, 0, 19, 0
                    elif call_time.weekday() == 5:  # Saturday
                        start_h, start_m, end_h, end_m = 8, 0, 16, 0
                    else:  # Sunday
                        return 0
                else:
                    # May 2025 onward, no Saturday coverage
                    if call_time.weekday() <= 4:  # Monday-Friday
                        start_h, start_m, end_h, end_m = 7, 0, 19, 0
                    else:
                        return 0
            elif dep in business_hours:
                if call_time.weekday() > 4:  # No weekend coverage for other teams
                    return 0
                start_h, start_m, end_h, end_m = business_hours[dep]
            else:
                return 0  # Default: unknown department is outside business hours

            # Construct start and end time for the call day
            start_time = call_time.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
            end_time = call_time.replace(hour=end_h, minute=end_m, second=0, microsecond=0)

            return int(start_time <= call_time <= end_time)

        # Apply the function
        total_calls['Business_Hours'] = total_calls.apply(is_business_hours, axis=1)

        if st.button("Exclude calls outside business hours?"):
            # Keep only calls within business hours
            total_calls = total_calls[total_calls['Business_Hours'] == 1].copy()


        # Multi-select widget types of calls
        default_calls = [c for c in ["No Agent", "Inbound", "Outbound", "Voicemail", "Other"] if c in teams]

        selected_calls = st.multiselect(
            "Select call types:",
            options=default_calls,
        )


        st.dataframe(total_calls)


        # Filter based on selection and business hours
        filtered_calls = total_calls[
            (total_calls['department'].isin(selected_teams)) &
            (total_calls['call_category'].isin(selected_calls))
        ]


        category_counts = (
            filtered_calls
                .groupby(["team_name", "Timeframe", "call_category"])
                .size()
                .unstack(fill_value=0)
                .reset_index()
        )

        # create main source dataframe
        monthly_team_calls = (
            filtered_calls
                .groupby(["team_name", "Timeframe"])
                .agg(
                    # counts / metrics
                    call_volume=('master_contact_id', 'count'),
                    prequeue_time=('PreQueue', 'sum'),
                    inqueue_time=('InQueue', 'sum'),
                    agent_time=('Agent_Time', 'sum'),
                    acw_time=('ACW_Seconds', 'sum'),
                    abandon_time=('Abandon_Time', 'sum'),
                    total_calls_time=('Total_Time', 'sum'),
                    unique_agents_count=('agent_name', 'nunique'),
                    unique_skills_count=('skill_name', 'nunique'),
                    unique_campaigns_count=('campaign_name', 'nunique'),

                    # lists of unique values
                    agent_list=('agent_name', lambda x: list(x.dropna().unique())),
                    skill_list=('skill_name', lambda x: list(x.dropna().unique())),
                    campaign_list=('campaign_name', lambda x: list(x.dropna().unique())),

                    # NEW: customer contacts as (name, call_count)
                    Customer_Contacts=(
                        'contact_name',
                        lambda x: list(x.value_counts().items())
                    )
                )
                .reset_index()
        )

        monthly_team_calls = monthly_team_calls.merge(
            category_counts,
            on=["team_name", "Timeframe"],
            how="left"
        )

        display_df = monthly_team_calls.copy()

        list_cols = ['agent_list', 'skill_list', 'campaign_list', 'Customer_Contacts']

        for col in list_cols:
            display_df[col] = display_df[col].apply(lambda x: ", ".join(map(str, x)) if isinstance(x, list) else "")

        st.dataframe(display_df)



        # ib_category_counts = (
        #     inbound_df
        #         .groupby(["team_name", "Timeframe", "call_category"])
        #         .size()
        #         .unstack(fill_value=0)
        #         .reset_index()
        # )
        # ob_category_counts = (
        #     outbound_df
        #         .groupby(["team_name", "Timeframe", "call_category"])
        #         .size()
        #         .unstack(fill_value=0)
        #         .reset_index()
        # )
        # vm_category_counts = (
        #     vm_df
        #         .groupby(["team_name", "Timeframe", "call_category"])
        #         .size()
        #         .unstack(fill_value=0)
        #         .reset_index()
        # )
        # na_category_counts = (
        #     na_df
        #         .groupby(["team_name", "Timeframe", "call_category"])
        #         .size()
        #         .unstack(fill_value=0)
        #         .reset_index()
        # )
        # other_category_counts = (
        #     other_df
        #         .groupby(["team_name", "Timeframe", "call_category"])
        #         .size()
        #         .unstack(fill_value=0)
        #         .reset_index()
        # )
        # category_counts = (
        #     total_calls
        #         .groupby(["team_name", "Timeframe", "call_category"])
        #         .size()
        #         .unstack(fill_value=0)
        #         .reset_index()
        # )
        # category_counts
        # category_count_dfs = [ib_category_counts, vm_category_counts, na_category_counts, category_counts]


        # #add button option to filter out calls that happened outside of business hours
        # if st.button("Exclude calls outside business hours?"):
        #     # Make sure 'start_time' is datetime
        #     total_calls['start_time'] = pd.to_datetime(total_calls['start_time'])

        #     # Define working hours
        #     start_hour = 7          # 7:00 AM
        #     end_hour = 18           # 6:30 PM = 18:30
        #     end_minute = 30

        #     # Filter within working hours
        #     total_calls = total_calls[
        #         ((total_calls['start_time'].dt.hour > start_hour) |
        #         ((total_calls['start_time'].dt.hour == start_hour))) &
        #         ((total_calls['start_time'].dt.hour < end_hour) |
        #         ((total_calls['start_time'].dt.hour == end_hour) &
        #         (total_calls['start_time'].dt.minute <= end_minute)))
        #     ]

        #     st.success("Calls outside business hours (7:00 AM – 6:30 PM) have been removed.")


        # monthly_team_calls = (
        #     total_calls
        #         .groupby(["team_name", "Timeframe"])
        #         .agg(
        #             # counts / metrics
        #             call_volume=('master_contact_id', 'count'),
        #             prequeue_time=('PreQueue', 'sum'),
        #             inqueue_time=('InQueue', 'sum'),
        #             agent_time=('Agent_Time', 'sum'),
        #             acw_time=('ACW_Seconds', 'sum'),
        #             abandon_time=('Abandon_Time', 'sum'),
        #             total_calls_time=('Total_Time', 'sum'),
        #             unique_agents_count=('agent_name', 'nunique'),
        #             unique_skills_count=('skill_name', 'nunique'),
        #             unique_campaigns_count=('campaign_name', 'nunique'),
        #             unique_DNIS_count=('DNIS', 'nunique'),
        #             unique_ANI_count=('ANI', 'nunique'),


        #             # lists of unique values
        #             agent_list=('agent_name', lambda x: list(x.dropna().unique())),
        #             skill_list=('skill_name', lambda x: list(x.dropna().unique())),
        #             campaign_list=('campaign_name', lambda x: list(x.dropna().unique())),

        #             # customer contacts as (name, call_count)
        #             Customer_Contacts=(
        #                 'contact_name',
        #                 lambda x: list(x.value_counts().items())
        #             )
        #         )
        #         .reset_index()
        # )













# total_calls['Agent_Time_Mins'] = total_calls['Agent_Time'] / 60

# total_calls['Abandon_Mins']= total_calls['Abandon_Time'] / 60
# total_calls['ACW_Mins'] = total_calls['ACW_Seconds'] / 60
# total_calls['Agent_Work_Seconds'] = total_calls['ACW_Seconds'] + total_calls['Agent_Time']
# total_calls['Agent_Work_Mins'] = total_calls['Agent_Work_Seconds'] / 60


# monthly_team_calls = monthly_team_calls.merge(
#     category_counts,
#     on=["team_name", "Timeframe"],
#     how="left"
# )

# monthly_team_calls.columns



#         inbound_df = total_calls[total_calls["call_category"] == "Inbound"].copy()
#         outbound_df = total_calls[total_calls["call_category"] == "Outbound"].copy()
#         vm_df = total_calls[total_calls["call_category"] == "Voicemail"].copy()
#         na_df = total_calls[total_calls["call_category"] == "No Agent"].copy()
#         other_df = total_calls[total_calls["call_category"] == "Other"].copy()
#         call_df_list = [total_calls, inbound_df, outbound_df, vm_df, na_df, other_df]
#         call_df_names = ['All Calls', 'Inbound Calls', 'Outbound Calls', 'Voicemails', 'No Agent', 'Other']



# call_df_names = ['All Calls', 'Inbound Calls', 'Outbound Calls', 'Voicemails', 'No Agent', 'Other']



# call_df_list = [total_calls, inbound_df, outbound_df, vm_df, na_df, other_df]



