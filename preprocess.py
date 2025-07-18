# preprocess.py
import pandas as pd

def detect_month_from_filename(filename):
    filename = filename.lower()
    for month in ["jan", "feb", "mar", "apr", "may", "jun",
                  "jul", "aug", "sep", "oct", "nov", "dec"]:
        if month in filename:
            return month.capitalize()
    return "Unknown"

def clean_and_label(dfs: list):
    all_data = []
    for df in dfs:
        source = df['SourceFile'].iloc[0]
        month = detect_month_from_filename(source)
        df['UploadMonth'] = month

        name_col = next((c for c in df.columns if 'name' in c.lower()), None)
        if name_col:
            df.rename(columns={name_col: 'EmployeeName'}, inplace=True)

        all_data.append(df)

    return pd.concat(all_data, ignore_index=True)
