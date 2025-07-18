# predict_enhanced.py
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

# 🔮 Predict top 10 at-risk employees using penalty, attendance, and salary

def predict_attrition(df):
    df = df.copy()

    required_cols = ['EmployeeName', 'Penalty', 'Present', 'Absent', 'Net Salary']
    detected_cols = {}
    for col in df.columns:
        lower = col.lower()
        if 'penalt' in lower:
            detected_cols['Penalty'] = col
        elif 'present' in lower:
            detected_cols['Present'] = col
        elif 'absent' in lower:
            detected_cols['Absent'] = col
        elif 'salary' in lower and 'net' in lower:
            detected_cols['Net Salary'] = col
        elif 'name' in lower:
            detected_cols['EmployeeName'] = col

    if len(detected_cols) < 5:
        return pd.DataFrame([{"Error": "Missing required columns for prediction"}])

    df = df.rename(columns=detected_cols)
    df = df.dropna(subset=['Penalty', 'Present', 'Absent', 'Net Salary'])

    if df.shape[0] == 0:
        return pd.DataFrame([{"Error": "No valid rows for prediction"}])

    X = df[['Penalty', 'Present', 'Absent', 'Net Salary']]
    y = ((df['Penalty'] > 1000) | (df['Absent'] > 4)).astype(int)  # Simplified assumption

    model = RandomForestClassifier()
    model.fit(X, y)

    df['AttritionRisk'] = model.predict_proba(X)[:, 1]  # probability of attrition
    top_risk = df.sort_values(by='AttritionRisk', ascending=False).head(10)

    return top_risk[['EmployeeName', 'Penalty', 'Present', 'Absent', 'Net Salary', 'AttritionRisk']]

# 🏭 Predict department-level attrition risk

def get_attrition_by_department(df):
    dept_col = next((c for c in df.columns if 'depart' in c.lower() or 'plant' in c.lower()), None)
    absent_col = next((c for c in df.columns if 'absent' in c.lower()), None)
    penalty_col = next((c for c in df.columns if 'penalt' in c.lower()), None)

    if not dept_col or not absent_col or not penalty_col:
        return pd.DataFrame([{"Error": "Missing department/absent/penalty column"}])

    dept_summary = df.groupby(dept_col).agg({absent_col: 'mean', penalty_col: 'mean'}).reset_index()
    dept_summary.rename(columns={absent_col: 'Avg Absent', penalty_col: 'Avg Penalty'}, inplace=True)
    return dept_summary

# 📈 Forecast penalties (dummy trend simulation)
def forecast_penalty(df):
    name_col = next((c for c in df.columns if 'name' in c.lower()), 'EmployeeName')
    penalty_col = next((c for c in df.columns if 'penalt' in c.lower()), None)

    if not penalty_col:
        return pd.DataFrame([{"Error": "Penalty column missing"}])

    forecast = df.groupby(name_col)[penalty_col].mean().reset_index()
    forecast.columns = ['EmployeeName', 'AvgPenalty']
    forecast['ExpectedNextPenalty'] = forecast['AvgPenalty'] * 1.05  # simulate 5% increase
    return forecast
