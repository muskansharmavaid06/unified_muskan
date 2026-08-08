import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="Customer Engagement & Product Utilization Analytics",
    page_icon="📊",
    layout="wide"
)

# Set your fixed local CSV file path here
CSV_FILE_PATH = "European_Bank.csv"

@st.cache_data
def load_and_transform_csv_from_path(file_path):
    """
    Reads directly from a local CSV file path, validates data types,
    and updates/maps column values for consistency.
    """
    if not os.path.exists(file_path):
        return None
        
    # 1. Direct CSV Reading from File Path
    df = pd.read_csv(file_path)
    
    # Clean and standardize column names
    df.columns = df.columns.str.strip()

    # 2. Update and Validate Binary Column Values
    binary_columns = ['HasCrCard', 'IsActiveMember', 'Exited']
    for col in binary_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower().map({
                '1': 1, '1.0': 1, 'true': 1,
                '0': 0, '0.0': 0, 'false': 0
            }).fillna(0).astype(int)

    # 3. Update / Create Readable Churn Labels
    if 'Exited' in df.columns:
        df['Exited_Label'] = df['Exited'].map({0: 'Retained', 1: 'Churned'})
    
    # 4. Update Product Count Values
    if 'NumOfProducts' in df.columns:
        df['NumOfProducts'] = pd.to_numeric(df['NumOfProducts'], errors='coerce').fillna(1).astype(int)
        
    return df

# =============================================================================
# 2. FEATURE ENGINEERING & SEGMENTATION MODULE
# =============================================================================
def apply_analytics_features(df, balance_threshold, salary_threshold):
    # Create updated Engagement Profiles
    def classify_engagement(row):
        if row['IsActiveMember'] == 1 and row['NumOfProducts'] >= 2:
            return 'Active Engaged'
        elif row['IsActiveMember'] == 0 and row['NumOfProducts'] == 1:
            return 'Inactive Disengaged'
        elif row['IsActiveMember'] == 1 and row['NumOfProducts'] == 1:
            return 'Active Low-Product'
        elif row['IsActiveMember'] == 0 and row['Balance'] >= balance_threshold:
            return 'Inactive High-Balance'
        else:
            return 'Standard Customer'

    df['Engagement_Profile'] = df.apply(classify_engagement, axis=1)
    
    # Update Product Utilization Categories
    df['Product_Tier'] = df['NumOfProducts'].apply(lambda x: 'Single-Product' if x == 1 else 'Multi-Product')
    
    # Financial Mismatch & At-Risk Premium Identification
    df['High_Balance'] = df['Balance'] >= balance_threshold
    df['Low_Salary'] = df['EstimatedSalary'] <= salary_threshold
    df['Salary_Balance_Mismatch'] = df['High_Balance'] & df['Low_Salary']
    
    df['At_Risk_Premium'] = (
        (df['Balance'] >= balance_threshold) & 
        (df['IsActiveMember'] == 0) & 
        (df['NumOfProducts'] == 1)
    )
    
    # Sticky Customer Definition
    df['Is_Sticky'] = (df['IsActiveMember'] == 1) & (df['HasCrCard'] == 1) & (df['NumOfProducts'] >= 2)
    
    return df


st.title("Customer Engagement & Product Analytics Platform")
st.markdown("Analyze customer retention, engagement profiles, and product utilization directly from local CSV files.")



# Allow dynamic path editing in sidebar if needed, defaulting to CSV_FILE_PATH
file_path_input = st.sidebar.text_input("", value=CSV_FILE_PATH)

# Enforce Direct Reading from Path
if not os.path.exists(file_path_input):
    st.error(f"❌ Could not find CSV file at path: `{file_path_input}`. Please ensure the path is correct.")
    st.stop()

raw_df = load_and_transform_csv_from_path(file_path_input)



st.sidebar.subheader("Analysis Thresholds")
balance_threshold = st.sidebar.slider(
    "High-Balance Threshold ($)", 
    min_value=10000, max_value=200000, value=75000, step=5000
)
salary_threshold = st.sidebar.slider(
    "Low-Salary Threshold ($)", 
    min_value=10000, max_value=100000, value=40000, step=5000
)

# Dynamic Filters
st.sidebar.subheader(" Filtering Options")
geography_options = list(raw_df['Geography'].unique()) if 'Geography' in raw_df.columns else []
selected_geography = st.sidebar.multiselect(
    "Geography", 
    options=geography_options, 
    default=geography_options
)

