"""
Streamlit app for the financial dashboard
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplcursors
import seaborn as sns
from pathlib import Path
import plotly.graph_objects as go
from matplotlib import cm, colors as mcolors
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

        def palette_hex(cmap_name, n):
            if n == 0:
                return []
            cmap = cm.get_cmap(cmap_name)
            vals = cmap(np.linspace(0.35, 0.85, n))
            return [mcolors.to_hex(v) for v in vals]


        # ----------------------------- LINE CHART -----------------------------
        if chart_type == "Line":
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=monthly["YearMonth"],
                y=monthly["Income"],
                mode='lines+markers',
                name='Income'
            ))

            fig.add_trace(go.Scatter(
                x=monthly["YearMonth"],
                y=monthly["Expense"],
                mode='lines+markers',
                name='Expense'
            ))

            fig.add_trace(go.Scatter(
                x=monthly["YearMonth"],
                y=monthly["Net"],
                mode='lines+markers',
                name='Net'
            ))

            fig.update_layout(
                title="Monthly Income / Expense / Net",
                xaxis_title="Month",
                yaxis_title="Amount",
                template="simple_white"
            )


        # ---------------------- SIDE-BY-SIDE STACKED BAR CHART ----------------------
        elif chart_type == "Bar":
            df_copy = df_filtered.copy()
            df_copy["YearMonth"] = df_copy["Date"].dt.to_period("M").dt.to_timestamp()

            income_df = df_copy[df_copy["Type"] == "Income"]
            expense_df = df_copy[df_copy["Type"] == "Expense"]

            income_pivot = income_df.pivot_table(
                index="YearMonth", columns="Category", values="Amount",
                aggfunc="sum", fill_value=0
            )
            expense_pivot = expense_df.pivot_table(
                index="YearMonth", columns="Category", values="Amount",
                aggfunc="sum", fill_value=0
            )

            # Sort categories by size
            if not income_pivot.empty:
                income_pivot = income_pivot[income_pivot.sum().sort_values(ascending=False).index]
            if not expense_pivot.empty:
                expense_pivot = expense_pivot[expense_pivot.sum().sort_values(ascending=False).index]

            all_months = sorted(set(income_pivot.index) | set(expense_pivot.index))
            x_str = [m.strftime("%Y-%m") for m in all_months]

            income_pivot = income_pivot.reindex(all_months, fill_value=0)
            expense_pivot = expense_pivot.reindex(all_months, fill_value=0)

            income_colors = palette_hex("Blues", len(income_pivot.columns))
            expense_colors = palette_hex("Oranges", len(expense_pivot.columns))

            fig = go.Figure()

            # Income bars (stacked)
            for idx, col in enumerate(income_pivot.columns):
                fig.add_trace(go.Bar(
                    name=f"Income - {col}",
                    x=x_str,
                    y=income_pivot[col].values,
                    offsetgroup="income",
                    marker_color=income_colors[idx],
                    hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:,.2f}<extra></extra>",
                ))

            # Expense bars (stacked)
            for idx, col in enumerate(expense_pivot.columns):
                fig.add_trace(go.Bar(
                    name=f"Expense - {col}",
                    x=x_str,
                    y=expense_pivot[col].values,
                    offsetgroup="expense",
                    marker_color=expense_colors[idx],
                    hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:,.2f}<extra></extra>",
                ))

            fig.update_layout(
                title="Monthly Income & Expense Breakdown by Category",
                barmode="stack",
                xaxis_title="Month",
                yaxis_title="Amount",
                legend=dict(orientation="v", x=1.02, y=1),
                template="simple_white",
                margin=dict(l=40, r=260, t=60, b=80)
            )


        # ---------------------- STACKED BAR (INCOME+EXPENSE) ----------------------
        elif chart_type == "Stacked Bar":
            fig = go.Figure()

            fig.add_trace(go.Bar(
                name="Income",
                x=monthly["YearMonth"].dt.strftime("%Y-%m"),
                y=monthly["Income"],
                marker_color="#1f77b4"
            ))

            fig.add_trace(go.Bar(
                name="Expense",
                x=monthly["YearMonth"].dt.strftime("%Y-%m"),
                y=monthly["Expense"],
                marker_color="#ff7f0e"
            ))

            fig.update_layout(
                title="Stacked Monthly Income and Expense",
                barmode="stack",
                xaxis_title="Month",
                yaxis_title="Amount",
                template="simple_white"
            )


        # ---------------------- PIE CHART (EXPENSE ONLY) ----------------------
        elif chart_type == "Pie":
            expense_df = df_filtered[df_filtered["Type"] == "Expense"]

            totals = (
                expense_df.groupby("Category")["Amount"].sum()
                .sort_values(ascending=False)
            )

            fig = go.Figure()

            fig.add_trace(go.Pie(
                labels=totals.index,
                values=totals.values,
                hole=0.4,  # donut for readability
                textinfo="none",  # no labels on slices
                hovertemplate="%{label}: %{value:,.2f}<extra></extra>"
            ))

            fig.update_layout(
                title="Expense Share by Category",
                legend=dict(orientation="v", x=1.02, y=1),
                template="simple_white"
            )


        # ---------------------- RENDER PLOT ----------------------
        st.plotly_chart(fig, use_container_width=True)

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
