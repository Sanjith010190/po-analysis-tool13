
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(layout="wide")
st.title("📊 Purchase Order Analysis Tool")

@st.cache_data
def load_data(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file, parse_dates=["Report Date"], low_memory=False)
    elif file.name.endswith(".parquet"):
        return pd.read_parquet(file)
    elif file.name.endswith(".xlsx"):
        return pd.read_excel(file, parse_dates=["Report Date"])
    else:
        st.error("Unsupported file type.")
        return pd.DataFrame()

uploaded_file = st.file_uploader("Upload your Purchase Order dataset (.csv, .xlsx, .parquet)", type=["csv", "xlsx", "parquet"])
if uploaded_file:
    df = load_data(uploaded_file)
    required_cols = ["Supplier", "Cost Center Code", "Purchase Order Value", "Receipted Value", "Invoiced Value", "Report Date", "PO Number", "Description", "Item Description"]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"Missing required columns: {', '.join(missing_cols)}")
        st.write("Available columns:", list(df.columns))
        st.stop()

    st.success(f"Loaded {len(df):,} rows.")

    for col in ["Purchase Order Value", "Receipted Value", "Invoiced Value"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sidebar filters
    with st.sidebar:
        st.header("🔍 Filters")
        min_date, max_date = df["Report Date"].min(), df["Report Date"].max()
        date_range = st.date_input("Report Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

        all_suppliers = sorted(df["Supplier"].dropna().unique())
        all_centers = sorted(df["Cost Center Code"].dropna().unique())

        select_all_suppliers = st.checkbox("Select All Suppliers", value=True)
        selected_suppliers = st.multiselect("Suppliers", all_suppliers, default=all_suppliers if select_all_suppliers else [])

        select_all_centers = st.checkbox("Select All Cost Center Codes", value=True)
        selected_centers = st.multiselect("Cost Center Codes", all_centers, default=all_centers if select_all_centers else [])

    mask = (
        (df["Report Date"] >= pd.to_datetime(date_range[0])) &
        (df["Report Date"] <= pd.to_datetime(date_range[1]))
    )
    if selected_suppliers:
        mask &= df["Supplier"].isin(selected_suppliers)
    if selected_centers:
        mask &= df["Cost Center Code"].isin(selected_centers)

    filtered_df = df[mask].copy()
    filtered_df["Unreceipted Value"] = filtered_df["Purchase Order Value"] - filtered_df["Receipted Value"]
    filtered_df["Uninvoiced Value"] = filtered_df["Receipted Value"] - filtered_df["Invoiced Value"]

    if not filtered_df.empty:
        filtered_df = filtered_df.copy(deep=False)
        # KPIs
        st.subheader("📈 Summary KPIs")
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total PO Value", f"£{filtered_df['Purchase Order Value'].sum():,.2f}")
        k2.metric("Receipted", f"£{filtered_df['Receipted Value'].sum():,.2f}")
        k3.metric("Invoiced", f"£{filtered_df['Invoiced Value'].sum():,.2f}")
        k4.metric("Unreceipted", f"£{filtered_df['Unreceipted Value'].sum():,.2f}")
        k5.metric("Uninvoiced", f"£{filtered_df['Uninvoiced Value'].sum():,.2f}")

        # Summary by Supplier
        st.subheader("📋 Summary by Supplier")
        summary = (
            filtered_df.groupby("Supplier")[["Purchase Order Value", "Receipted Value", "Invoiced Value", "Unreceipted Value", "Uninvoiced Value"]]
            .sum()
            .sort_values("Purchase Order Value", ascending=False)
        )
        st.dataframe(summary.style.format("£{:,.2f}"), use_container_width=True)

        # Drilldown Table
        st.subheader("📑 PO-Level Drilldown")
        drilldown_df = filtered_df[filtered_df["Supplier"].isin(selected_suppliers)]
        drilldown_df = drilldown_df[[
            "Supplier", "PO Number", "Description", "Item Description", "Cost Center Code", "Report Date",
            "Purchase Order Value", "Receipted Value", "Invoiced Value",
            "Unreceipted Value", "Uninvoiced Value"
        ]]
        numeric_cols = ["Purchase Order Value", "Receipted Value", "Invoiced Value", "Unreceipted Value", "Uninvoiced Value"]

        # Disable formatting if too large
        max_cells = 250000
        total_cells = drilldown_df.shape[0] * drilldown_df.shape[1]
        if total_cells > max_cells:
            st.warning("Large table detected — formatting disabled for performance.")
            st.dataframe(drilldown_df, use_container_width=True)
        else:
            
        styled_df = drilldown_df.style.format({col: "£{:,.2f}" for col in numeric_cols})
        st.dataframe(styled_df, use_container_width=True)
    

        
        # Supplier Trend Chart
        st.subheader("📈 Supplier PO Value Over Time")
        trend_df = (
            filtered_df.groupby(["Report Date", "Supplier"])["Purchase Order Value"]
            .sum()
            .reset_index()
            .sort_values("Report Date")
        )
        fig_trend = px.line(trend_df, x="Report Date", y="Purchase Order Value", color="Supplier", title="PO Value Trend by Supplier")
        st.plotly_chart(fig_trend, use_container_width=True)

        
        # Cost Center Trend Chart
        st.subheader("📉 Cost Center PO Value Over Time")
        cc_trend_df = (
            filtered_df.groupby(["Report Date", "Cost Center Code"])["Purchase Order Value"]
            .sum()
            .reset_index()
            .sort_values("Report Date")
        )
        fig_cc_trend = px.line(cc_trend_df, x="Report Date", y="Purchase Order Value", color="Cost Center Code", title="PO Value Trend by Cost Center Code")
        st.plotly_chart(fig_cc_trend, use_container_width=True)

        # Charts
        col1, col2 = st.columns(2)
        with col1:
            chart1 = filtered_df.groupby("Supplier")["Purchase Order Value"].sum().nlargest(10).reset_index()
            fig1 = px.bar(chart1, x="Supplier", y="Purchase Order Value", title="Top 10 Suppliers by PO Value")
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            chart2 = filtered_df.groupby("Cost Center Code")["Purchase Order Value"].sum().nlargest(10).reset_index()
            fig2 = px.pie(chart2, names="Cost Center Code", values="Purchase Order Value", title="Top Cost Centers")
            st.plotly_chart(fig2, use_container_width=True)

        # Export
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=filtered_df.to_csv(index=False).encode("utf-8"),
            file_name="filtered_po_data.csv",
            mime="text/csv"
        )
    else:
        st.warning("No data found with the selected filters.")
else:
    st.info("Upload a file to begin.")
