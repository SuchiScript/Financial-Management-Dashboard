"""
Streamlit app for the financial dashboard
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from utils import read_csv_to_df, combine_dataframes, agg_monthly, agg_by_category_year

st.set_page_config(page_title="Financial Dashboard", layout="wide")

st.title("Financial Management Dashboard")

# Sidebar: Upload
st.sidebar.header("Upload CSV files")
uploaded_files = st.sidebar.file_uploader(
    "Upload one or more financial CSV files (one-year-per-file recommended)",
    type=["csv"],
    accept_multiple_files=True,
)



# Read uploaded files
dfs = []
errors = []
if uploaded_files:
    for f in uploaded_files:
        try:
            dfs.append(read_csv_to_df(f))
        except Exception as e:
            errors.append(str(e))


if errors:
    st.sidebar.error("Some files could not be read: " + "; ".join(errors))

# Combine
combined = combine_dataframes(dfs)

if combined.empty:
    st.info("No data loaded yet. Upload CSV files in the sidebar.")
    st.stop()

# Controls
st.sidebar.header("Filters")
all_years = sorted(combined["Year"].dropna().unique().astype(int).tolist())
selected_years = st.sidebar.multiselect("Years", all_years, default=all_years)

categories = sorted(combined["Category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect("Categories", categories, default=categories)

accounts = sorted(combined["Account"].dropna().unique().tolist())
selected_accounts = st.sidebar.multiselect("Accounts", accounts, default=accounts)

chart_type = st.sidebar.radio("Chart type", ["Line", "Bar", "Stacked Bar", "Pie"])

# Apply filters
df_filtered = combined[
    (combined["Year"].isin(selected_years))
    & (combined["Category"].isin(selected_categories))
    & (combined["Account"].isin(selected_accounts))
]

# Main layout
left_col, right_col = st.columns([3, 1])

with left_col:
    st.header("Trends & Charts")

    # Monthly aggregation
    monthly = agg_monthly(df_filtered)

    if monthly.empty:
        st.warning("No transactions found for selected filters")
    else:
        fig, ax = plt.subplots(figsize=(10, 5))

        if chart_type == "Line":
            ax.plot(monthly["YearMonth"], monthly["Income"], label="Income")
            ax.plot(monthly["YearMonth"], monthly["Expense"], label="Expense")
            ax.plot(monthly["YearMonth"], monthly["Net"], label="Net")
            ax.set_title("Monthly Income / Expense / Net")
            ax.legend()

        elif chart_type == "Bar":
            ax.bar(monthly["YearMonth"], monthly["Income"], label="Income", alpha=0.7)
            ax.bar(monthly["YearMonth"], -monthly["Expense"], label="Expense (neg)", alpha=0.7)
            ax.set_title("Monthly Income and Expense")
            ax.legend()

        elif chart_type == "Stacked Bar":
            ax.bar(monthly["YearMonth"], monthly["Income"], label="Income")
            ax.bar(monthly["YearMonth"], -monthly["Expense"],
                   bottom=monthly["Income"], label="Expense")
            ax.set_title("Stacked Monthly Income vs Expense")
            ax.legend()

        elif chart_type == "Pie":
            total_by_cat = df_filtered.groupby("Category").agg(Total=("SignedAmount", "sum")).abs()
            if total_by_cat.empty:
                st.warning("No data for pie chart")
            else:
                ax.pie(
                    total_by_cat["Total"],
                    labels=total_by_cat.index,
                    autopct="%.1f%%"
                )
                ax.set_title("Spending / Income share by Category")

        ax.set_xlabel("")
        fig.autofmt_xdate()
        st.pyplot(fig)

    # Yearly category comparison
    st.subheader("Category totals by Year")
    cat_year = agg_by_category_year(df_filtered)
    if not cat_year.empty:
        pivot = cat_year.pivot(index="Category", columns="Year", values="Total").fillna(0)
        st.dataframe(pivot)

with right_col:
    st.header("Summary")
    total_income = df_filtered.loc[df_filtered["SignedAmount"] > 0, "SignedAmount"].sum()
    total_expense = -df_filtered.loc[df_filtered["SignedAmount"] < 0, "SignedAmount"].sum()
    net = total_income - total_expense

    st.metric("Total income", f"{total_income:,.2f}")
    st.metric("Total expense", f"{total_expense:,.2f}")
    st.metric("Net", f"{net:,.2f}")

    st.markdown("---")
    st.subheader("Top categories (by absolute amount)")
    top_cat = (
        df_filtered.groupby("Category")
        .agg(Total=("SignedAmount", "sum"))
        .abs()
        .sort_values("Total", ascending=False)
    )
    st.table(top_cat.head(10))

# Raw data viewer
st.header("Raw data (filtered)")
st.dataframe(df_filtered)

# Export filtered CSV
csv = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button("Download filtered CSV", data=csv, file_name="filtered_financials.csv")
