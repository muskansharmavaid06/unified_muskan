import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="EduPro - Course Demand & Revenue Forecasting",
    page_icon="",
    layout="wide"
)

# ---------------------------------------------------------
# 1. DATA LOADING HELPER (WITH ALL 4 SHEETS)
# ---------------------------------------------------------
@st.cache_data
def load_excel_data(file_path_or_buffer):
    """Reads Excel file containing Users, Teachers, Courses, and Transactions sheets."""
   
    excel_file = 'Instructor_Performance_and_Course_Quality_Evaluation_on_EduPro/read_edu.xlsx'

     # Raw Sheet Loading
    raw_users_df = pd.read_excel(excel_file, sheet_name='Users')
    raw_teachers_df = pd.read_excel(excel_file, sheet_name='Teachers')
    raw_courses_df = pd.read_excel(excel_file, sheet_name='Courses')
    raw_transactions_df = pd.read_excel(excel_file, sheet_name='Transactions')

    # Mapping to exact requested structure
    users_df = pd.DataFrame({
        'UserID': raw_users_df['UserID'],
        'UserName': raw_users_df['UserName'],
        'Age': raw_users_df['Age'],
        'Gender': raw_users_df['Gender'],
        'Email': raw_users_df['Email'],
    })

    teachers_df = pd.DataFrame({
        'TeacherID': raw_teachers_df['TeacherID'],
        'TeacherName': raw_teachers_df['TeacherName'],
        'Age': raw_teachers_df['Age'],
        'Gender': raw_teachers_df['Gender'],
        'Expertise': raw_teachers_df['Expertise'],
        'YearsOfExperience': raw_teachers_df['YearsOfExperience'],
        'TeacherRating': raw_teachers_df['TeacherRating'],
    })

    courses_df = pd.DataFrame({
        'CourseID': raw_courses_df['CourseID'],
        'CourseName': raw_courses_df['CourseName'],
        'CourseCategory': raw_courses_df['CourseCategory'],
        'CourseLevel': raw_courses_df['CourseLevel'],
        'CourseRating': raw_courses_df['CourseRating'],
    })
    
    # Handle optional price/type if missing in raw courses sheet
    if 'CoursePrice' in raw_courses_df.columns:
        courses_df['CoursePrice'] = raw_courses_df['CoursePrice']
    else:
        courses_df['CoursePrice'] = 100.0

    if 'CourseType' in raw_courses_df.columns:
        courses_df['CourseType'] = raw_courses_df['CourseType']
    else:
        courses_df['CourseType'] = 'Self-Paced'

    if 'CourseDuration' in raw_courses_df.columns:
        courses_df['CourseDuration'] = raw_courses_df['CourseDuration']
    else:
        courses_df['CourseDuration'] = 20

    transactions_df = pd.DataFrame({
        'TransactionID': raw_transactions_df['TransactionID'],
        'UserID': raw_transactions_df['UserID'],
        'CourseID': raw_transactions_df['CourseID'],
        'TeacherID': raw_transactions_df['TeacherID'],
    })

    if 'Amount' in raw_transactions_df.columns:
        transactions_df['Amount'] = raw_transactions_df['Amount']
    else:
        # Fallback amount merged from course price
        transactions_df = pd.merge(transactions_df, courses_df[['CourseID', 'CoursePrice']], on='CourseID', how='left')
        transactions_df['Amount'] = transactions_df['CoursePrice'].fillna(50)

    return users_df, teachers_df, courses_df, transactions_df




