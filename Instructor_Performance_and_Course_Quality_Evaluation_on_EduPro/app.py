import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="EduPro | Instructor & Course Quality Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1rem;
        color: #4B5563;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADING & INTEGRATION FUNCTION
# ==========================================
@st.cache_data
def load_and_process_data():
    """
    Reads data from Excel file ('EduPro Online Platform.xlsx') containing 
    'Users', 'Teachers', 'Courses', and 'Transactions' sheets, 
    or falls back to individual CSV files / synthetic data generation.
    """
    excel_file = 'read_edu.xlsx'
    

    # Attempt to load directly from Excel Workbook with all sheets
    users_df = pd.read_excel(excel_file, sheet_name='Users')
    teachers_df = pd.read_excel(excel_file, sheet_name='Teachers')
    courses_df = pd.read_excel(excel_file, sheet_name='Courses')
    transactions_df = pd.read_excel(excel_file, sheet_name='Transactions')
 
            
       
            # Fallback: Synthetic Data Generation matching exact schema
            
            # 1. Users Data
        
    users_df = pd.DataFrame({
        'UserID':users_df['UserID'],
        'UserName': users_df['UserName'],
        'Age':users_df['Age'],
        'Gender':users_df['Gender'],
        'Email': users_df['Email'],
    })

    # 2. Teachers Data
    n_teachers = 50
    expertise_list = ['Data Science', 'Web Development', 'UI/UX Design', 'Business Analytics', 'Cloud Computing', 'AI & Machine Learning']
    teachers_df = pd.DataFrame({
        'TeacherID':teachers_df['TeacherID'],
        'TeacherName':teachers_df['TeacherName'],
        'Age': teachers_df['Age'],
        'Gender': teachers_df['Gender'],
        'Expertise': teachers_df['Expertise'],
        'YearsOfExperience': teachers_df['YearsOfExperience'],
        'TeacherRating': teachers_df['TeacherRating'],
            })

    # 3. Courses Data
    n_courses = 100
    categories = ['Technology', 'Design', 'Business', 'Data & AI', 'Marketing']
    levels = ['Beginner', 'Intermediate', 'Advanced']
    courses_df = pd.DataFrame({
        'CourseID': courses_df['CourseID'],
        'CourseName': courses_df['CourseName'],
        'CourseCategory': courses_df['CourseCategory'],
        'CourseLevel':courses_df['CourseLevel'],
        'CourseRating':courses_df['CourseRating'],
    })

    # 4. Transactions Data
    n_transactions = 1500
    transactions_df = pd.DataFrame({
        'TransactionID': transactions_df['TransactionID'],
        'UserID': transactions_df['UserID'],
        'CourseID':transactions_df['CourseID'],
        'TeacherID': transactions_df['TeacherID'],
    })

    # ------------------------------------------
    # DATA INTEGRATION & MERGING
    # Join Users <-> Transactions <-> Teachers <-> Courses
    # ------------------------------------------
    merged_df = transactions_df.copy()
    
    if 'UserID' in merged_df.columns and 'UserID' in users_df.columns:
        merged_df = merged_df.merge(users_df, on='UserID', how='inner', suffixes=('', '_User'))
        
    if 'TeacherID' in merged_df.columns and 'TeacherID' in teachers_df.columns:
        merged_df = merged_df.merge(teachers_df, on='TeacherID', how='inner', suffixes=('', '_Teacher'))
        
    if 'CourseID' in merged_df.columns and 'CourseID' in courses_df.columns:
        merged_df = merged_df.merge(courses_df, on='CourseID', how='inner', suffixes=('', '_Course'))

    # Define Instructor Rating Tiers
    def get_rating_tier(rating):
        if rating >= 4.5:
            return 'High-Rated (4.5 - 5.0)'
        elif rating >= 3.8:
            return 'Mid-Rated (3.8 - 4.49)'
        else:
            return 'Low-Rated (< 3.8)'
            
    if 'TeacherRating' in teachers_df.columns:
        teachers_df['RatingTier'] = teachers_df['TeacherRating'].apply(get_rating_tier)
    if 'TeacherRating' in merged_df.columns:
        merged_df['RatingTier'] = merged_df['TeacherRating'].apply(get_rating_tier)
    
    return users_df, teachers_df, courses_df, transactions_df, merged_df

