import streamlit as st
import plotly.graph_objects as go
import streamlit_authenticator as stauth
import yaml
import pandas as pd
import os 
import glob
from streamlit_plotly_events import plotly_events

# Define the YAML configuration for authentication
config = {
    'credentials': {
        'usernames': {
            'hc': {
                'name': 'User One',
                'password': 'hc_cloud'
            },
            'sanskar': {
                'name': 'User Two',
                'password': 'sanskar'
            }
        }
    },
    'cookie': {
        'expiry_days': 30,
        'key': 'some_signature_key',
        'name': 'some_cookie_name'
    },
    'preauthorized': {
        'emails': ['email@domain.com']
    }
}

# Save the configuration to a file
with open('config.yaml', 'w') as file:
    yaml.dump(config, file, default_flow_style=False)

# Load the configuration file
with open('config.yaml') as file:
    config = yaml.safe_load(file)

# Initialize the authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

# Display the login form
auth_status = authenticator.login('main', fields = {'Form name': 'Hotel Cloud'})

if auth_status[1]:
    st.write(f'Welcome')
   
    authenticator.logout('Logout', 'sidebar')
    data = pd.read_csv("visualisation_task_data - visualisation_task_data.csv", parse_dates=["stay_date", "report_date"])
    data["lead_in"] = data["stay_date"] - data["report_date"]
    data["lead_in"] = data["lead_in"].astype(str).apply(lambda x: x.split(" ")[0]).astype("int")
    data["error"] = data["individual_reservation_change_3_actual"]  - data["individual_reservation_change_3_predicted"]
    data["stay_day_of_week"] = data["stay_date"].dt.day_of_week

    fig = go.Figure()

    # Create a list of dropdown menu options and corresponding traces
    dropdown_buttons = []
    for lead_in in range(1, 31):
        lead_in_data = data[data["lead_in"] == lead_in]
        
        actual_means = lead_in_data.groupby("stay_day_of_week")["individual_reservation_change_3_actual"].mean()
        predicted_means = lead_in_data.groupby("stay_day_of_week")["individual_reservation_change_3_predicted"].mean()
        
        fig.add_trace(go.Bar(y=actual_means, name="Actual", visible=(lead_in == 1)))
        fig.add_trace(go.Bar(y=predicted_means, name="Predicted", visible=(lead_in == 1)))

        dropdown_buttons.append(
            dict(
                label=f'Lead_in {lead_in}',
                method='update',
                args=[{
                    'visible': [False] * (2 * 30),
                    'title': f'Lead_in {lead_in}',
                }]
            )
        )
        
        dropdown_buttons[-1]['args'][0]['visible'][2*(lead_in-1)] = True
        dropdown_buttons[-1]['args'][0]['visible'][2*(lead_in-1) + 1] = True

    # Update layout with dropdown menu and set the initial visible traces
    fig.update_layout(
        updatemenus=[
            dict(
                active=0,
                buttons=dropdown_buttons,
                direction="down",
                showactive=True
            )
        ],
        title='Actual and Predicted Pickup by Day of Week, Lead In Analysis',
        title_x=0.45,
    )
    fig.update_xaxes(title_text="Day of Week")
    st.plotly_chart(fig)

    def format_date_option(date):
        return date.strftime('%Y-%m-%d')

    
    stay_date_range_options = [format_date_option(date) for date in pd.date_range(start=data["stay_date"].min(), end=data["stay_date"].max())]
    report_date_range_options = [format_date_option(date) for date in pd.date_range(start=data["report_date"].min(), end=data["report_date"].max())]

    # Convert to datetime.date
    stay_date_range_start = pd.to_datetime(stay_date_range_options[0]).date()
    stay_date_range_end = pd.to_datetime(stay_date_range_options[-1]).date()
    report_date_range_start = pd.to_datetime(report_date_range_options[0]).date()
    report_date_range_end = pd.to_datetime(report_date_range_options[-1]).date()

    # Streamlit's slider for date ranges
    report_date_range_slider = st.slider(
        'Report Date Range',
        min_value=report_date_range_start,
        max_value=report_date_range_end,
        value=(report_date_range_start, report_date_range_end),
        format="YYYY-MM-DD"
    )

    stay_date_range_slider = st.slider(
        'Stay Date Range',
        min_value=stay_date_range_start,
        max_value=stay_date_range_end,
        value=(stay_date_range_start, stay_date_range_end),
        format="YYYY-MM-DD"
    )

    color_range_min = st.selectbox(
        'Color Range Min',
        options=[str(i) for i in range(0, 51)],
        index=0
    )

    color_range_max = st.selectbox(
        'Color Range Max',
        options=[str(i) for i in range(1, 51)],
        index=25
    )

    
    report_date_start, report_date_end = report_date_range_slider
    stay_date_start, stay_date_end = stay_date_range_slider
    report_date_start = pd.to_datetime(report_date_start)
    report_date_end = pd.to_datetime(report_date_end)
    stay_date_start = pd.to_datetime(stay_date_start)
    stay_date_end = pd.to_datetime(stay_date_end)

    color_range_min = int(color_range_min)
    color_range_max = int(color_range_max)

    
    filter_data = data[(data["report_date"] >= report_date_start) & (data["report_date"] <= report_date_end) & (data["stay_date"] >= stay_date_start) & (data["stay_date"] <= stay_date_end)]
    filter_data["stay_date"] = filter_data["stay_date"].astype(str)
    filter_data["report_date"] = filter_data["report_date"].astype(str)

    heatmap_df_preds = filter_data.pivot(index = "stay_date", columns = "report_date", values = "individual_reservation_change_3_predicted")
    heatmap_df_true = filter_data.pivot(index = "stay_date", columns = "report_date", values = "individual_reservation_change_3_actual")
    heatmap_df_error = filter_data.pivot(index = "stay_date", columns = "report_date", values = "error")

    heatmap_df_preds.sort_index(level=0, ascending=False, inplace=True)
    heatmap_df_true.sort_index(level=0, ascending=False, inplace=True)
    heatmap_df_error.sort_index(level=0, ascending=False, inplace=True)

    # zmin = min(heatmap_df_preds.min().min(), heatmap_df_true.min().min())
    # zmax = max(heatmap_df_preds.max().max(), heatmap_df_true.max().max())
    z_range = max(abs(heatmap_df_error.min().min()), abs(heatmap_df_error.max().max()))



    trace_preds = go.Heatmap(
        z=heatmap_df_preds,
        y=heatmap_df_preds.columns,
        x=heatmap_df_preds.index,
        colorscale='gray',
        zmin=color_range_min,
        zmax=color_range_max,
        visible=False 
    )

    trace_true = go.Heatmap(
        z=heatmap_df_true,
        y=heatmap_df_true.columns,
        x=heatmap_df_true.index,
        colorscale='gray',
        zmin=color_range_min,
        zmax=color_range_max,
    )

    trace_error = go.Heatmap(
        z=heatmap_df_error,
        y=heatmap_df_error.columns,
        x=heatmap_df_error.index,
        colorscale='rdbu',
        visible=False  ,
        zmin=-z_range,
        zmax=z_range
    )


    fig = go.Figure(data=[trace_true, trace_preds, trace_error])

    # Define buttons for layout
    buttons = [
        dict(label='Show Ground Truths',
            method='update',
            args=[{'visible': [True, False, False]}]),  # Enable only Ground Truths
        dict(label='Show Predictions',
            method='update',
            args=[{'visible': [False, True, False]}]),  # Enable only Predictions
        dict(label='Show Errors',
            method='update',
            args=[{'visible': [False, False, True]}])   # Enable only Errors
    ]

    # Add button layout to the figure
    fig.update_layout(
        title=f'Heatmap Analysis, Stay Date Range: {stay_date_start.strftime("%m/%d/%Y")} to {stay_date_end.strftime("%m/%d/%Y")}',
        title_x=0.5,
        updatemenus=[{
            'type': 'buttons',
            'direction': 'right',
            'x': 0.65,
            'y': 1.15,
            'showactive': True,
            'buttons': buttons
        }]
    )

    # Update axis labels
    fig.update_xaxes(title_text="Stay Date")
    fig.update_yaxes(title_text="Report Date")
    
    selected_points = plotly_events(fig, click_event=True, hover_event=False, select_event=True)
    
    stay_date = data["stay_date"].iloc[100]
    report_date = data["report_date"].iloc[100]

    if selected_points:
        stay_date = selected_points[0]['x']
        report_date = selected_points[0]['y']
        with st.columns(3)[1]:
            st.write(f"Stay Date: {stay_date}")
            st.write(f"Report Date: {report_date}")

    sample_stay_df = data[data["stay_date"] == stay_date][["individual_reservation_change_3_actual", "individual_reservation_change_3_predicted", "lead_in", "error"]]

    fig = go.Figure()


    fig.add_trace(go.Scatter(x=sample_stay_df["lead_in"], 
                            y=sample_stay_df["individual_reservation_change_3_predicted"],
                            mode='markers+lines',
                            marker=dict(color='red', symbol='circle'),
                            name='Predicted'))


    fig.add_trace(go.Scatter(x=sample_stay_df["lead_in"], 
                            y=sample_stay_df["individual_reservation_change_3_actual"],
                            mode='markers+lines',
                            marker=dict(color='blue', symbol='circle-open', line=dict(color='white')),
                            name='Actual'))


    fig.add_trace(go.Bar(x=sample_stay_df["lead_in"], 
                        y=abs(sample_stay_df["error"]),
                        marker=dict(color='red', opacity=0.2),
                        name='Error'))


    fig.update_layout(
        title=f"Actual and Predicted Pickup, Stay Date: {stay_date}",
        xaxis_title="Lead In",
        yaxis_title="3D Look Ahead Individual Reservations",
        legend_title="Legend",
        title_x = 0.45,
    )

    st.plotly_chart(fig)


    sample_report_df = data[data["report_date"] == report_date][["individual_reservation_change_3_actual", "individual_reservation_change_3_predicted", "lead_in", "error"]]
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=sample_report_df["lead_in"],
                            y=sample_report_df["individual_reservation_change_3_predicted"],
                            mode='markers+lines',
                            marker=dict(color='red', symbol='circle'),
                            name='Predicted'))
    
    fig.add_trace(go.Scatter(x=sample_report_df["lead_in"],
                            y=sample_report_df["individual_reservation_change_3_actual"],
                            mode='markers+lines',
                            marker=dict(color='blue', symbol='circle-open', line=dict(color='white')),
                            name='Actual'))
    
    fig.add_trace(go.Bar(x=sample_report_df["lead_in"],
                        y=abs(sample_report_df["error"]),
                        marker=dict(color='red', opacity=0.2),
                        name='Error'))
    
    fig.update_layout(
        title=f"Actual and Predicted Pickup, Report Date: {report_date}",
        xaxis_title="Lead In",
        yaxis_title="3D Look Ahead Individual Reservations",
        legend_title="Legend",
        title_x = 0.45,
    )

    st.plotly_chart(fig)

elif auth_status[1] == False:
    st.error('Username/password is incorrect')
elif auth_status[1] == None:
    st.warning('Please enter your username and password')
