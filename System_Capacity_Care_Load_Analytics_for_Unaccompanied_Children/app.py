import numpy as np
import pandas as pd
import streamlit as st

# ==========================================
# 1. DATA INGESTION & STRUCTURING
# ==========================================


def load_and_structure_data(file_path_or_df):
    """Loads daily time-series data (2023-2025), converts dates, sorts

    chronologically, and reindexes to a complete daily calendar.
    """
    if isinstance(file_path_or_df, str):
        df = pd.read_csv("HHS_Unaccompanied_Alien_Children_Program.csv")
    else:
        df = file_path_or_df.copy()

    # Convert Date column to datetime
    df["Date"] = pd.to_datetime(df["Date"])

    # Remove duplicate dates keeping the first record
    df = df.drop_duplicates(subset=["Date"])

    # Ensure chronological ordering
    df = df.sort_values("Date").reset_index(drop=True)

    # Create complete daily date index to expose missing days
    full_date_range = pd.date_range(
        start=df["Date"].min(), end=df["Date"].max(), freq="D"
    )
    df = df.set_index("Date").reindex(full_date_range)
    df.index.name = "Date"
    df = df.reset_index()

    return df


# ==========================================
# 2. DATA QUALITY & VALIDATION
# ==========================================


def validate_and_flag_data(df):
    """Validates logical constraints, identifies missing dates, and flags

    anomalies.
    """
    df = df.copy()

    # Flag missing dates filled during reindexing
    df["Anomaly_Missing_Date"] = df["Children in HHS Care"].isna()

    # Forward-fill or interpolate missing daily figures for analytics continuity
    metric_cols = [
        "Children apprehended and placed in CBP custody",
        "Children in CBP custody",
        "Children transferred out of CBP custody",
        "Children in HHS Care",
        "Children discharged from HHS Care",
    ]
    df[metric_cols] = df[metric_cols].ffill().bfill()

    # Validate logical constraints
    # Constraint 1: Transfers out of CBP <= CBP Custody
    df["Constraint_Transfers_Valid"] = (
        df["Children transferred out of CBP custody"]
        <= df["Children in CBP custody"]
    )

    # Constraint 2: Discharges from HHS <= HHS Care
    df["Constraint_Discharges_Valid"] = (
        df["Children discharged from HHS Care"] <= df["Children in HHS Care"]
    )

    # Flag general reporting anomalies
    df["Reporting_Anomaly"] = (
        (~df["Constraint_Transfers_Valid"])
        | (~df["Constraint_Discharges_Valid"])
        | (df["Anomaly_Missing_Date"])
    )

    return df


# ==========================================
# 3. DERIVED HEALTHCARE CAPACITY METRICS
# ==========================================


def compute_capacity_metrics(df):
    """Computes Total System Load, Net Daily Intake, Care Load Growth Rate, and

    Backlog Indicators.
    """
    df = df.copy()

    # Total System Load = CBP Custody + HHS Care
    df["Total System Load"] = (
        df["Children in CBP custody"] + df["Children in HHS Care"]
    )

    # Net Daily Intake = Transfers into HHS - Discharges from HHS
    df["Net Daily Intake"] = (
        df["Children transferred out of CBP custody"]
        - df["Children discharged from HHS Care"]
    )

    # Care Load Growth Rate = Day-over-Day % change in Total System Load
    df["Care Load Growth Rate (%)"] = (
        df["Total System Load"].pct_change() * 100
    ).fillna(0)

    # Backlog Indicator = Cumulative sum of net positive intake over time
    df["Backlog Indicator"] = df["Net Daily Intake"].cumsum()

    return df


# ==========================================
# 4. TREND, TEMPORAL & PRESSURE ANALYSIS
# ==========================================


def compute_trend_and_pressure_metrics(df):
    """Calculates rolling averages, volatility, and key KPIs."""
    df = df.copy()

    # Rolling Averages (7-day and 14-day)
    df["System_Load_7D_MA"] = df["Total System Load"].rolling(7).mean()
    df["System_Load_14D_MA"] = df["Total System Load"].rolling(14).mean()

    # 7-day Rolling Volatility (Standard Deviation)
    df["Care Load Volatility Index"] = (
        df["Total System Load"].rolling(7).std().fillna(0)
    )

    # Prolonged Strain Window: Total System Load exceeding 90th percentile over 7 consecutive days
    high_threshold = df["Total System Load"].quantile(0.90)
    df["High_Stress_Flag"] = df["Total System Load"] > high_threshold
    df["Prolonged_Strain_Window"] = (
        df["High_Stress_Flag"].rolling(7).sum() >= 5
    )

    return df


# ==========================================
# 5. KPI SUMMARY CALCULATOR
# ==========================================


