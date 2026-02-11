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

        # Multi-select widget
        selected_teams = st.multiselect(
            "Select team to view calls for:",  # Label
            options=teams,                     # Options list
            default=["Customer Support", "Deployment", "Sales", "Billing and Collections", "Technical Team", "Other"]     # default selection
        )


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

        selected_calls = st.multiselect(
            "Select call types:",
            options= ["After Hours","No Agent", "Inbound", "Outbound", "Voicemail", "Other"],
            default = ["After Hours","No Agent", "Inbound", "Outbound", "Voicemail", "Other"]
        )


        # Filter based on selection and business hours
        filtered_calls = total_calls[
            (total_calls['department'].isin(selected_teams)) &
            (total_calls['call_category'].isin(selected_calls))
        ]


        timeframe_options = (
            total_calls[["Timeframe", "timeframe_period"]]
            .drop_duplicates()
            .sort_values("timeframe_period")
        )

        labels = timeframe_options["Timeframe"].tolist()
        periods = timeframe_options["timeframe_period"].tolist()

        if not labels:
            st.warning("No calls found for the selected teams, call types, or business hours.")
            filtered_df = pd.DataFrame()  # empty placeholder
        else:
            # ---- defaults ----
            default_start_period = pd.Period("2024-03", freq="M")
            default_start_idx = periods.index(default_start_period) if default_start_period in periods else 0
            default_end_idx = len(periods) - 1
            end_default_idx = max(default_end_idx, default_start_idx)

            # Start Month
            start_idx = st.selectbox(
                "Start Month:",
                options=range(len(labels)),
                index=default_start_idx,
                format_func=lambda i: labels[i],
            )

            # End Month
            end_idx = st.selectbox(
                "End Month:",
                options=range(start_idx, len(labels)),
                index=end_default_idx - start_idx,
                format_func=lambda i: labels[i],
            )

            # Filter DataFrame
            start_period = periods[start_idx]
            end_period = periods[end_idx]
            filtered_df = total_calls[
                (total_calls["month"] >= start_period) & (total_calls["month"] <= end_period)
            ]

        category_counts = (
            filtered_calls
                .groupby(["team_name", "Timeframe", "call_category"])
                .size()
                .unstack(fill_value=0)
                .reset_index()
        )

        # -------------------------------
        # 1. PER-CALL TIME (ROW LEVEL)
        # -------------------------------
        time_cols = ['PreQueue', 'InQueue', 'Agent_Time', 'Abandon_Time']

        filtered_calls['customer_call_time'] = filtered_calls[time_cols].sum(axis=1)


        # -------------------------------
        # 3. MAIN MONTHLY AGGREGATION
        # -------------------------------
        monthly_team_calls = (
            filtered_calls
                .groupby(["team_name", "Timeframe"])
                .agg(
                    # counts
                    call_volume=('master_contact_id', 'count'),

                    # time totals (REAL, no reconstruction later)
                    total_customer_call_time=('customer_call_time', 'sum'),
                    prequeue_time=('PreQueue', 'sum'),
                    inqueue_time=('InQueue', 'sum'),
                    agent_time=('Agent_Time', 'sum'),
                    acw_time=('ACW_Seconds', 'sum'),
                    agent_total_time=('Agent_Work_Time', 'sum'),
                    abandon_time=('Abandon_Time', 'sum'),

                    # uniques
                    unique_agents_count=('agent_name', 'nunique'),
                    unique_skills_count=('skill_name', 'nunique'),
                    unique_campaigns_count=('campaign_name', 'nunique'),

                    # lists
                    agent_list=('agent_name', lambda x: list(x.dropna().unique())),
                    skill_list=('skill_name', lambda x: list(x.dropna().unique())),
                    campaign_list=('campaign_name', lambda x: list(x.dropna().unique())),
                    Customer_Contacts=('contact_name', lambda x: list(x.value_counts().items()))
                )
                .reset_index()
        )


        # -------------------------------
        # 4. CALL TYPE COUNTS (NO DOUBLE COUNT)
        # -------------------------------
        call_type_counts = (
            filtered_calls
                .groupby(['team_name', 'Timeframe', 'call_category'])
                .size()
                .unstack(fill_value=0)
                .reset_index()
        )

        monthly_team_calls = monthly_team_calls.merge(
            call_type_counts,
            on=["team_name", "Timeframe"],
            how="left"
        )


        # -------------------------------
        # 5. DISPLAY TABLE
        # -------------------------------
        display_df = monthly_team_calls.copy()

        list_cols = ['agent_list', 'skill_list', 'campaign_list', 'Customer_Contacts']
        for col in list_cols:
            display_df[col] = display_df[col].apply(
                lambda x: ", ".join(map(str, x)) if isinstance(x, list) else ""
            )

        st.dataframe(display_df)

        call_cols = ['Inbound', 'Outbound', 'Voicemail', 'After Hours', 'No Agent', 'Other']

        # -------------------------------
        # 6. CALL TYPES BY TEAM (COUNTS)
        # -------------------------------
        existing_call_cols = [c for c in call_cols if c in monthly_team_calls.columns]

        agg_df = (
            monthly_team_calls
                .groupby('team_name', as_index=False)[existing_call_cols]
                .sum()
        )

        agg_df['Total Calls'] = agg_df[existing_call_cols].sum(axis=1)

        agg_df = agg_df.sort_values('Total Calls', ascending=False)

        st.text('Call Types by Team')

        # Define a consistent color mapping for call types
        call_colors = {
            "Inbound": "#0B3D91",
            "Outbound": "#89CFF0",
            "Voicemail": "#FFD700",
            "After Hours": "#AB63FA",
            "No Agent":  "#EF553B",
            "Other": "#808080",
        }


        # -------------------------------
        # 7. PLOTLY BAR CHART
        # -------------------------------
        agg_df_sorted = agg_df.sort_values("Total Calls", ascending=True)


        # Long format for stacking
        plot_df = agg_df.melt(
            id_vars="team_name",
            value_vars=existing_call_cols,
            var_name="Call Type",
            value_name="Calls"
        )

        # Calls by team
        fig = px.bar(
            plot_df,
            x="team_name",
            y="Calls",
            color="Call Type",
            title="Call Types by Team",
            text_auto=True,
            color_discrete_map=call_colors
        )
        fig.update_layout(
            barmode="stack",
            xaxis_title="Team",
            yaxis_title="Number of Calls",
            legend_title="Call Type",
            height=150
        )
        fig.update_xaxes(tickangle=-45)
        fig.update_xaxes(
            categoryorder="array",
            categoryarray=agg_df.sort_values("Total Calls", ascending=False)["team_name"]
        )


        fig.update_traces(
            texttemplate="%{text}" if plot_df["Calls"].min() > 10 else "",
            textposition="inside"
        )

        fig.update_traces(
            hovertemplate="%{x}<br>%{color}: %{y} calls"
        )
        st.plotly_chart(fig, use_container_width=True)

        # -------------------------------
        # 8. TIME BY CALL TYPE (Agent Time)
        # -------------------------------
        time_by_call_type = (
            filtered_calls
                .groupby(['team_name', 'call_category'], as_index=False)
                .agg(
                    total_calls=('master_contact_id', 'count'),
                    agent_total_time_mins=('Agent_Work_Time', 'sum')  # sum first
                )
        )

        # Convert to minutes AFTER aggregation
        time_by_call_type['agent_total_time_mins'] = time_by_call_type['agent_total_time_mins'] / 60

        time_pivot = time_by_call_type.pivot(
            index='team_name',
            columns='call_category',
            values='agent_total_time_mins'   # <- matches the aggregated column name
        ).fillna(0)

        #st.dataframe(time_pivot)
        
        if not time_pivot.empty:
            # Reset index for plotting
            plot_time_df = time_pivot.reset_index().melt(
                id_vars='team_name',
                var_name='Call Type',
                value_name='Agent Time (mins)'
            )

        # Agent time by call type
        fig_time = px.bar(
            plot_time_df,
            x='team_name',
            y='Agent Time (mins)',
            color='Call Type',
            title='Agent Work Time by Call Type and Team',
            text_auto=True,
            color_discrete_map=call_colors
        )
        fig_time.update_layout(
            barmode='stack',
            xaxis_title='Team',
            yaxis_title='Total Agent Time (mins)',
            legend_title='Call Type',
            height=150
        )
        fig_time.update_xaxes(tickangle=-45)
        fig_time.update_xaxes(
            categoryorder="array",
            categoryarray=agg_df.sort_values("Total Calls", ascending=False)["team_name"]
        )

        fig_time.update_traces(
            texttemplate="%{text}" if plot_time_df["Agent Time (mins)"].min() > 10 else "",
            textposition="inside"
        )

        fig_time.update_traces(
            hovertemplate="%{x}<br>%{color}: %{y} agent work time"
        )

        st.plotly_chart(fig_time, use_container_width=True)




        team_colors = {
            "Admin": "#F2C94C",
            "Business Support": "#9B6FF3",
            "Account Manager": "#1ECAD3",
            "DefaultTeam": "#6C7AF2",
            "Inside Sales": "#F25022",
            "Level 2 Support": "#00C389",
            "Test": "#F29D59",
            "Solutions": "#F76C8A",


            "Collections": "#F25022",
            "MCF Support":"#B08BF9",
            "Customer Support ATL": "#1EC6E8",
            "Field Services": "#00B294",
            "Commissioning": "#F7A1E6",
            "SDR Team": "#A6D785",
            "Billing": "#5B7BE5",
            "SB-AM": "#F9A55A",
        }
        # Add a color column to the DataFrame
        monthly_team_calls['color'] = monthly_team_calls['team_name'].map(team_colors)

        # Convert Timeframe to datetime
        monthly_team_calls['Timeframe_dt'] = pd.to_datetime(monthly_team_calls['Timeframe'], format='%b-%Y')

        # Sort by datetime to ensure correct order
        monthly_team_calls = monthly_team_calls.sort_values('Timeframe_dt')

        time_fig_calls = px.bar(
            monthly_team_calls,
            x='Timeframe_dt',             # use the datetime column for proper ordering
            y='call_volume',
            color='team_name',
            color_discrete_map=team_colors,
            title='Monthly Call Volume by Team',
            labels={'call_volume': 'Call Volume', 'Timeframe_dt': 'Month', 'team_name': 'Team'}
        )

        # Make it stacked
        time_fig_calls.update_layout(
            barmode='stack',
            xaxis_tickangle=-45,
            height=600,
            yaxis=dict(title='Call Volume', rangemode='tozero')
        )

        # Format x-axis to show Month-Year nicely
        time_fig_calls.update_xaxes(tickformat="%b-%Y")


        st.plotly_chart(time_fig_calls, use_container_width=True)


































#agg_df['Total Calls'] == monthly_team_calls.groupby('team_name')['call_volume'].sum()




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







# call_cols = ['Inbound', 'Outbound', 'Voicemail', 'No Agent', 'Other']
# time_cols = [
#             'agent_time', 
#              'acw_time', 
#              'abandon_time',
#              'total_calls_time'
#              ]

# # Sum total hours for each row
# monthly_team_calls['total_calls_time'] = monthly_team_calls[time_cols].sum(axis=1)

# # Aggregate total calls and total hours per team
# agg = monthly_team_calls.groupby('team_name', as_index=False).agg(
#     total_calls_time=('total_calls_time', 'sum'),
#     **{col: ('{}'.format(col), 'sum') for col in call_cols}
# )
# agg
