import streamlit as st
import pandas as pd
import plotly.express as px
from src.loader import load_and_merge_data, prepare_features
from src.modeling import evaluate_kmeans, run_clustering

st.set_page_config(
    page_title="Parcl - Buyer Segmentation Dashboard",
    layout="wide"
)

st.title("Real Estate Buyer Segmentation & Market Intelligence")
st.markdown("AI-driven Buyer Profiling and Analytics Platform for **Parcl Co. Limited**.")

@st.cache_data
def load_data():
    df = load_and_merge_data('data/clients.csv', 'data/properties.csv')
    X, _ = prepare_features(df)
    labels = run_clustering(X, n_clusters=4, method='kmeans')
    
    # Assign cluster labels mapped to target segments
    cluster_map = {
        0: 'C1 - Global Investors',
        1: 'C2 - First-Time Buyers',
        2: 'C3 - Corporate Buyers',
        3: 'C4 - Luxury Investors'
    }
    df['Cluster'] = [cluster_map[label] for label in labels]
    return df

df = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Global Dashboard Filters")
country_filter = st.sidebar.multiselect("Select Country", options=df['country'].dropna().unique(), default=df['country'].dropna().unique())
region_filter = st.sidebar.multiselect("Select Region", options=df['region'].dropna().unique(), default=df['region'].dropna().unique())
purpose_filter = st.sidebar.multiselect("Acquisition Purpose", options=df['acquisition_purpose'].dropna().unique(), default=df['acquisition_purpose'].dropna().unique())
type_filter = st.sidebar.multiselect("Client Type", options=df['client_type'].dropna().unique(), default=df['client_type'].dropna().unique())

filtered_df = df[
    (df['country'].isin(country_filter)) &
    (df['region'].isin(region_filter)) &
    (df['acquisition_purpose'].isin(purpose_filter)) &
    (df['client_type'].isin(type_filter))
]

# --- MAIN DASHBOARD TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    " Buyer Segmentation Overview", 
    " Investor Behavior Dashboard", 
    " Geographic Buyer Analysis", 
    " Segment Insights Panel"
])

with tab1:
    st.subheader("Buyer Distribution across Clusters")
    col1, col2 = st.columns([2, 1])
    
    fig_pie = px.pie(
        filtered_df, names='Cluster', title="Buyer Segment Distribution",
        color_discrete_sequence=px.colors.sequential.RdBu
    )
    col1.plotly_chart(fig_pie, use_container_width=True)
    
    col2.metric("Total Filtered Clients", len(filtered_df))
    col2.metric("Total Portfolio Value", f"${filtered_df['total_investment'].sum():,.2f}")

with tab2:
    st.subheader("Investment Patterns & Financial Profile")
    fig_box = px.box(
        filtered_df, x='Cluster', y='total_investment', color='Cluster',
        title="Total Investment Amount by Buyer Segment", points="all"
    )
    st.plotly_chart(fig_box, use_container_width=True)
    
    fig_bar = px.histogram(
        filtered_df, x='Cluster', color='loan_applied', barmode='group',
        title="Loan Application Distribution per Segment"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    st.subheader("Geographic Distribution of Buyer Segments")
    geo_df = filtered_df.groupby(['country', 'Cluster']).size().reset_index(name='count')
    fig_geo = px.bar(
        geo_df, x='country', y='count', color='Cluster', title="Buyers by Country & Cluster",
        barmode='stack'
    )
    st.plotly_chart(fig_geo, use_container_width=True)

with tab4:
    st.subheader("Segment Summary & Descriptive Statistics")
    summary = filtered_df.groupby('Cluster').agg({
        'age': 'mean',
        'satisfaction_score': 'mean',
        'total_investment': 'mean',
        'total_properties': 'mean'
    }).reset_index()
    
    st.dataframe(summary.style.format({
        'age': '{:.1f}',
        'satisfaction_score': '{:.2f}',
        'total_investment': '${:,.2f}',
        'total_properties': '{:.1f}'
    }), use_container_width=True)