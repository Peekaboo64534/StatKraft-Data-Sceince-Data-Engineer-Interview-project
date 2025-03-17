import pandas as pd
import numpy as np
import dash
from dash import dcc, html, callback, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta
from ttf_futures import DataStore, SecurityType

# Initialize the DataStore
pickle_file = "ttf_futures_data.pkl"

if os.path.exists(pickle_file):
    # Load from serialized file
    print(f"Loading from serialized file: {pickle_file}")
    datastore = DataStore(pickle_file=pickle_file)
else:
    # Initialize the DataStore from CSV
    print("Loading from CSV file and creating new serialized data")
    datastore = DataStore(csv_file="ttf_calendar.csv")
    # Save to disk for future use
    datastore.save_to_pickle(pickle_file)


def load_intraday_data():
    """func for loading intraday form the csv - contracts,csv."""
     
    df = pd.read_csv("contract_data.csv", delimiter=';')
    
    # Split the Time column into Date and Time
    df[['Date', 'Time']] = df['Time'].str.split(' ', expand=True)
    
    #  Date to datetime , correct format with dots (DD.MM.YYYY)
    df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y')
    
    df['Timestamp'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'])
    
    # Remove prefix from contracts
    df['symbol'] = df['symbol'].str.replace('ENDEX::F:', '', regex=False)
    
    return df

# Load the intraday data
intraday_data = load_intraday_data()

# Available dates from the data
available_dates = sorted(intraday_data['Date'].dt.date.unique())

#  Dash app
app = dash.Dash(__name__)
app.title = "TTF Futures Visualizer"

# Layout
app.layout = html.Div([
    html.H1("TTF Futures Visualization", style={'textAlign': 'center', 'marginTop': '20px', 'marginBottom': '20px'}),
    
    dcc.Tabs([
        dcc.Tab(label="Intraday Price Changes", children=[
            html.Div([
                html.H5("Contract Selection", style={'marginBottom': '15px', 'marginTop': '15px'}),
                html.Div([
                    html.Div([
                        html.Label("Security Type:"),
                        dcc.Dropdown(
                            id='security-type-dropdown',
                            options=[
                                {'label': 'Specific', 'value': 'specific'},
                                {'label': 'Generic', 'value': 'generic'},
                                {'label': 'Monthly Generic', 'value': 'monthly_generic'}
                            ],
                            value='specific',
                            clearable=False
                        )
                    ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '20px'}),
                    
                    html.Div([
                        html.Label("Security Code:"),
                        dcc.Input(
                            id='security-code-input',
                            type='text',
                            value='TFM\\J25',
                            placeholder="Enter security code",
                            style={'width': '100%'}
                        )
                    ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '20px'}),
                    
                    html.Div([
                        html.Label("Date Selection:"),
                        dcc.DatePickerSingle(
                            id='date-picker',
                            date=datetime.strptime(str(available_dates[-1]), '%Y-%m-%d').date(),
                            min_date_allowed=datetime.strptime(str(available_dates[0]), '%Y-%m-%d').date(),
                            max_date_allowed=datetime.strptime(str(available_dates[-1]), '%Y-%m-%d').date(),
                            display_format='MM/DD/YYYY'
                        )
                    ], style={'width': '30%', 'display': 'inline-block'})
                ]),
                
                html.Div([
                    html.Label("Days to Show:"),
                    dcc.Slider(
                        id='days-slider',
                        min=1,
                        max=10,
                        step=1,
                        value=5,
                        marks={i: str(i) for i in range(1, 11)},
                    )
                ], style={'marginTop': '20px', 'marginBottom': '20px'}),
                
                html.Div([
                    html.Label("Visualization Type:"),
                    dcc.RadioItems(
                        id='viz-type',
                        options=[
                            {'label': 'Price Change from Previous Close', 'value': 'price_change'},
                            {'label': 'OHLC Chart', 'value': 'ohlc'}
                        ],
                        value='price_change',
                        inline=True
                    )
                ], style={'marginTop': '10px', 'marginBottom': '20px'}),
                
                html.Div([
                    dcc.Loading(
                        id="loading-1",
                        type="default",
                        children=[
                            dcc.Graph(id='main-graph', style={'height': '70vh'})
                        ]
                    )
                ]),
                
                html.Div(id='contract-info', style={'marginTop': '20px'})
            ], style={'padding': '20px'})
        ]),

        # New Spread Analysis Tab
        dcc.Tab(label="Spread Analysis", children=[
            html.Div([
                html.H5("Spread Contract Selection", style={'marginBottom': '15px', 'marginTop': '15px'}),
                html.Div([
                    html.Div([
                        html.Label("Spread Type:"),
                        dcc.Dropdown(
                            id='spread-type-dropdown',
                            options=[
                                {'label': 'DEC-JUN Spread', 'value': 'TFMDECJUN1'},
                                {'label': 'DEC-DEC Spread', 'value': 'TFMDECDEC1'},
                                {'label': 'JAN-APR Spread', 'value': 'TFMJANAPR1'}
                            ],
                            value='TFMDECJUN1',
                            clearable=False
                        )
                    ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '20px'}),
                    
                    html.Div([
                        html.Label("Date Selection:"),
                        dcc.DatePickerSingle(
                            id='spread-date-picker',
                            date=datetime.strptime(str(available_dates[-1]), '%Y-%m-%d').date(),
                            min_date_allowed=datetime.strptime(str(available_dates[0]), '%Y-%m-%d').date(),
                            max_date_allowed=datetime.strptime(str(available_dates[-1]), '%Y-%m-%d').date(),
                            display_format='MM/DD/YYYY'
                        )
                    ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '20px'}),
                    
                    html.Div([
                        html.Label("Days to Show:"),
                        dcc.Slider(
                            id='spread-days-slider',
                            min=1,
                            max=10,
                            step=1,
                            value=5,
                            marks={i: str(i) for i in range(1, 11)},
                        )
                    ], style={'width': '30%', 'display': 'inline-block'})
                ]),
                
                html.Div([
                    html.Label("Visualization Type:"),
                    dcc.RadioItems(
                        id='spread-viz-type',
                        options=[
                            {'label': 'Spread Price', 'value': 'spread_price'},
                            {'label': 'Individual Legs', 'value': 'legs_comparison'}
                        ],
                        value='spread_price',
                        inline=True
                    )
                ], style={'marginTop': '20px', 'marginBottom': '20px'}),
                
                html.Div([
                    dcc.Loading(
                        id="loading-spread",
                        type="default",
                        children=[
                            dcc.Graph(id='spread-graph', style={'height': '70vh'})
                        ]
                    )
                ]),
                
                html.Div(id='spread-info', style={'marginTop': '20px'})
            ], style={'padding': '20px'})
        ]),
    ])
], style={'maxWidth': '1200px', 'margin': '0 auto', 'padding': '20px'})

@callback(
    [Output('main-graph', 'figure'),
     Output('contract-info', 'children')],
    [Input('security-type-dropdown', 'value'),
     Input('security-code-input', 'value'),
     Input('date-picker', 'date'),
     Input('days-slider', 'value'),
     Input('viz-type', 'value')]
)
def update_main_graph(security_type, security_code, selected_date, days_to_show, viz_type):
    if not security_code:
        return {}, "Please enter a security code."
    
    try:
        # Convert the date string to datetime
        point_in_time = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        
        #  DataStore to get the specific contract for the selected security
        result = datastore.query(security_code, security_type, point_in_time)
        
        if result.empty:
            return {}, f"No data found for {security_code} with type {security_type} on {point_in_time}."
        
        #  specific contract code
        specific_contract = result['TFM_Code'].iloc[0]
        
        # Calculate the date range to display
        end_date = datetime.strptime(selected_date, '%Y-%m-%d')
        start_date = end_date - timedelta(days=days_to_show)
        
        # Filter intraday data for  specific contract, date range
        contract_data = intraday_data[
            (intraday_data['symbol'] == specific_contract) & 
            (intraday_data['Date'] >= start_date.strftime('%Y-%m-%d')) &
            (intraday_data['Date'] <= end_date.strftime('%Y-%m-%d'))
        ].copy()
        
        if contract_data.empty:
            return {}, f"No intraday data found for {specific_contract} in the selected date range."
        
        #  if string convert to datetime
        if isinstance(contract_data['Date'].iloc[0], str):
            contract_data['Date'] = pd.to_datetime(contract_data['Date'])
        
        # Extract hour from Time column and filter for 7:00 to 17:00
        contract_data['hour'] = contract_data['Time'].str.split(':').str[0].astype(int)
        contract_data = contract_data[(contract_data['hour'] >= 7) & (contract_data['hour'] <= 17)]
        
        # Group by date to get the previous day's close for each day
        contract_data['date_only'] = contract_data['Date'].dt.date
        daily_closes = contract_data.groupby('date_only')['CLOSE'].last().reset_index()
        daily_closes['prev_close'] = daily_closes['CLOSE'].shift(1)
        
        # Merge back to get previous day's close for each bar
        contract_data = pd.merge(
            contract_data,
            daily_closes[['date_only', 'prev_close']],
            on='date_only',
            how='left'
        )
        
        # For the first day in our data, we might not have a previous close
        # In this case, use the first open price as the reference
        if contract_data['prev_close'].isnull().any():
            first_date = contract_data[contract_data['prev_close'].isnull()]['date_only'].min()
            first_open = contract_data[contract_data['date_only'] == first_date]['OPEN'].iloc[0]
            contract_data.loc[contract_data['date_only'] == first_date, 'prev_close'] = first_open
        
        # Calculate price change from previous close
        contract_data['price_change'] = contract_data['CLOSE'] - contract_data['prev_close']
        
        # Create visualizations based on the selected type
        if viz_type == 'price_change':
            # Create a figure for price change from previous close
            fig = go.Figure()
            
            # Get a list of unique dates for plotting
            unique_dates = sorted(contract_data['date_only'].unique())
            
            #  distinct colors
            import plotly.express as px
            colors = px.colors.qualitative.Plotly + px.colors.qualitative.Dark24
            
            # Define a list of marker symbols for variety
            marker_symbols = ['circle', 'square', 'diamond', 'cross', 'x', 'triangle-up', 
                             'triangle-down', 'star', 'pentagon', 'hexagon']
            
            # Add a trace for each day
            for i, date in enumerate(unique_dates):
                date_str = date.strftime('%Y-%m-%d')
                day_data = contract_data[contract_data['date_only'] == date].sort_values('Time')
                
                # Choose color and marker symbol (cycling if more days than options)
                color = colors[i % len(colors)]
                symbol = marker_symbols[i % len(marker_symbols)]
                
                fig.add_trace(go.Scatter(
                    x=day_data['Time'],  # Use Time directly for x-axis
                    y=day_data['price_change'],
                    mode='lines+markers',
                    name=date_str,
                    line=dict(color=color, width=2),
                    marker=dict(
                        symbol=symbol,
                        size=8,
                        color=color,
                        line=dict(width=1, color='white')
                    )
                ))
            
            # Update layout with enhancements for better visibility
            fig.update_layout(
                title=f"Intraday Price Change for {specific_contract} (from previous close)",
                xaxis_title="Time",
                yaxis_title="Price Change",
                legend_title="Date",
                hovermode="x unified",
                template="plotly_white",
                # Improve legend visibility
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.99,
                    xanchor="right",
                    x=0.99,
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="lightgrey",
                    borderwidth=1
                )
            )
            
            # Create a fixed time range from 7:00 to 17:00
            fig.update_xaxes(
                tickformat="%H:%M",
                tickmode="array",
                tickvals=["07:00", "08:00", "09:00", "10:00", "11:00", "12:00", 
                          "13:00", "14:00", "15:00", "16:00", "17:00"],
                range=["07:00", "17:00"]
            )
            
            # Add a horizontal line at zero
            fig.add_shape(
                type="line",
                x0="07:00",
                y0=0,
                x1="17:00",
                y1=0,
                line=dict(color="black", width=1, dash="dash"),
            )
            
        elif viz_type == 'ohlc':
            # Create an OHLC chart with volume
            fig = make_subplots(
                rows=2, 
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                subplot_titles=(f"OHLC for {specific_contract}", "Volume"),
                row_heights=[0.7, 0.3]
            )
            
            # Get a list of unique dates for plotting
            unique_dates = sorted(contract_data['date_only'].unique())
            
            # Get a color palette with enough distinct colors
            import plotly.express as px
            colors = px.colors.qualitative.Plotly + px.colors.qualitative.Dark24
            
            # Process data for each day - use unique colors for each day
            for i, date in enumerate(unique_dates):
                date_str = date.strftime('%Y-%m-%d')
                day_data = contract_data[contract_data['date_only'] == date].sort_values('Time')
                
                # Choose color (cycling if more days than colors)
                color = colors[i % len(colors)]
                
                # Add OHLC candles with consistent color per day
                fig.add_trace(
                    go.Candlestick(
                        x=day_data['Time'],
                        open=day_data['OPEN'],
                        high=day_data['HIGH'],
                        low=day_data['LOW'],
                        close=day_data['CLOSE'],
                        name=date_str,
                        increasing=dict(line=dict(color=color)),
                        decreasing=dict(line=dict(color=color)),
                        line=dict(width=2)
                    ),
                    row=1, col=1
                )
                
                # Add volume bars with matching colors
                fig.add_trace(
                    go.Bar(
                        x=day_data['Time'],
                        y=day_data['VOLUME'],
                        name=f"Volume {date_str}",
                        marker_color=color,
                        showlegend=False,
                        opacity=0.7
                    ),
                    row=2, col=1
                )
            
            # Update layout
            fig.update_layout(
                title=f"OHLC and Volume for {specific_contract}",
                xaxis_title="",
                legend_title="Date",
                hovermode="x unified",
                template="plotly_white",
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.99,
                    xanchor="right",
                    x=0.99,
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="lightgrey",
                    borderwidth=1
                )
            )
            
            # Create a fixed time range from 7:00 to 17:00
            fig.update_xaxes(
                tickformat="%H:%M",
                tickmode="array",
                tickvals=["07:00", "08:00", "09:00", "10:00", "11:00", "12:00", 
                          "13:00", "14:00", "15:00", "16:00", "17:00"],
                range=["07:00", "17:00"]
            )
            
            # Hide rangeslider
            fig.update_layout(xaxis_rangeslider_visible=False)
        
        # Create contract info display
        contract_info = html.Div([
            html.H5(f"Contract Information:"),
            html.P([
                html.Strong("Selected Contract: "), f"{security_code} ({security_type})", html.Br(),
                html.Strong("Mapped to Specific: "), f"{specific_contract}", html.Br(),
                html.Strong("Delivery Month: "), f"{result['delivery_month'].iloc[0]}", html.Br(),
                html.Strong("Expiry Date: "), f"{result['expiry_date'].iloc[0]}"
            ])
        ])
        
        return fig, contract_info
        
    except Exception as e:
        import traceback
        return {}, f"Error: {str(e)}\n{traceback.format_exc()}"

