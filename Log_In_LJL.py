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
import traceback

# ---------------- DATABASE ----------------
conn = sqlite3.connect("records.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    logindate TEXT,
    logintime TEXT,
    logoutdate TEXT,
    logouttime TEXT,
    notes TEXT
)
""")
conn.commit()

# ---------------- APP ----------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# ---------------- FUNCTIONS ----------------
def fetch_data(query, params=()):
    df = pd.read_sql_query(query, conn, params=params)

    if not df.empty:
        # ✅ Duration
        df["duration"] = df.apply(
            lambda row: calculate_duration(
                row["logindate"],
                row["logintime"],
                row["logoutdate"],
                row["logouttime"]
            ),
            axis=1
        )

        # ✅ Fraction (decimal hours)
        df["fraction"] = df.apply(
            lambda row: calculate_fraction(
                row["logindate"],
                row["logintime"],
                row["logoutdate"],
                row["logouttime"]
            ),
            axis=1
        )

        # ✅ Reorder columns → duration + fraction before notes
        cols = df.columns.tolist()

        cols.insert(cols.index("notes"), cols.pop(cols.index("fraction")))
        cols.insert(cols.index("fraction"), cols.pop(cols.index("duration")))

        df = df[cols]

        # ✅ Delete button
        df["delete"] = df["id"].apply(lambda x: f"[🗑️ Delete](delete-{x})")

    else:
        df["duration"] = []
        df["fraction"] = []
        df["delete"] = []

    return df.to_dict('records')

def calculate_duration(logindate, logintime, logoutdate, logouttime):
    try:
        # Combine date + time into full datetime
        login_dt = datetime.strptime(f"{logindate} {logintime}", "%Y-%m-%d %H:%M")
        logout_dt = datetime.strptime(f"{logoutdate} {logouttime}", "%Y-%m-%d %H:%M")

        # Compute difference
        duration = logout_dt - login_dt

        # Convert to hours and minutes
        total_minutes = int(duration.total_seconds() / 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60

        return f"{hours}h {minutes}m"
    
    except Exception as e:
        print("Error calculating duration:", e)
        return None

def calculate_fraction(logindate, logintime, logoutdate, logouttime):
    try:
        if not all([logindate, logintime, logoutdate, logouttime]):
            return None

        login_dt = datetime.strptime(f"{logindate} {logintime}", "%Y-%m-%d %H:%M")
        logout_dt = datetime.strptime(f"{logoutdate} {logouttime}", "%Y-%m-%d %H:%M")

        duration = logout_dt - login_dt
        total_hours = duration.total_seconds() / 3600  # ✅ convert to hours (float)

        return round(total_hours, 2)  # e.g. 2.5

    except Exception as e:
        print("Error calculating fraction:", e)
        return None
# ---------------- LAYOUT ----------------
app.layout = dbc.Container([
    html.H2("ClockIn ClockOut Job Record"),

    dbc.Row([
        dbc.Col([
            dcc.Input(id='name', placeholder='Name'),

            html.Label("Log-In Date"),
            dcc.DatePickerSingle(id='logindate'),

            html.Label("Log-In Time"),
            dcc.Input(id='logintime', placeholder='HH:MM'),
            
            html.Label("Log-Out Date"),
            dcc.DatePickerSingle(id='logoutdate'),

            html.Label("Log-Out Time"),
            dcc.Input(id='logouttime', placeholder='HH:MM'),
            
            dcc.Textarea(id='notes', placeholder='Notes'),


            html.Br(),
            dbc.Button("Save Entry", id='save_btn', color='success'),
            dbc.Button("Load User", id='load_btn', color='info'),
            dbc.Button("Export CSV", id='export_btn', color='secondary'),
        ], width=4),

        dbc.Col([
            dcc.DatePickerSingle(id='logindate_picker', placeholder='Log In Date'),
            dbc.Button("Search", id='search_btn'),
            dbc.Button("Show All", id='show_all_btn'),

            dash_table.DataTable(
                id='table',
                columns=[
                    {"name": i, "id": i} for i in [
                        "id",
                        "name",
                        "logindate",
                        "logintime",
                        "logoutdate",
                        "logouttime",
                        "duration",
                        "fraction",# ✅ NEW
                        "notes"
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
    State('logindate_picker', 'date'),
    prevent_initial_call=True
)
def search(n, lid):
    return fetch_data("SELECT * FROM records WHERE logindate=?", (lid,))

# Load user into inputs
@app.callback(
    Output('name', 'value'),
    Output('logindate', 'date'),
    Output('logintime', 'value'),
    Output('logoutdate', 'date'),
    Output('logouttime', 'value'),
    Input('load_btn', 'n_clicks'),
    State('logindate_picker', 'date'),
    prevent_initial_call=True
)
def load_user(n, lid):
    cursor.execute("SELECT name, logindate FROM records WHERE logindate_picker=? LIMIT 1", (lid,))
    row = cursor.fetchone()
    if row:
        return row[0], row[1], row[2]
    return "", "", ""
# Save entry
@app.callback(
    Output('table', 'data', allow_duplicate=True),
    Input('save_btn', 'n_clicks'),
    State('name', 'value'),
    State('logindate', 'date'),
    State('logintime', 'value'),
    State('logoutdate', 'date'),
    State('logouttime', 'value'),
    State('notes', 'value'),
    prevent_initial_call=True
)
def save(n, name, logindate, logintime, logoutdate, logouttime, notes):
    try:
        # ✅ Basic validation (prevents bad inserts)
        if not name or not logindate or not logintime:
            print("Missing required fields")
            return fetch_data("SELECT * FROM records")

        cursor.execute("""
            INSERT INTO records (name, logindate, logintime, logoutdate, logouttime, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, logindate, logintime, logoutdate, logouttime, notes))

        conn.commit()

    except Exception as e:
        print("ERROR saving record:", e)

    # ✅ Refresh table (duration will be recalculated automatically)
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

        if not df.empty:
            df["duration"] = df.apply(
                lambda row: calculate_duration(
                    row["logindate"],
                    row["logintime"],
                    row["logoutdate"],
                    row["logouttime"]
                ),
                axis=1
            )

            df["fraction"] = df.apply(
                lambda row: calculate_fraction(
                    row["logindate"],
                    row["logintime"],
                    row["logoutdate"],
                    row["logouttime"]
                ),
                axis=1
            )

            # ✅ SAFE COLUMN ORDER (INSIDE FUNCTION ONLY)
            cols = [
                "id",
                "name",
                "logindate",
                "logintime",
                "logoutdate",
                "logouttime",
                "duration",
                "fraction",
                "notes"
            ]

            df = df[cols]

        df.to_csv("records_export.csv", index=False)

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)
    
    
# http://127.0.0.1:8050/