min_prod = int(raw_df['NumOfProducts'].min())
max_prod = int(raw_df['NumOfProducts'].max())
product_filter = st.sidebar.slider(
    "Product Count Range", 
    min_value=min_prod, 
    max_value=max_prod, 
    value=(min_prod, max_prod)
)

engagement_filter = st.sidebar.multiselect(
    "Active Status", 
    options=["Active", "Inactive"], 
    default=["Active", "Inactive"]
)

# Apply User Capabilities (Filtering)
filtered_df = raw_df.copy()
if 'Geography' in filtered_df.columns and selected_geography:
    filtered_df = filtered_df[filtered_df['Geography'].isin(selected_geography)]

filtered_df = filtered_df[filtered_df['NumOfProducts'].between(product_filter[0], product_filter[1])]

active_values = []
if "Active" in engagement_filter:
    active_values.append(1)
if "Inactive" in engagement_filter:
    active_values.append(0)

filtered_df = filtered_df[filtered_df['IsActiveMember'].isin(active_values)]

# Apply Features and Calculations
df = apply_analytics_features(filtered_df, balance_threshold, salary_threshold)

# -----------------------------------------------------------------------------
# KPI DASHBOARD SUMMARY
# -----------------------------------------------------------------------------
st.markdown("---")
st.header("Key Performance Indicators (KPIs)")

active_churn = df[df['IsActiveMember'] == 1]['Exited'].mean() if len(df[df['IsActiveMember'] == 1]) > 0 else 0
inactive_churn = df[df['IsActiveMember'] == 0]['Exited'].mean() if len(df[df['IsActiveMember'] == 0]) > 0 else 0
engagement_retention_ratio = (1 - active_churn) / (1 - inactive_churn) if (1 - inactive_churn) > 0 else np.nan

multi_prod = df[df['NumOfProducts'] > 1]
single_prod = df[df['NumOfProducts'] == 1]
multi_prod_retention = (1 - multi_prod['Exited'].mean()) if len(multi_prod) > 0 else 0
single_prod_retention = (1 - single_prod['Exited'].mean()) if len(single_prod) > 0 else 0
product_depth_index = multi_prod_retention / single_prod_retention if single_prod_retention > 0 else np.nan

high_bal_disengaged = df[(df['Balance'] >= balance_threshold) & (df['IsActiveMember'] == 0)]
high_bal_disengaged_churn = high_bal_disengaged['Exited'].mean() if len(high_bal_disengaged) > 0 else 0.0

card_owners_churn = df[df['HasCrCard'] == 1]['Exited'].mean() if len(df[df['HasCrCard'] == 1]) > 0 else 0
non_card_churn = df[df['HasCrCard'] == 0]['Exited'].mean() if len(df[df['HasCrCard'] == 0]) > 0 else 0
credit_card_stickiness = (1 - card_owners_churn) - (1 - non_card_churn)

rsi_score = ((df['IsActiveMember'].mean() * 0.4) + ((df['NumOfProducts'] / 4).mean() * 0.4) + ((1 - df['Exited'].mean()) * 0.2)) * 100

kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
kpi_col1.metric("Engagement Retention Ratio", f"{engagement_retention_ratio:.2f}x" if not np.isnan(engagement_retention_ratio) else "N/A")
kpi_col2.metric("Product Depth Index", f"{product_depth_index:.2f}x" if not np.isnan(product_depth_index) else "N/A")
kpi_col3.metric("High-Bal Disengagement Churn", f"{high_bal_disengaged_churn:.1%}")
kpi_col4.metric("Credit Card Stickiness", f"{credit_card_stickiness:+.1%}")
kpi_col5.metric("Relationship Strength Index", f"{rsi_score:.1f}/100")

# -----------------------------------------------------------------------------
# CORE MODULES
# -----------------------------------------------------------------------------
st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs([
    "Engagement vs Churn Overview",
    "Product Utilization Impact",
    "High-Value Disengaged Detector",
    "Retention Strength Panels"
])

# MODULE 1: Engagement vs Churn Overview
with tab1:
    st.subheader("Engagement Profiles & Churn Distribution")
    col1, col2 = st.columns(2)
    
    with col1:
        prof_df = df.groupby(['Engagement_Profile', 'Exited_Label']).size().reset_index(name='Count')
        prof_fig = px.bar(
            prof_df, x='Engagement_Profile', y='Count', color='Exited_Label',
            barmode='group', title="Customer Count by Engagement Profile & Churn Status",
            color_discrete_map={'Retained': '#2ecc71', 'Churned': '#e74c3c'}
        )
        st.plotly_chart(prof_fig, use_container_width=True)
        
    with col2:
        churn_rate_profile = df.groupby('Engagement_Profile')['Exited'].mean().reset_index()
        churn_rate_profile['Churn Rate (%)'] = churn_rate_profile['Exited'] * 100
        rate_fig = px.bar(
            churn_rate_profile, x='Engagement_Profile', y='Churn Rate (%)',
            title="Churn Rate % across Engagement Tiers", text_auto='.1f',
            color='Churn Rate (%)', color_continuous_scale='Reds'
        )
        st.plotly_chart(rate_fig, use_container_width=True)

