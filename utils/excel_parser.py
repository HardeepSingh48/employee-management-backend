import pandas as pd

REQUIRED_COLUMNS = [
    "Full Name", "Date of Birth", "Gender",
    "Site Name", "Rank", "State", "Base Salary"
]

def load_excel_to_frames(file_storage):
    """
    Returns dict: {sheet_name: DataFrame}
    Ensures required columns exist (case sensitive).
    """
    xls = pd.read_excel(file_storage, sheet_name=None)  # dict of dfs
    cleaned = {}
    for sheet, df in xls.items():
        if df.empty:
            continue
        # strip headers
        df.columns = [str(c).strip() for c in df.columns]
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Sheet '{sheet}' missing columns: {missing}")
        cleaned[sheet] = df
    if not cleaned:
        raise ValueError("No non-empty sheets found.")
    return cleaned
