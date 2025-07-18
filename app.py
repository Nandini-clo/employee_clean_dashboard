# app.py
import dash
from dash import html, dcc, dash_table, Input, Output, State
import pandas as pd
import plotly.express as px
import base64
import io
from prediction import predict_attrition, get_attrition_by_department, forecast_penalty

app = dash.Dash(__name__)
app.title = "📊 Employee Dataset Dashboard"

app.layout = html.Div([
    html.H2("📂 Upload Employee Excel File", style={'textAlign': 'center'}),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📥 Drag & Drop or ', html.A('Click to Select Files')]),
        style={
            'width': '95%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed',
            'borderRadius': '5px', 'textAlign': 'center',
            'margin': '20px auto'
        },
        multiple=False
    ),

    html.Div(id='uploaded-file-name', style={'textAlign': 'center', 'fontWeight': 'bold'}),
    html.Label("🎛️ Choose header row (0 = top row)", style={'marginLeft': '20px'}),
    dcc.Slider(id='header-row', min=0, max=10, step=1, value=0,
               marks={i: str(i) for i in range(11)}, tooltip={"placement": "bottom"}),

    html.Br(),
    html.Button("🔍 Analyze File", id='analyze-button', n_clicks=0),
    html.Div(id='output')
])

def decode_excel(content):
    content_type, content_string = content.split(',')
    decoded = base64.b64decode(content_string)
    return io.BytesIO(decoded)

@app.callback(
    Output('uploaded-file-name', 'children'),
    Input('upload-data', 'filename')
)
def show_filename(name):
    return f"✅ File Uploaded: {name}" if name else ""

@app.callback(
    Output('output', 'children'),
    Input('analyze-button', 'n_clicks'),
    State('upload-data', 'contents'),
    State('upload-data', 'filename'),
    State('header-row', 'value')
)
def process_uploaded_file(n_clicks, content, filename, header_row):
    if n_clicks > 0 and content:
        try:
            buffer = decode_excel(content)
            df = pd.read_excel(buffer, header=header_row)
            df['SourceFile'] = filename

            # Detect relevant columns
            name_col = next((c for c in df.columns if 'name' in c.lower()), None)
            dept_col = next((c for c in df.columns if 'depart' in c.lower() or 'plant' in c.lower()), None)
            salary_col = next((c for c in df.columns if 'net' in c.lower() and 'salary' in c.lower()), None)
            present_col = next((c for c in df.columns if 'present' in c.lower()), None)
            absent_col = next((c for c in df.columns if 'absent' in c.lower()), None)
            penalty_col = next((c for c in df.columns if 'penalt' in c.lower()), None)
            skill_col = next((c for c in df.columns if 'skill' in c.lower()), None)
            ot_col = next((c for c in df.columns if 'ot' in c.lower() or 'overtime' in c.lower()), None)
            total_days_col = next((c for c in df.columns if 'total' in c.lower() and 'day' in c.lower()), None)

            if absent_col is None and present_col and total_days_col:
                df['Absent'] = df[total_days_col] - df[present_col]
                absent_col = 'Absent'

            visuals = []

            # 🔟 Ten Visualizations
            if name_col and salary_col:
                fig1 = px.bar(df.sort_values(by=salary_col, ascending=False).head(5), x=name_col, y=salary_col, title="Top 5 Highest Salary Employees")
                visuals.append(dcc.Graph(figure=fig1))

            if name_col and present_col:
                fig2 = px.bar(df.sort_values(by=present_col, ascending=False).head(5), x=name_col, y=present_col, title="Top 5 Most Present Employees")
                visuals.append(dcc.Graph(figure=fig2))

            if name_col and absent_col:
                fig3 = px.bar(df.sort_values(by=absent_col, ascending=False).head(5), x=name_col, y=absent_col, title="Top 5 Most Absent Employees")
                visuals.append(dcc.Graph(figure=fig3))

            if dept_col and salary_col:
                fig4 = px.bar(df.groupby(dept_col)[salary_col].mean().reset_index(), x=dept_col, y=salary_col, title="Average Salary per Department")
                visuals.append(dcc.Graph(figure=fig4))

            if dept_col:
                dept_count = df[dept_col].value_counts().reset_index()
                dept_count.columns = [dept_col, 'Count']
                fig5 = px.pie(dept_count, names=dept_col, values='Count', title="Department-wise Employee Count")
                visuals.append(dcc.Graph(figure=fig5))

            if salary_col and present_col:
                fig6 = px.scatter(df, x=present_col, y=salary_col, title="Attendance vs Salary")
                visuals.append(dcc.Graph(figure=fig6))

            if skill_col:
                skill_count = df[skill_col].value_counts().reset_index()
                skill_count.columns = [skill_col, 'Count']
                fig7 = px.pie(skill_count, names=skill_col, values='Count', title="Skill Distribution")
                visuals.append(dcc.Graph(figure=fig7))

            if ot_col and salary_col:
                fig8 = px.scatter(df, x=ot_col, y=salary_col, title="Overtime vs Salary")
                visuals.append(dcc.Graph(figure=fig8))

            if dept_col and penalty_col:
                penalty_avg = df.groupby(dept_col)[penalty_col].mean().reset_index()
                fig9 = px.bar(penalty_avg, x=dept_col, y=penalty_col, title="Average Penalty per Department")
                visuals.append(dcc.Graph(figure=fig9))

            if absent_col and penalty_col and salary_col:
                df['RiskScore'] = (df[absent_col] + df[penalty_col]) / (df[salary_col] + 1)
                top_risk = df.sort_values(by='RiskScore', ascending=False).head(10)
                fig10 = px.bar(top_risk, x=name_col, y='RiskScore', title="Top 10 At-Risk Employees")
                visuals.append(dcc.Graph(figure=fig10))

            # 🧠 Predictions Below
            visuals.append(html.Hr())
            visuals.append(html.H3("🔮 Attrition Prediction"))
            risky_employees = predict_attrition(df)
            visuals.append(dash_table.DataTable(
                data=risky_employees.to_dict('records'),
                columns=[{"name": i, "id": i} for i in risky_employees.columns],
                page_size=10
            ))

            visuals.append(html.H3("🏢 Department-wise Risk"))
            dept_risk = get_attrition_by_department(df)
            visuals.append(dash_table.DataTable(
                data=dept_risk.to_dict('records'),
                columns=[{"name": i, "id": i} for i in dept_risk.columns],
                page_size=10
            ))

            visuals.append(html.H3("📉 Penalty Forecast"))
            penalty_df = forecast_penalty(df)
            visuals.append(dash_table.DataTable(
                data=penalty_df.to_dict('records'),
                columns=[{"name": i, "id": i} for i in penalty_df.columns],
                page_size=10
            ))

            return html.Div(visuals)

        except Exception as e:
            return html.Div([html.H4("❌ Error Reading File"), html.Pre(str(e))])
    return ""

if __name__ == "__main__":
    import webbrowser
    webbrowser.open("http://127.0.0.1:8050/")
    app.run(debug=True)
