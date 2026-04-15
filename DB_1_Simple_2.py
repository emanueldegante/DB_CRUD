# -*- coding: utf-8 -*-
"""
Created on Sun Apr 12 21:22:54 2026

@author: emanu
"""

import sqlite3
import pandas as pd
from dash import Dash, html, dcc, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from datetime import datetime

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

# ---------------- FUNCTIONS ----------------
def fetch_data(query, params=()):
    df = pd.read_sql_query(query, conn, params=params)

    # Add delete button column
    if not df.empty:
        df["delete"] = df["id"].apply(lambda x: f"[🗑️ Delete](delete-{x})")
    else:
        df["delete"] = []

    return df.to_dict('records')

# ---------------- LAYOUT ----------------
app.layout = dbc.Container([
    html.H2("Patient Management System"),

    dbc.Row([
        dbc.Col([
            dcc.Input(id='unique_id', placeholder='Unique ID'),
            dcc.Input(id='name', placeholder='Name'),
            dcc.Input(id='last_name', placeholder='Last Name'),
            dcc.Input(id='age', placeholder='Age', type='number'),
            dcc.Input(id='cost', placeholder='Cost', type='number'),
            dcc.Input(id='treatment', placeholder='Treatment'),
            dcc.Input(id='time', type='datetime-local'),
            dcc.Textarea(id='notes', placeholder='Notes'),

            html.Br(),
            dbc.Button("Save Entry", id='save_btn', color='success'),
            dbc.Button("Load User", id='load_btn', color='info'),
            dbc.Button("Export CSV", id='export_btn', color='secondary'),
        ], width=4),

        dbc.Col([
            dcc.Input(id='search_id', placeholder='Search by Unique ID'),
            dbc.Button("Search", id='search_btn'),
            dbc.Button("Show All", id='show_all_btn'),

            dash_table.DataTable(
                id='table',
                columns=[
                    {"name": i, "id": i} for i in [
                        "id","unique_id","name","last_name","age","cost","treatment","time","notes"
                    ]
                ] + [{"name": "Delete", "id": "delete", "presentation": "markdown"}],
                page_size=10,
                editable=True,
            )
        ], width=8)
    ])
])

# ---------------- CALLBACKS ----------------

# Load all records
@app.callback(
    Output('table', 'data'),
    Input('show_all_btn', 'n_clicks')
)
def load_all(n):
    return fetch_data("SELECT * FROM records")

# Search
@app.callback(
    Output('table', 'data', allow_duplicate=True),
    Input('search_btn', 'n_clicks'),
    State('search_id', 'value'),
    prevent_initial_call=True
)
def search(n, uid):
    return fetch_data("SELECT * FROM records WHERE unique_id=?", (uid,))

# Load user into inputs
@app.callback(
    Output('name', 'value'),
    Output('last_name', 'value'),
    Output('age', 'value'),
    Input('load_btn', 'n_clicks'),
    State('unique_id', 'value'),
    prevent_initial_call=True
)
def load_user(n, uid):
    cursor.execute("SELECT name, last_name, age FROM records WHERE unique_id=? LIMIT 1", (uid,))
    row = cursor.fetchone()
    if row:
        return row[0], row[1], row[2]
    return "", "", ""

# Save entry
@app.callback(
    Output('table', 'data', allow_duplicate=True),
    Input('save_btn', 'n_clicks'),
    State('unique_id', 'value'),
    State('name', 'value'),
    State('last_name', 'value'),
    State('age', 'value'),
    State('cost', 'value'),
    State('treatment', 'value'),
    State('time', 'value'),
    State('notes', 'value'),
    prevent_initial_call=True
)
def save(n, uid, name, last_name, age, cost, treatment, time, notes):
    cursor.execute("""
    INSERT INTO records (unique_id, name, last_name, age, cost, treatment, time, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (uid, name, last_name, age, cost, treatment, time, notes))
    conn.commit()
    return fetch_data("SELECT * FROM records")

# Delete row (PROFESSIONAL UX)
@app.callback(
    Output('table', 'data', allow_duplicate=True),
    Input('table', 'active_cell'),
    State('table', 'data'),
    prevent_initial_call=True
)
def handle_delete(active_cell, table_data):
    if not active_cell:
        return table_data

    if active_cell["column_id"] == "delete":
        row = active_cell["row"]
        record_id = table_data[row]["id"]

        cursor.execute("DELETE FROM records WHERE id=?", (record_id,))
        conn.commit()

        return fetch_data("SELECT * FROM records")

    return table_data

# Export CSV
@app.callback(
    Input('export_btn', 'n_clicks')
)
def export(n):
    if n:
        df = pd.read_sql_query("SELECT * FROM records", conn)
        df.to_csv("records_export.csv", index=False)

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)