# MODULE 2: Product Utilization Impact Analysis
with tab2:
    st.subheader("Product Depth vs Retention Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        prod_churn = df.groupby('NumOfProducts')['Exited'].mean().reset_index()
        prod_churn['Churn Rate (%)'] = prod_churn['Exited'] * 100
        prod_fig = px.line(
            prod_churn, x='NumOfProducts', y='Churn Rate (%)', markers=True,
            title="Churn Rate by Number of Products Held",
            labels={'NumOfProducts': 'Number of Products'}
        )
        st.plotly_chart(prod_fig, use_container_width=True)
        
    with col2:
        tier_churn = df.groupby('Product_Tier')['Exited_Label'].value_counts(normalize=True).unstack().fillna(0).reset_index()
        tier_fig = px.bar(
            tier_churn, x='Product_Tier', y=['Retained', 'Churned'],
            title="Single-Product vs Multi-Product Retention Comparison",
            barmode='stack', color_discrete_map={'Retained': '#3498db', 'Churned': '#e67e22'}
        )
        st.plotly_chart(tier_fig, use_container_width=True)

# MODULE 3: High-Value Disengaged Customer Detector
with tab3:
    st.subheader("High-Value & Premium Customer Risk Detection")
    col1, col2 = st.columns(2)
    
    with col1:
        scatter_fig = px.scatter(
            df, x='Balance', y='EstimatedSalary', color='At_Risk_Premium',
            symbol='Exited_Label',
            title="Salary vs. Balance (Highlighting At-Risk Premium Customers)",
            labels={'At_Risk_Premium': 'At-Risk Premium'},
            color_discrete_map={True: '#e74c3c', False: '#95a5a6'},
            hover_data=['CustomerId', 'NumOfProducts', 'Age']
        )
        st.plotly_chart(scatter_fig, use_container_width=True)
        
    with col2:
        mismatch_count = df['Salary_Balance_Mismatch'].value_counts().reset_index()
        mismatch_count.columns = ['Is_Mismatch', 'Count']
        mismatch_fig = px.pie(
            mismatch_count, names='Is_Mismatch', values='Count',
            title="Salary–Balance Mismatch Detection Share",
            color_discrete_sequence=['#f39c12', '#2c3e50']
        )
        st.plotly_chart(mismatch_fig, use_container_width=True)
        
    st.markdown("Identified At-Risk Premium Customers")
    cols_to_show = [c for c in ['CustomerId', 'Surname', 'Geography', 'Balance', 'EstimatedSalary', 'NumOfProducts', 'Exited_Label'] if c in df.columns]
    at_risk_df = df[df['At_Risk_Premium']][cols_to_show]
    st.dataframe(at_risk_df, use_container_width=True)

# MODULE 4: Retention Strength Scoring Panels
with tab4:
    st.subheader("Retention Strength & Customer Stickiness Profiles")
    col1, col2 = st.columns(2)
    
    with col1:
        sticky_summary = df.groupby('Is_Sticky')['Exited_Label'].value_counts(normalize=True).unstack().fillna(0).reset_index()
        sticky_fig = px.bar(
            sticky_summary, x='Is_Sticky', y=['Retained', 'Churned'],
            title="Sticky Customer Profile vs Normal Churn Rates",
            labels={'Is_Sticky': 'Is Sticky Customer'},
            barmode='group', color_discrete_map={'Retained': '#2ecc71', 'Churned': '#e74c3c'}
        )
        st.plotly_chart(sticky_fig, use_container_width=True)
        
    with col2:
        heatmap_data = df.pivot_table(index='NumOfProducts', columns='IsActiveMember', values='Exited', aggfunc='mean')
        heatmap_fig = px.imshow(
            heatmap_data, 
            labels=dict(x="Active Member (0=No, 1=Yes)", y="Number of Products", color="Churn Rate"),
            title="Retention Matrix (Product Count x Active Status)",
            color_continuous_scale="Reds", text_auto=".2f"
        )
        st.plotly_chart(heatmap_fig, use_container_width=True)