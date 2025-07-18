# prediction.py
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder

def predict_attrition(df):
    name_col = next((col for col in df.columns if 'name' in col.lower()), None)
    dept_col = next((col for col in df.columns if 'depart' in col.lower() or 'plant' in col.lower()), None)
    salary_col = next((col for col in df.columns if 'net' in col.lower() and 'salary' in col.lower()), None)
    present_col = next((col for col in df.columns if 'present' in col.lower()), None)
    total_days_col = next((col for col in df.columns if 'total' in col.lower() and 'day' in col.lower()), None)
    penalty_col = next((col for col in df.columns if 'penalt' in col.lower()), None)
    skill_col = next((col for col in df.columns if 'skill' in col.lower()), None)

    required_cols = [dept_col, salary_col, present_col, total_days_col, penalty_col]
    df[required_cols] = df[required_cols].fillna(0)

    df['AttendanceRate'] = df[present_col] / (df[total_days_col] + 1)
    df['PenaltyRate'] = df[penalty_col] / (df[salary_col] + 1)

    features = ['AttendanceRate', 'PenaltyRate', salary_col]

    if dept_col:
        le_dept = LabelEncoder()
        df['DeptEncoded'] = le_dept.fit_transform(df[dept_col].astype(str))
        features.append('DeptEncoded')

    if skill_col:
        le_skill = LabelEncoder()
        df['SkillEncoded'] = le_skill.fit_transform(df[skill_col].astype(str))
        features.append('SkillEncoded')

    df['Attrition'] = ((df['AttendanceRate'] < 0.75) & (df['PenaltyRate'] > 0.01)).astype(int)

    df = df.dropna(subset=features + ['Attrition'])

    if df.empty:
        return pd.DataFrame(columns=["No data available for prediction"])

    X = df[features]
    y = df['Attrition']
    model = RandomForestClassifier(random_state=42)
    model.fit(X, y)
    df['Attrition_Risk'] = model.predict(X)

    output_cols = [name_col, dept_col, salary_col, present_col, total_days_col, penalty_col,
                   'AttendanceRate', 'PenaltyRate']
    risky_df = df[df['Attrition_Risk'] == 1]
    risky_employees = risky_df[output_cols].sort_values(by='PenaltyRate', ascending=False).head(10)

    return risky_employees

def get_attrition_by_department(df):
    dept_col = next((col for col in df.columns if 'depart' in col.lower() or 'plant' in col.lower()), None)
    present_col = next((col for col in df.columns if 'present' in col.lower()), None)
    total_days_col = next((col for col in df.columns if 'total' in col.lower() and 'day' in col.lower()), None)
    penalty_col = next((col for col in df.columns if 'penalt' in col.lower()), None)

    if not all([dept_col, present_col, total_days_col, penalty_col]):
        return pd.DataFrame(columns=["Department", "Attrition Risk Score"])

    df[[present_col, total_days_col, penalty_col]] = df[[present_col, total_days_col, penalty_col]].fillna(0)

    df['AttendanceRate'] = df[present_col] / (df[total_days_col] + 1)
    df['PenaltyRate'] = df[penalty_col] / (df[penalty_col].max() + 1)
    df['RiskScore'] = (1 - df['AttendanceRate']) + df['PenaltyRate']

    dept_risk = df.groupby(dept_col)['RiskScore'].mean().reset_index()
    dept_risk.columns = ["Department", "Attrition Risk Score"]
    return dept_risk.sort_values(by="Attrition Risk Score", ascending=False)

def forecast_penalty(df):
    name_col = next((col for col in df.columns if 'name' in col.lower()), None)
    penalty_col = next((col for col in df.columns if 'penalt' in col.lower()), None)
    present_col = next((col for col in df.columns if 'present' in col.lower()), None)
    total_days_col = next((col for col in df.columns if 'total' in col.lower() and 'day' in col.lower()), None)

    if not all([name_col, penalty_col, present_col, total_days_col]):
        return pd.DataFrame(columns=["Employee", "Predicted Penalty"])

    df[[penalty_col, present_col, total_days_col]] = df[[penalty_col, present_col, total_days_col]].fillna(0)

    df['AttendanceRate'] = df[present_col] / (df[total_days_col] + 1)
    features = df[['AttendanceRate']]
    target = df[penalty_col]

    model = LinearRegression()
    model.fit(features, target)
    df['PredictedPenalty'] = model.predict(features)

    result = df[[name_col, penalty_col, 'PredictedPenalty']].copy()
    result.columns = ["Employee", "Current Penalty", "Predicted Penalty"]
    return result.sort_values(by="Predicted Penalty", ascending=False).head(10)