def load_excel_data_from_dfs(raw_users_df, raw_teachers_df, raw_courses_df, raw_transactions_df):
    """Formats raw dataframes into specified user structure."""
    users_df = pd.DataFrame({
        'UserID': raw_users_df['UserID'],
        'UserName': raw_users_df['UserName'],
        'Age': raw_users_df['Age'],
        'Gender': raw_users_df['Gender'],
        'Email': raw_users_df['Email'],
    })

    teachers_df = pd.DataFrame({
        'TeacherID': raw_teachers_df['TeacherID'],
        'TeacherName': raw_teachers_df['TeacherName'],
        'Age': raw_teachers_df['Age'],
        'Gender': raw_teachers_df['Gender'],
        'Expertise': raw_teachers_df['Expertise'],
        'YearsOfExperience': raw_teachers_df['YearsOfExperience'],
        'TeacherRating': raw_teachers_df['TeacherRating'],
    })

    courses_df = pd.DataFrame({
        'CourseID': raw_courses_df['CourseID'],
        'CourseName': raw_courses_df['CourseName'],
        'CourseCategory': raw_courses_df['CourseCategory'],
        'CourseLevel': raw_courses_df['CourseLevel'],
        'CourseRating': raw_courses_df['CourseRating'],
        'CoursePrice': raw_courses_df['CoursePrice'],
        'CourseType': raw_courses_df['CourseType'],
        'CourseDuration': raw_courses_df['CourseDuration']
    })

    transactions_df = pd.DataFrame({
        'TransactionID': raw_transactions_df['TransactionID'],
        'UserID': raw_transactions_df['UserID'],
        'CourseID': raw_transactions_df['CourseID'],
        'TeacherID': raw_transactions_df['TeacherID'],
        'Amount': raw_transactions_df['Amount']
    })

    return users_df, teachers_df, courses_df, transactions_df

# ---------------------------------------------------------
# 2. FEATURE ENGINEERING & PREPROCESSING
# ---------------------------------------------------------
def process_data(users_df, teachers_df, courses_df, transactions_df):
    # Aggregating transaction metrics at Course level
    tx_agg = transactions_df.groupby('CourseID').agg(
        EnrollmentCount=('TransactionID', 'count'),
        CourseRevenue=('Amount', 'sum'),
        AvgTransactionValue=('Amount', 'mean'),
        UniqueUsers=('UserID', 'nunique')
    ).reset_index()

    # Link primary teacher per course from transaction data
    course_teacher_map = transactions_df.groupby('CourseID')['TeacherID'].agg(
        lambda x: x.mode()[0] if not x.empty else None
    ).reset_index()
    
    courses_with_teacher = pd.merge(courses_df, course_teacher_map, on='CourseID', how='left')
    merged = pd.merge(courses_with_teacher, teachers_df, on='TeacherID', how='left')

    df = pd.merge(merged, tx_agg, on='CourseID', how='left').fillna({
        'EnrollmentCount': 0,
        'CourseRevenue': 0,
        'AvgTransactionValue': 0,
        'UniqueUsers': 0,
        'YearsOfExperience': teachers_df['YearsOfExperience'].median(),
        'TeacherRating': teachers_df['TeacherRating'].median()
    })

    # ---------------------------------------------------------
    # SAFE FEATURE ENGINEERING (FIXES THE VALUEERROR)
    # ---------------------------------------------------------
    
    # SAFE PRICE BANDS: Using rank/pct or cut to guarantee label matching
    try:
        df['PriceBand'] = pd.qcut(df['CoursePrice'], q=3, labels=['Low', 'Medium', 'High'], duplicates='drop')
    except ValueError:
        # Fallback if qcut drops edges due to duplicate prices
        df['PriceBand'] = pd.cut(df['CoursePrice'], bins=3, labels=['Low', 'Medium', 'High'])

    # SAFE DURATION BUCKETS: Exactly 4 bin edges [0, 15, 35, 100] -> Exactly 3 labels
    df['DurationBucket'] = pd.cut(
        df['CourseDuration'], 
        bins=[-1, 15, 35, 1000],  # -1 handles 0-hour durations safely
        labels=['Short', 'Medium', 'Long']
    )

    df['ExpertiseMatchScore'] = (df['CourseCategory'] == df['Expertise']).astype(int)
    df['RevenuePerEnrollment'] = np.where(df['EnrollmentCount'] > 0, df['CourseRevenue'] / df['EnrollmentCount'], 0)

    return df