# Load all 4 dataframes
users, teachers, courses, transactions, df = load_and_process_data()

# ==========================================
# 3. SIDEBAR FILTERS
# ==========================================


# Optional File Uploader in Sidebar


# Dynamic Filters
selected_expertise = st.sidebar.multiselect(
    "Select Instructor Expertise:",
    options=teachers['Expertise'].unique() if 'Expertise' in teachers.columns else [],
    default=teachers['Expertise'].unique() if 'Expertise' in teachers.columns else []
)

selected_category = st.sidebar.multiselect(
    "Select Course Category:",
    options=courses['CourseCategory'].unique() if 'CourseCategory' in courses.columns else [],
    default=courses['CourseCategory'].unique() if 'CourseCategory' in courses.columns else []
)

selected_level = st.sidebar.multiselect(
    "Select Course Level:",
    options=courses['CourseLevel'].unique() if 'CourseLevel' in courses.columns else [],
    default=courses['CourseLevel'].unique() if 'CourseLevel' in courses.columns else []
)

# Apply filters to merged dataframe
filtered_df = df[
    (df['Expertise'].isin(selected_expertise)) &
    (df['CourseCategory'].isin(selected_category)) &
    (df['CourseLevel'].isin(selected_level))
]

filtered_teachers = teachers[teachers['Expertise'].isin(selected_expertise)]

# ==========================================
# 4. DASHBOARD HEADER & KPIS
# ==========================================
st.markdown('<p class="main-header">EduPro Instructor Performance & Course Quality Analytics</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Data Integration across Users ↔ Teachers ↔ Courses ↔ Transactions</p>', unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Users", f"{len(users):,}")
col2.metric("Total Instructors", f"{len(teachers):,}")
col3.metric("Total Courses", f"{len(courses):,}")
col4.metric("Total Transactions", f"{len(transactions):,}")
col5.metric("Avg Course Rating", f"{courses['CourseRating'].mean():.2f}" if 'CourseRating' in courses.columns else "N/A")

st.markdown("---")

# ==========================================
# 5. DATA PREVIEW TAB & ANALYTICS
# ==========================================
tab_data, tab1, tab2, tab3 = st.tabs([
    "Raw Data Tables", 
    "Instructor Profile", 
    "Experience vs Performance", 
    "Course & User Demographics"
])

with tab_data:
    st.subheader("Data Sheets Overview")
    
    s_col1, s_col2 = st.columns(2)
    with s_col1:
        st.markdown("##### Users Sheet")
        st.dataframe(users.head(5), use_container_width=True)
        
        st.markdown("#####  Teachers Sheet")
        st.dataframe(teachers.head(5), use_container_width=True)
        
    with s_col2:
        st.markdown("##### Courses Sheet")
        st.dataframe(courses.head(5), use_container_width=True)
        
        st.markdown("##### Transactions Sheet")
        st.dataframe(transactions.head(5), use_container_width=True)

with tab1:
    st.subheader("Instructor Performance Profile")
    col_a, col_b = st.columns(2)
    with col_a:
        fig_exp = px.histogram(filtered_teachers, x='YearsOfExperience', nbins=10, title='Instructor Experience Distribution')
        st.plotly_chart(fig_exp, use_container_width=True)
    with col_b:
        fig_rat = px.box(filtered_teachers, y='TeacherRating', x='Gender', color='Gender', title='Teacher Rating Spread')
        st.plotly_chart(fig_rat, use_container_width=True)

with tab2:
    st.subheader("Experience vs. Performance Dynamics")
    fig_scat = px.scatter(filtered_teachers, x='YearsOfExperience', y='TeacherRating', color='Expertise', size='Age', title='Years of Experience vs Teacher Rating')
    st.plotly_chart(fig_scat, use_container_width=True)

with tab3:
    st.subheader("Learner & Course Demographics")
    if 'Gender' in users.columns:
        user_gender = users['Gender'].value_counts().reset_index()
        user_gender.columns = ['Gender', 'Count']
        fig_user = px.pie(user_gender, names='Gender', values='Count', title='User Base Gender Breakdown')
        st.plotly_chart(fig_user, use_container_width=True)