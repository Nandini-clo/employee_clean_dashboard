import dash
from dash import dcc, html, Input, Output, State, ctx, dash_table
import dash_bootstrap_components as dbc
import base64
import io
import pandas as pd
import plotly.express as px
from sklearn.preprocessing import MinMaxScaler

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SANDSTONE])
app.title = "Employee Analysis Dashboard"

def clean_columns(df):
    seen = {}
    new_cols = []
    for col in df.columns:
        col = col.strip()
        if col in seen:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_cols.append(col)
    df.columns = new_cols
    return df

def process_file(contents, header_row):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df = pd.read_excel(io.BytesIO(decoded), header=header_row)
        df = clean_columns(df)
        return df
    except:
        return None

def classify_risk(df):
    df['Absent Days'] = df['Total Days'] - df['Present Days']
    df['Absent Ratio'] = df['Absent Days'] / df['Total Days']
    df['Risk Status'] = df['Absent Ratio'].apply(lambda x: 'High Risk' if x >= 0.3 else 'Medium' if x >= 0.15 else 'Low Risk')
    return df

app.layout = dbc.Container([
    html.H2("📁 Upload Employee Excel Files", className="my-3"),
    dcc.Upload(
        id='upload-data',
        children=html.Div(["📂 Drag & Drop or Click to Select Excel Files"]),
        style={'border': '2px dashed #aaa', 'padding': '30px', 'textAlign': 'center'},
        multiple=True
    ),
    html.Label("Choose header row (0 = top row)"),
    dcc.Dropdown(id='header-row', options=[{"label": str(i), "value": i} for i in range(11)], value=0),
    html.Br(),
    dbc.Button("📊 Analyze Files", id="analyze-btn", color="primary"),
    html.Hr(),
    html.Div(id='output-area')
])

@app.callback(
    Output('output-area', 'children'),
    Input("analyze-btn", "n_clicks"),
    State("upload-data", "contents"),
    State("upload-data", "filename"),
    State("header-row", "value"),
    prevent_initial_call=True
)
def analyze_data(n_clicks, contents, filenames, header_row):
    if contents is None:
        return html.Div("⚠️ No files uploaded")

    # Load & Merge
    dfs = []
    for content in contents:
        df = process_file(content, header_row)
        if df is not None:
            dfs.append(df)
    if not dfs:
        return html.Div("❌ Could not load any files")
    df = pd.concat(dfs, ignore_index=True)
    
    # Normalize column names
    df.columns = df.columns.str.strip()
    name_col = next((col for col in df.columns if 'name' in col.lower()), None)
    if name_col is None or 'Total Days' not in df.columns or 'Present Days' not in df.columns:
        return html.Div("❌ Required columns missing: 'Employee Name', 'Total Days', 'Present Days'")
    
    df = df.rename(columns={name_col: 'EmployeeName'})
    df = df[df['EmployeeName'].notna()]

    # Calculate insights
    df['Absent Days'] = df['Total Days'] - df['Present Days']
    df['Attendance %'] = (df['Present Days'] / df['Total Days']) * 100
    df['Absent %'] = 100 - df['Attendance %']
    df = classify_risk(df)

    top_present = df.sort_values(by='Present Days', ascending=False).head(5)
    top_absent = df.sort_values(by='Absent Days', ascending=False).head(5)
    
    graphs = [
        dcc.Graph(figure=px.bar(df.groupby("Risk Status").size().reset_index(name="Count"),
                                x="Risk Status", y="Count", title="🛑 Risk Category Count")),

        dcc.Graph(figure=px.pie(df, names="Risk Status", title="🧠 Risk Distribution Pie Chart")),

        dcc.Graph(figure=px.bar(top_present, x='EmployeeName', y='Present Days',
                                title="✅ Top 5 Present Employees")),

        dcc.Graph(figure=px.bar(top_absent, x='EmployeeName', y='Absent Days',
                                title="❌ Top 5 Absent Employees")),

        dcc.Graph(figure=px.scatter(df, x="Present Days", y="Basic salary",
                                    color="Risk Status", title="📉 Present Days vs Salary")),

        dcc.Graph(figure=px.histogram(df, x="Attendance %", nbins=10,
                                      title="⏱ Attendance % Distribution")),

        dcc.Graph(figure=px.bar(df.sort_values(by="Basic salary", ascending=False).head(5),
                                x='EmployeeName', y='Basic salary', title="💰 Top 5 Salaries")),

        dcc.Graph(figure=px.bar(df.sort_values(by="Bonus", ascending=False).head(5),
                                x='EmployeeName', y='Bonus', title="🎁 Top 5 Bonuses")),

        dcc.Graph(figure=px.bar(df.sort_values(by="Penalty", ascending=False).head(5),
                                x='EmployeeName', y='Penalty', title="🚫 Top 5 Penalty Earners")),

        dcc.Graph(figure=px.line(df.sort_values(by="Attendance %", ascending=False).head(5),
                                 x='EmployeeName', y='Attendance %',
                                 title="📈 Attendance % of Top 5 Employees"))
    ]

    table = dash_table.DataTable(
        data=df[['EmployeeName', 'Total Days', 'Present Days', 'Absent Days', 'Attendance %', 'Basic salary', 'Risk Status']].to_dict('records'),
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'},
        style_header={'backgroundColor': 'lightblue', 'fontWeight': 'bold'}
    )

    return html.Div([
        html.H4(f"📋 Total Employees: {df['EmployeeName'].nunique()}"),
        html.H5("📌 Sample Insights Table"),
        table,
        html.Hr(),
        html.H4("📊 Insights & Visuals"),
        html.Div(graphs)
    ])

if __name__ == "__main__":
    app.run(debug=True)
