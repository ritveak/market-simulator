"""Data loader for CSV price files.

Data format: 2 columns only - Date, Close.
- Built-in files: Date in DD/MM/YY
- User uploads: Date in MM/DD/YY (as specified in upload instructions)
"""
import pandas as pd
from pathlib import Path
from typing import List, Tuple


RESOURCES_DIR = Path(__file__).resolve().parent.parent.parent / "resources"


def discover_csv_files() -> List[Tuple[str, Path]]:
    """Recursively discover all CSV files in resources folder.
    Returns list of (display_label, file_path) tuples.
    """
    if not RESOURCES_DIR.exists():
        return []
    files = []
    for path in RESOURCES_DIR.rglob("*.csv"):
        rel = path.relative_to(RESOURCES_DIR)
        label = str(rel).replace("\\", "/")
        files.append((label, path))
    return sorted(files, key=lambda x: x[0])


def load_price_data(file_path: Path, start_date: pd.Timestamp = None, end_date: pd.Timestamp = None) -> pd.DataFrame:
    """Load and normalize price data from CSV.
    
    Expected format: Date (DD/MM/YY), Close - two columns only.
    """
    df = pd.read_csv(file_path)
    if "Date" not in df.columns or "Close" not in df.columns:
        raise ValueError(f"CSV must have Date and Close columns. Found: {list(df.columns)}")
    
    # Parse DD/MM/YY format (handles D/M/YY as well)
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%y", dayfirst=True, errors="coerce")
    df = df.sort_values("Date").reset_index(drop=True)
    df = df[["Date", "Close"]].dropna()
    
    if start_date is not None:
        df = df[df["Date"] >= start_date]
    if end_date is not None:
        df = df[df["Date"] <= end_date]
    
    df = df.set_index("Date").sort_index()
    return df


def load_price_data_from_upload(file_like, start_date: pd.Timestamp = None, end_date: pd.Timestamp = None) -> pd.DataFrame:
    """Load price data from an uploaded file (e.g. from st.file_uploader).

    Expected format: Date (MM/DD/YY), Close - two columns only.
    """
    df = pd.read_csv(file_like)
    if "Date" not in df.columns or "Close" not in df.columns:
        raise ValueError(f"CSV must have 'Date' and 'Close' columns. Found: {list(df.columns)}")

    # Parse MM/DD/YY format
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%y", errors="coerce")
    df = df.sort_values("Date").reset_index(drop=True)
    df = df[["Date", "Close"]].dropna()

    if start_date is not None:
        df = df[df["Date"] >= start_date]
    if end_date is not None:
        df = df[df["Date"] <= end_date]

    df = df.set_index("Date").sort_index()
    return df
