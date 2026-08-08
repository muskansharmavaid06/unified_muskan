import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer

def load_and_merge_data(clients_path, properties_path):
    clients_df = pd.read_csv(clients_path)
    properties_df = pd.read_csv(properties_path)
    
    # Clean sale_price column in properties
    if 'sale_price' in properties_df.columns:
        properties_df['sale_price_clean'] = (
            properties_df['sale_price']
            .astype(str)
            .str.replace('$', '', regex=False)
            .str.replace(',', '', regex=False)
            .astype(float)
        )
    
    # Aggregate property metrics per client
    sold_props = properties_df[properties_df['listing_status'] == 'Sold']
    client_property_agg = sold_props.groupby('client_ref').agg(
        total_investment=('sale_price_clean', 'sum'),
        total_properties=('listing_id', 'count'),
        avg_property_size=('floor_area_sqft', 'mean')
    ).reset_index()
    
    # Merge with client records
    merged_df = pd.merge(
        clients_df, 
        client_property_agg, 
        left_on='client_id', 
        right_on='client_ref', 
        how='left'
    )
    
    # Fill non-purchasing or missing aggregations
    merged_df['total_investment'] = merged_df['total_investment'].fillna(0)
    merged_df['total_properties'] = merged_df['total_properties'].fillna(0)
    merged_df['avg_property_size'] = merged_df['avg_property_size'].fillna(0)
    
    # Compute Age
    merged_df['date_of_birth'] = pd.to_datetime(merged_df['date_of_birth'], errors='coerce')
    current_year = datetime.now().year
    merged_df['age'] = current_year - merged_df['date_of_birth'].dt.year
    merged_df['age'] = merged_df['age'].fillna(merged_df['age'].median())
    
    return merged_df

def prepare_features(df):
    feature_cols = [
        'client_type', 'gender', 'country', 'region', 
        'acquisition_purpose', 'loan_applied', 'referral_channel',
        'satisfaction_score', 'age', 'total_investment', 'total_properties'
    ]
    
    data = df[feature_cols].copy()
    
    categorical_cols = ['client_type', 'gender', 'country', 'region', 'acquisition_purpose', 'loan_applied', 'referral_channel']
    numeric_cols = ['satisfaction_score', 'age', 'total_investment', 'total_properties']
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_cols)
        ]
    )
    
    X_processed = preprocessor.fit_transform(data)
    return X_processed, preprocessor