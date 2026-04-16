# -*- coding: utf-8 -*-
"""
Created on Sat Apr 11 22:23:25 2026

@author: emanu
"""

import sqlite3
import pandas as pd
from dash import Dash, html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px

# ---------------- DATABASE ----------------
conn = sqlite3.connect("records.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unique_id TEXT,
    name TEXT,
    last_name TEXT,
    age INTEGER,
    cost REAL,
    treatment TEXT,
    time TEXT,
    notes TEXT
)
""")
conn.commit()

# ---------------- APP ----------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# ---------------- LAYOUT ----------------
app.layout = dbc.Container([
    html.H2("Patient Management System"),

    # -------- FILTERS --------
    dbc.Row([
        dbc.Col([
            html.Label("Filter by Unique ID"),
            dcc.Input(id='filter_id', placeholder='Enter ID'),
        ], width=3),

        dbc.Col([
            html.Label("Date Range"),
            dcc.DatePickerRange(id='date_range')
        ], width=4),
    ]),

    html.Br(),

 # -------- KPI CARDS --------
    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardBody([
            html.H6("Total Cost"),
            html.H4(id='total_cost')
        ])])),

        dbc.Col(dbc.Card([dbc.CardBody([
            html.H6("Total Visits"),
            html.H4(id='total_visits')
        ])])),

        dbc.Col(dbc.Card([dbc.CardBody([
            html.H6("Avg Cost"),
            html.H4(id='avg_cost')
        ])])),
    ]),

    html.Br(),

    dbc.Row([
        dbc.Col([
            dcc.Input(id='unique_id', placeholder='Unique ID'),
            dcc.Input(id='name', placeholder='Name'),
            dcc.Input(id='last_name', placeholder='Last Name'),
            dcc.Input(id='age', placeholder='Age', type='number'),
            dcc.Input(id='cost', placeholder='Cost', type='number'),
            dcc.Input(id='treatment', placeholder='Treatment'),

            html.Label("Select Date"),
            dcc.DatePickerSingle(id='date'),

            html.Label("Time (HH:MM)"),
            dcc.Input(id='time', placeholder='14:30'),

            dcc.Textarea(id='notes', placeholder='Notes'),

            html.Br(),
            dbc.Button("Save", id='save_btn', color='success'),
        ], width=3),

        dbc.Col([
            dash_table.DataTable(
                id='table',
                columns=[{"name": i, "id": i} for i in [
                    "id","unique_id","name","last_name","age","cost","treatment","time","notes"
                ]],
                page_size=10,
                editable=True,
                row_deletable=True
            )
        ], width=5),

        dbc.Col([
            dcc.Graph(id='cost_chart'),
            dcc.Graph(id='treatment_chart')
        ], width=4)
    ])
])

# ---------------- FUNCTIONS ----------------

def fetch_df():
    df = pd.read_sql_query("SELECT * FROM records", conn)
    if not df.empty:
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
    return df

# ---------------- CALLBACKS ----------------
@app.callback(
    Output('table', 'data'),
    Output('cost_chart', 'figure'),
    Output('treatment_chart', 'figure'),
    Output('total_cost', 'children'),
    Output('total_visits', 'children'),
    Output('avg_cost', 'children'),
    Input('save_btn', 'n_clicks'),
    Input('filter_id', 'value'),
    Input('date_range', 'start_date'),
    Input('date_range', 'end_date')
)
def update_all(n, uid, start_date, end_date):
    df = fetch_df()

    if uid:
        df = df[df['unique_id'] == uid]

    if start_date and end_date:
        df = df[(df['time'] >= start_date) & (df['time'] <= end_date)]

    if df.empty:
        return [], {}, {}, "0", "0", "0"

    # Charts
    cost_fig = px.line(df, x='time', y='cost', title='Cost Over Time')
    treat_fig = px.histogram(df, x='treatment', title='Treatment Frequency')

    # KPIs
    total_cost = f"${df['cost'].sum():.2f}"
    total_visits = str(len(df))
    avg_cost = f"${df['cost'].mean():.2f}"

    return df.to_dict('records'), cost_fig, treat_fig, total_cost, total_visits, avg_cost

@app.callback(
    Input('save_btn', 'n_clicks'),
    State('unique_id', 'value'),
    State('name', 'value'),
    State('last_name', 'value'),
    State('age', 'value'),
    State('cost', 'value'),
    State('treatment', 'value'),
    State('date', 'date'),
    State('time', 'value'),
    State('notes', 'value')
)
def save(n, uid, name, last_name, age, cost, treatment, date, time, notes):
    if not n:
        return

    if date:
        datetime_value = f"{date} {time if time else '00:00'}"
    else:
        datetime_value = None

    cursor.execute("""
    INSERT INTO records (unique_id, name, last_name, age, cost, treatment, time, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (uid, name, last_name, age, cost, treatment, datetime_value, notes))
    conn.commit()

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)


#http://127.0.0.1:8050/