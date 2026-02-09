import streamlit as st
import plotly.express as px

# Define expected call columns
call_cols = ['Inbound', 'Outbound', 'Voicemail', 'No Agent', 'Other']

# Keep only columns that actually exist in the DataFrame
existing_call_cols = [col for col in call_cols if col in monthly_team_calls.columns]

# Aggregate by team
agg_df = (
    monthly_team_calls
        .groupby('team_name', as_index=False)[existing_call_cols]
        .sum()
)

# Compute total calls across available columns
agg_df['Total Calls'] = agg_df[existing_call_cols].sum(axis=1)

# Sort by total calls (descending for table)
agg_df = agg_df.sort_values('Total Calls', ascending=False)
st.dataframe(agg_df)

# Sort ascending for horizontal bar chart
agg_df_sorted = agg_df.sort_values("Total Calls", ascending=True)

# Melt for Plotly using only available columns + Total Calls
agg_df_melt = agg_df_sorted.melt(
    id_vars="team_name",
    value_vars=existing_call_cols + ["Total Calls"],
    var_name="CallType",
    value_name="Count"
)

# Build Plotly chart
fig = px.bar(
    agg_df_melt,
    x="Count",
    y="team_name",
    color="CallType",
    barmode="group",
    orientation="h",
    title="Call Volume by Team"
)

# Auto-scale height
fig.update_layout(
    height=max(600, 40 * agg_df_sorted["team_name"].nunique()),
    yaxis_title="Team",
    xaxis_title="Call Count",
    legend_title="Call Type"
)

# Render in Streamlit
st.plotly_chart(fig, use_container_width=True)