# ---------------------------------------------------------
# 3. MODEL TRAINING
# ---------------------------------------------------------
def train_predictive_models(df):
    le_category = LabelEncoder()
    le_level = LabelEncoder()
    le_type = LabelEncoder()

    df_model = df.copy()
    df_model['Category_Enc'] = le_category.fit_transform(df_model['CourseCategory'].astype(str))
    df_model['Level_Enc'] = le_level.fit_transform(df_model['CourseLevel'].astype(str))
    df_model['Type_Enc'] = le_type.fit_transform(df_model['CourseType'].astype(str))

    feature_cols = [
        'CoursePrice', 'CourseDuration', 'CourseRating', 
        'YearsOfExperience', 'TeacherRating', 'ExpertiseMatchScore',
        'Category_Enc', 'Level_Enc', 'Type_Enc'
    ]

    X = df_model[feature_cols]
    y_enroll = df_model['EnrollmentCount']
    y_rev = df_model['CourseRevenue']

    X_train, X_test, y_enroll_train, y_enroll_test, y_rev_train, y_rev_test = train_test_split(
        X, y_enroll, y_rev, test_size=0.2, random_state=42
    )

    model_enroll = RandomForestRegressor(n_estimators=100, random_state=42)
    model_enroll.fit(X_train, y_enroll_train)

    model_rev = GradientBoostingRegressor(n_estimators=100, random_state=42)
    model_rev.fit(X_train, y_rev_train)

    y_enroll_pred = model_enroll.predict(X_test)
    y_rev_pred = model_rev.predict(X_test)

    metrics = {
        'Enrollment': {
            'MAE': round(mean_absolute_error(y_enroll_test, y_enroll_pred), 2),
            'RMSE': round(float(np.sqrt(mean_squared_error(y_enroll_test, y_enroll_pred))), 2),
            'R2': round(r2_score(y_enroll_test, y_enroll_pred), 3)
        },
        'Revenue': {
            'MAE': round(mean_absolute_error(y_rev_test, y_rev_pred), 2),
            'RMSE': round(float(np.sqrt(mean_squared_error(y_rev_test, y_rev_pred))), 2),
            'R2': round(r2_score(y_rev_test, y_rev_pred), 3)
        }
    }

    encoders = {'Category': le_category, 'Level': le_level, 'Type': le_type}
    return model_enroll, model_rev, feature_cols, metrics, encoders

