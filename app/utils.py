"""
Utility functions for the Streamlit financial dashboard
"""
from typing import List
import pandas as pd
import numpy as np

REQUIRED_COLS = ["Date", "Category", "Account", "Type", "Amount"]


def read_csv_to_df(file) -> pd.DataFrame:
    """
    Read uploaded CSV or file-like object into a cleaned DataFrame.
    """
    df = pd.read_csv(file)

    # Normalize column names
    df.columns = [c.strip() for c in df.columns]

    if "Date" not in df.columns:
        for alt in ["date", "DATE"]:
            if alt in df.columns:
                df.rename(columns={alt: "Date"}, inplace=True)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Ensure required columns exist
    for col in ["Category", "Account", "Type", "Amount"]:
        if col not in df.columns:
            if col == "Account":
                df["Account"] = "Unknown"
            else:
                raise ValueError(f"Required column '{col}' not found.")

    # Normalize type
    df["Type"] = df["Type"].astype(str).str.strip().str.title()
    df.loc[~df["Type"].isin(["Income", "Expense"]), "Type"] = "Expense"

    # Amount numeric
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    # Year and Month
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month

    # Signed amount (income positive, expense negative)
    df["SignedAmount"] = df.apply(
        lambda r: r["Amount"] if r["Type"] == "Income" else -abs(r["Amount"]), axis=1
    )

    return df


def combine_dataframes(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    if not dfs:
        return pd.DataFrame()
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined[~combined["Date"].isna()].copy()
    combined.sort_values("Date", inplace=True)
    return combined


def agg_monthly(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["YearMonth"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby(["YearMonth"]).agg(
        Income=("SignedAmount", lambda s: s[s > 0].sum()),
        Expense=("SignedAmount", lambda s: -s[s < 0].sum()),
        Net=("SignedAmount", "sum"),
    )
    monthly.reset_index(inplace=True)
    return monthly


def agg_by_category_year(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(["Year", "Category"])
        .agg(Total=("SignedAmount", "sum"))
        .reset_index()
    )
    return summary
