import base64
import io
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, ctx, dash_table
import dash_bootstrap_components as dbc

# Dash App Init
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "📊 Employee Attendance & Attrition Analyzer"

# Helper to decode uploaded files
def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'xls' in filename:
            df = pd.read_excel(io.BytesIO(decoded), header=None)
            # Detect proper header row
            for i in range(3):
                df_try = pd.read_excel(io.BytesIO(decoded), header=i)
                if any(name.lower() in str(col).lower() for col in df_try.columns for name in ['name', 'employee name', 'emp name']):
                    df = df_try.copy()
                    break
            df['SourceFile'] = filename
            return df
    except Exception as e:
        return pd.DataFrame([{"Error": f"Could not parse file {filename}: {e}"}])

# Layout
app.layout = dbc.Container([
    html.H2("Employee Dataset Analyzer (Single & Multi-Upload)"),
    html.Hr(),

    dbc.RadioItems(
        id='upload-mode',
        options=[
            {'label': 'Single File Upload', 'value': 'single'},
            {'label': 'Multiple File Upload (2-3 files)', 'value': 'multiple'}
        ],
        value='single',
        inline=True,
    ),
    html.Br(),

    html.Div(id='upload-section'),
    html.Div(id='output-analysis')
], fluid=True)

# Upload Input Section based on Mode
@app.callback(
    Output('upload-section', 'children'),
    Input('upload-mode', 'value')
)
def render_upload_section(mode):
    return html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Div(['📤 Drag & Drop or Click to Upload Excel File(s)']),
            style={
                'width': '100%', 'height': '100px', 'lineHeight': '100px',
                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                'textAlign': 'center', 'margin-bottom': '20px'
            },
            multiple=(mode == 'multiple')
        ),
        dbc.Button("Run Analysis", id='analyze-button', color='primary')
    ])

# Core Logic: Parse and Analyze
@app.callback(
    Output('output-analysis', 'children'),
    Input('analyze-button', 'n_clicks'),
    State('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def analyze_uploaded_files(n_clicks, list_of_contents, list_of_names):
    if not list_of_contents:
        return dbc.Alert("❌ No file uploaded!", color='danger')

    if isinstance(list_of_contents, str):  # Single file string
        list_of_contents = [list_of_contents]
        list_of_names = [list_of_names]

    dfs = []
    for content, name in zip(list_of_contents, list_of_names):
        df = parse_contents(content, name)
        if 'Error' in df.columns:
            return dbc.Alert(df['Error'].iloc[0], color='danger')
        dfs.append(df)

    combined_df = pd.concat(dfs, ignore_index=True)
    combined_df.fillna('', inplace=True)

    # Auto-detect name and attendance columns
    name_col = next((col for col in combined_df.columns if 'name' in str(col).lower()), None)
    present_col = next((col for col in combined_df.columns if 'present' in str(col).lower()), None)
    total_col = next((col for col in combined_df.columns if 'total' in str(col).lower() and 'day' in str(col).lower()), None)
    penalty_col = next((col for col in combined_df.columns if 'penalt' in str(col).lower()), None)

    if not all([name_col, present_col, total_col]):
        return dbc.Alert("❌ Required columns (Name, Present, Total Days) not found.", color='danger')

    combined_df['Present %'] = round(combined_df[present_col] / (combined_df[total_col] + 1) * 100, 2)
    if penalty_col:
        combined_df['Penalty/Salary Ratio'] = round(combined_df[penalty_col] / (combined_df[penalty_col].max() + 1), 2)

    table = dash_table.DataTable(
        data=combined_df[[name_col, present_col, total_col, 'Present %'] + ([penalty_col] if penalty_col else [])].to_dict('records'),
        columns=[{"name": i, "id": i} for i in [name_col, present_col, total_col, 'Present %'] + ([penalty_col] if penalty_col else [])],
        style_table={'overflowX': 'auto'},
        style_cell={
            'minWidth': '150px', 'whiteSpace': 'normal', 'textAlign': 'center'
        },
        page_size=15
    )

    return html.Div([
        html.H5(f"📋 Total Employees: {len(combined_df)}"),
        html.Hr(),
        table
    ])

if __name__ == '__main__':
    app.run_server(debug=True)