# Add callback for the spread tab
@callback(
    [Output('spread-graph', 'figure'),
     Output('spread-info', 'children')],
    [Input('spread-type-dropdown', 'value'),
     Input('spread-date-picker', 'date'),
     Input('spread-days-slider', 'value'),
     Input('spread-viz-type', 'value')]
)
def update_spread_graph(spread_code, selected_date, days_to_show, viz_type):
    """
    Update the spread graph based on the selected spread, date, and visualization type.
    """
    if not spread_code:
        return {}, "Please select a spread type."
    
    try:
        # Convert the date string to datetime
        point_in_time = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        
        # Query for the spread contract details
        spread_result = datastore.query(spread_code, "spread", point_in_time)
        
        if spread_result.empty:
            return {}, f"No data found for spread {spread_code} on {point_in_time}."
        
        # Get the contract codes for both legs
        contract1_code = spread_result['contract1_code'].iloc[0]
        contract2_code = spread_result['contract2_code'].iloc[0]
        spread_type = spread_result['spread_type'].iloc[0]
        
        # Calculate the date range to display
        end_date = datetime.strptime(selected_date, '%Y-%m-%d')
        start_date = end_date - timedelta(days=days_to_show)
        
        # Filter intraday data for the date range
        date_filtered_data = intraday_data[
            (intraday_data['Date'] >= start_date.strftime('%Y-%m-%d')) &
            (intraday_data['Date'] <= end_date.strftime('%Y-%m-%d'))
        ].copy()
        
        # Filter for each leg
        leg1_data = date_filtered_data[date_filtered_data['symbol'] == contract1_code].copy()
        leg2_data = date_filtered_data[date_filtered_data['symbol'] == contract2_code].copy()
        
        if leg1_data.empty:
            return {}, f"No intraday data found for the first leg of the spread ({contract1_code}) in the selected date range."
        
        if leg2_data.empty:
            return {}, f"No intraday data found for the second leg of the spread ({contract2_code}) in the selected date range."
        
        # Merge the data on Timestamp
        # Make sure they have the same timestamps
        merged_data = pd.merge(
            leg1_data[['Timestamp', 'Date', 'Time', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']],
            leg2_data[['Timestamp', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']],
            on='Timestamp',
            suffixes=('_1', '_2')
        )
        
        if merged_data.empty:
            return {}, f"No matching timestamps found for both legs of the spread in the selected date range."
        
        # Calculate spread prices
        merged_data['OPEN_SPREAD'] = merged_data['OPEN_1'] - merged_data['OPEN_2']
        merged_data['HIGH_SPREAD'] = merged_data['HIGH_1'] - merged_data['HIGH_2']
        merged_data['LOW_SPREAD'] = merged_data['LOW_1'] - merged_data['LOW_2']
        merged_data['CLOSE_SPREAD'] = merged_data['CLOSE_1'] - merged_data['CLOSE_2']
        
        # Extract hour from Time column and filter for 7:00 to 17:00
        merged_data['hour'] = merged_data['Time'].str.split(':').str[0].astype(int)
        merged_data = merged_data[(merged_data['hour'] >= 7) & (merged_data['hour'] <= 17)]
        
        # Add date_only for grouping
        merged_data['date_only'] = merged_data['Date'].dt.date
        
        # Get unique dates
        unique_dates = sorted(merged_data['date_only'].unique())
        
        # Use a color palette
        import plotly.express as px
        colors = px.colors.qualitative.Plotly + px.colors.qualitative.Dark24
        
        # Create the visualization based on the selected type
        if viz_type == 'spread_price':
            # Create a figure for spread price
            fig = go.Figure()
            
            # Add a trace for each day
            for i, date in enumerate(unique_dates):
                date_str = date.strftime('%Y-%m-%d')
                day_data = merged_data[merged_data['date_only'] == date].sort_values('Time')
                
                # Choose color
                color = colors[i % len(colors)]
                
                fig.add_trace(go.Scatter(
                    x=day_data['Time'],
                    y=day_data['CLOSE_SPREAD'],
                    mode='lines+markers',
                    name=date_str,
                    line=dict(color=color, width=2),
                    marker=dict(size=8)
                ))
            
            # Update layout
            fig.update_layout(
                title=f"Spread Price for {spread_type} ({contract1_code} - {contract2_code})",
                xaxis_title="Time",
                yaxis_title="Spread Price",
                legend_title="Date",
                hovermode="x unified",
                template="plotly_white",
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.99,
                    xanchor="right",
                    x=0.99,
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="lightgrey",
                    borderwidth=1
                )
            )
            
            # Create a fixed time range from 7:00 to 17:00
            fig.update_xaxes(
                tickformat="%H:%M",
                tickmode="array",
                tickvals=["07:00", "08:00", "09:00", "10:00", "11:00", "12:00", 
                          "13:00", "14:00", "15:00", "16:00", "17:00"],
                range=["07:00", "17:00"]
            )
            
            # Add a horizontal line at zero
            fig.add_shape(
                type="line",
                x0="07:00",
                y0=0,
                x1="17:00",
                y1=0,
                line=dict(color="black", width=1, dash="dash"),
            )
            
        elif viz_type == 'legs_comparison':
            # Create a figure with subplots for each leg
            fig = make_subplots(
                rows=3, 
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=(
                    f"Leg 1: {contract1_code}", 
                    f"Leg 2: {contract2_code}",
                    f"Spread: {contract1_code} - {contract2_code}"
                ),
                row_heights=[0.33, 0.33, 0.33]
            )
            
            # Add a trace for each day and each leg
            for i, date in enumerate(unique_dates):
                date_str = date.strftime('%Y-%m-%d')
                day_data = merged_data[merged_data['date_only'] == date].sort_values('Time')
                
                # Choose color
                color = colors[i % len(colors)]
                
                # Add trace for leg 1
                fig.add_trace(
                    go.Scatter(
                        x=day_data['Time'],
                        y=day_data['CLOSE_1'],
                        mode='lines',
                        name=f"{date_str} (Leg 1)",
                        line=dict(color=color),
                        showlegend=True
                    ),
                    row=1, col=1
                )
                
                # Add trace for leg 2
                fig.add_trace(
                    go.Scatter(
                        x=day_data['Time'],
                        y=day_data['CLOSE_2'],
                        mode='lines',
                        name=f"{date_str} (Leg 2)",
                        line=dict(color=color, dash='dash'),
                        showlegend=True
                    ),
                    row=2, col=1
                )
                
                # Add trace for spread
                fig.add_trace(
                    go.Scatter(
                        x=day_data['Time'],
                        y=day_data['CLOSE_SPREAD'],
                        mode='lines',
                        name=f"{date_str} (Spread)",
                        line=dict(color=color, dash='dot'),
                        showlegend=True
                    ),
                    row=3, col=1
                )
            
            # Update layout
            fig.update_layout(
                title=f"Spread Components: {spread_type} ({contract1_code} - {contract2_code})",
                legend_title="Date and Component",
                hovermode="x unified",
                template="plotly_white",
                height=900,  # Taller figure for three subplots
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.99,
                    xanchor="right",
                    x=0.99,
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="lightgrey",
                    borderwidth=1
                )
            )
            
            # Create a fixed time range from 7:00 to 17:00 for all three subplots
            for i in range(1, 4):
                fig.update_xaxes(
                    tickformat="%H:%M",
                    tickmode="array",
                    tickvals=["07:00", "08:00", "09:00", "10:00", "11:00", "12:00", 
                              "13:00", "14:00", "15:00", "16:00", "17:00"],
                    range=["07:00", "17:00"],
                    row=i, col=1
                )
        
        # Create spread info display
        spread_info = html.Div([
            html.H5(f"Spread Information:"),
            html.P([
                html.Strong("Selected Spread: "), f"{spread_code} ({spread_type})", html.Br(),
                html.Strong("Leg 1: "), f"{contract1_code} (Expiry: {spread_result['contract1_expiry'].iloc[0]})", html.Br(),
                html.Strong("Leg 2: "), f"{contract2_code} (Expiry: {spread_result['contract2_expiry'].iloc[0]})", html.Br(),
                html.Strong("Current Spread Value: "), f"{merged_data['CLOSE_SPREAD'].iloc[-1]:.2f} (as of {merged_data['Time'].iloc[-1]} on {merged_data['Date'].iloc[-1].strftime('%Y-%m-%d')})"
            ])
        ])
        
        return fig, spread_info
        
    except Exception as e:
        import traceback
        return {}, f"Error: {str(e)}\n{traceback.format_exc()}"

if __name__ == '__main__':
    app.run_server(debug=True)