def calculate_kpis(df):
    """Computes summary metrics for KPI display cards."""
    latest_row = df.iloc[-1]

    total_children = latest_row["Total System Load"]
    net_intake_pressure = df["Net Daily Intake"].tail(7).mean()
    volatility = df["Care Load Volatility Index"].tail(7).mean()
    backlog_rate = df["Net Daily Intake"].tail(14).sum()

    total_transfers = df["Children transferred out of CBP custody"].tail(
        30
    ).sum()
    total_discharges = df["Children discharged from HHS Care"].tail(30).sum()
    discharge_offset_ratio = (
        (total_discharges / total_transfers) if total_transfers > 0 else 0
    )

    return {
        "Total Children Under Care": int(total_children),
        "Net Intake Pressure (7d avg)": round(net_intake_pressure, 2),
        "Care Load Volatility Index": round(volatility, 2),
        "Backlog Accumulation Rate (14d total)": int(backlog_rate),
        "Discharge Offset Ratio (30d)": f"{round(discharge_offset_ratio * 100, 1)}%",
    }



def run_streamlit_app(df):
    st.set_page_config(page_title="UAC Care Load Analytics", layout="wide")
    st.title(" System Capacity & Care Load Analytics")

    # --- Sidebar Filters ---
    st.sidebar.header("User Capabilities & Filters")

    # Date Range Selector
    min_date, max_date = df["Date"].min().date(), df["Date"].max().date()
    start_date, end_date = st.sidebar.date_input(
        "Date Range Selector",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    # Time Granularity Filter
    granularity = st.sidebar.selectbox(
        "Time Granularity", options=["Daily", "Weekly", "Monthly"]
    )

    # Filter DataFrame by Date Range
    filtered_df = df[
        (df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)
    ].copy()

    # Resample based on granularity selection
    if granularity == "Weekly":
        resampled_df = (
            filtered_df.resample("W", on="Date").mean(numeric_only=True).reset_index()
        )
    elif granularity == "Monthly":
        resampled_df = (
            filtered_df.resample("ME", on="Date").mean(numeric_only=True).reset_index()
        )
    else:
        resampled_df = filtered_df

    # --- Core Module 1: KPI Summary Cards ---
    st.subheader("Key Performance Indicators (KPIs)")
    kpis = calculate_kpis(filtered_df)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Children Under Care", f"{kpis['Total Children Under Care']:,}")
    col2.metric("Net Intake Pressure", kpis["Net Intake Pressure (7d avg)"])
    col3.metric("Volatility Index", kpis["Care Load Volatility Index"])
    col4.metric(
        "Backlog Accumulation", kpis["Backlog Accumulation Rate (14d total)"]
    )
    col5.metric("Discharge Offset Ratio", kpis["Discharge Offset Ratio (30d)"])

    st.markdown("---")

    # --- Core Module 2: System Load Overview Pane ---
    st.subheader("System Load Overview Pane")
    st.line_chart(
        resampled_df.set_index("Date")[
            ["Total System Load", "System_Load_7D_MA", "System_Load_14D_MA"]
        ]
    )

    # --- Core Module 3: CBP vs HHS Load Comparison ---
    st.subheader("CBP Custody vs. HHS Care Comparison")
    st.area_chart(
        resampled_df.set_index("Date")[
            ["Children in CBP custody", "Children in HHS Care"]
        ]
    )

    # --- Core Module 4: Net Intake & Backlog Trends ---
    st.subheader(" Net Intake & Backlog Trends")
    st.line_chart(
        resampled_df.set_index("Date")[["Net Daily Intake", "Backlog Indicator"]]
    )


# ==========================================
# PIPELINE EXECUTION EXAMPLE
# ==========================================
if __name__ == "__main__":
    # Create sample synthetic data matching the project's exact schema
    dates = pd.date_range("2023-01-01", "2025-12-31", freq="D")
    np.random.seed(42)

    sample_data = pd.DataFrame(
        {
            "Date": dates,
            "Children apprehended and placed in CBP custody": np.random.randint(
                200, 600, len(dates)
            ),
            "Children in CBP custody": np.random.randint(1500, 3000, len(dates)),
            "Children transferred out of CBP custody": np.random.randint(
                150, 500, len(dates)
            ),
            "Children in HHS Care": np.random.randint(8000, 12000, len(dates)),
            "Children discharged from HHS Care": np.random.randint(
                100, 450, len(dates)
            ),
        }
    )

    # Run Data Pipeline
    df_structured = load_and_structure_data(sample_data)
    df_validated = validate_and_flag_data(df_structured)
    df_metrics = compute_capacity_metrics(df_validated)
    df_final = compute_trend_and_pressure_metrics(df_metrics)

    # Run Streamlit Web Application
    # To run in local terminal: streamlit run <script_name>.py
    run_streamlit_app(df_final)