# ---------------------------------------------------------
# 4. STREAMLIT APPLICATION
# ---------------------------------------------------------
def main():
    st.title("EduPro - Course Demand & Revenue Forecasting")
    st.markdown("Forecasting enrollment demand and revenue analytics across Users, Teachers, Courses, and Transactions.")

    
    default_filename = 'Predictive_Modeling_for_Course_Demand_and_Revenue_Forecasting_on_EduPro/read_edu.xlsx'

    if os.path.exists(default_filename):
       
        users_df, teachers_df, courses_df, transactions_df = load_excel_data(default_filename)
    else:
        st.sidebar.warning(f"`{default_filename}` not found locally.")
        uploaded_file = st.sidebar.file_uploader("Upload Excel File (.xlsx)", type=['xlsx'])
        if uploaded_file is not None:
            users_df, teachers_df, courses_df, transactions_df = load_excel_data(uploaded_file)
        else:
            st.sidebar.info("Using synthetic demo data.")
            users_df, teachers_df, courses_df, transactions_df = generate_demo_data()

    # Process Data
    df = process_data(users_df, teachers_df, courses_df, transactions_df)
    model_enroll, model_rev, feature_cols, metrics, encoders = train_predictive_models(df)

    # Dashboard Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Predictive Simulator", 
        "Revenue Analytics", 
        "User Demographics",
        "Feature Importance", 
        "Category Demand"
    ])

    # TAB 1: Live Interactive Predictor
    with tab1:
        st.subheader("Predict Outcomes for New or Modified Courses")
        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox("Course Category", encoders['Category'].classes_)
            course_type = st.selectbox("Course Type", encoders['Type'].classes_)
            level = st.selectbox("Course Level", encoders['Level'].classes_)
        
        with col2:
            price = st.slider("Course Price ($)", 10.0, 500.0, 99.0)
            duration = st.slider("Duration (Hours)", 1, 100, 20)
            course_rating = st.slider("Target Course Rating", 1.0, 5.0, 4.5)

        with col3:
            exp = st.slider("Instructor Experience (Years)", 0, 30, 5)
            teacher_rating = st.slider("Instructor Rating", 1.0, 5.0, 4.7)
            expertise_match = st.radio("Expertise Match?", [1, 0], format_func=lambda x: "Yes" if x == 1 else "No")

        cat_enc = encoders['Category'].transform([category])[0]
        level_enc = encoders['Level'].transform([level])[0]
        type_enc = encoders['Type'].transform([course_type])[0]

        input_data = pd.DataFrame([[
            price, duration, course_rating, exp, teacher_rating, expertise_match, cat_enc, level_enc, type_enc
        ]], columns=feature_cols)

        pred_enroll = max(0, int(model_enroll.predict(input_data)[0]))
        pred_rev = max(0.0, float(model_rev.predict(input_data)[0]))

        st.markdown("---")
        res1, res2 = st.columns(2)
        res1.metric("Predicted Enrollments", f"{pred_enroll} Students")
        res2.metric("Predicted Total Revenue", f"${pred_rev:,.2f}")

    # TAB 2: Revenue Analytics
    with tab2:
        st.subheader("Category-Level Performance & Model Metrics")
        m_col1, m_col2 = st.columns(2)
        
        with m_col1:
            st.write("### Enrollment Model Metrics")
            st.json(metrics['Enrollment'])

        with m_col2:
            st.write("### Revenue Model Metrics")
            st.json(metrics['Revenue'])

        st.subheader("Total Revenue by Category")
        cat_agg = df.groupby('CourseCategory').agg({
            'EnrollmentCount': 'sum',
            'CourseRevenue': 'sum'
        }).reset_index()

        fig_cat = px.bar(
            cat_agg, x='CourseCategory', y='CourseRevenue', 
            color='CourseCategory', title="Total Revenue by Course Category",
            text_auto='.2s'
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    # TAB 3: User Demographics
    with tab3:
        st.subheader("User Community Overview")
        u_col1, u_col2 = st.columns(2)
        
        with u_col1:
            fig_gender = px.pie(users_df, names='Gender', title='User Gender Distribution')
            st.plotly_chart(fig_gender, use_container_width=True)

        with u_col2:
            fig_age = px.histogram(users_df, x='Age', nbins=15, title='User Age Distribution', color_discrete_sequence=['#636EFA'])
            st.plotly_chart(fig_age, use_container_width=True)

    # TAB 4: Feature Importance
    with tab4:
        st.subheader("Key Drivers of Demand & Revenue")
        fi_df = pd.DataFrame({
            'Feature': feature_cols,
            'Enrollment_Importance': model_enroll.feature_importances_,
            'Revenue_Importance': model_rev.feature_importances_
        }).sort_values(by='Revenue_Importance', ascending=False)

        fig_fi = px.bar(
            fi_df, x='Revenue_Importance', y='Feature', orientation='h',
            title="Feature Importance for Revenue Prediction",
            color='Revenue_Importance', color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_fi, use_container_width=True)

    # TAB 5: Category Demand Scatter
    with tab5:
        st.subheader("Enrollment vs. Pricing Distribution")
        fig_scatter = px.scatter(
            df, x='CoursePrice', y='EnrollmentCount', color='CourseCategory',
            size='CourseRevenue', hover_data=['CourseID', 'CourseRating'],
            title="Course Price vs. Enrollment Count (Bubble size = Total Revenue)"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

if __name__ == '__main__':
    main()
