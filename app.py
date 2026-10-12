import streamlit as st
from google.cloud import bigquery
import base64
import tempfile
import os
import datetime

# Page Configuration
st.set_page_config(page_title="Elite Search Engine", page_icon="🔍", layout="wide")

# Initialize Session State for Usage/Admin if not present
if "usage" not in st.session_state:
    st.session_state["usage"] = {}
if "quotas" not in st.session_state:
    st.session_state["quotas"] = {}
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
if "user_logs" not in st.session_state:
    st.session_state["user_logs"] = []

# Mock Current User for demonstration
current_user = st.text_input("Username / ID:", value="user_default")

# Admin Toggle (For testing logs & usage)
st.sidebar.title("Admin Controls")
st.session_state["is_admin"] = st.sidebar.checkbox("Enable Admin Mode", value=st.session_state["is_admin"])

# 1. Birthday Banner on Front Page
today = datetime.date.today()
# Example birthday check or toggle/banner display
st.markdown(
    """
    <div style="background-color: #ffeb3b; padding: 10px; border-radius: 5px; text-align: center; color: #000; margin-bottom: 20px;">
        🎉 <b>Happy Birthday to all users celebrating their special day this month!</b> Wishing you success and happiness! 🎂
    </div>
    """,
    unsafe_allow_html=True
)

# 6. Search Panel
st.title("🔍 Elite Search Engine")
st.write("Search across your BigQuery database records securely.")

# Admin Dashboard Section
if st.session_state["is_admin"]:
    st.subheader("📊 Admin Usage & User Logs Dashboard")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("### Monthly & Current Search Usage by User")
        if st.session_state["usage"]:
            usage_data = [{"User": u, "Searches Used": count} for u, count in st.session_state["usage"].items()]
            st.dataframe(usage_data, use_container_width=True)
            st.write(f"**Total Searches Across All Users:** {sum(st.session_state['usage'].values())}")
        else:
            st.info("No search usage recorded yet this month.")
            
    with col2:
        st.write("### Recent Search Activity Logs")
        if st.session_state["user_logs"]:
            st.dataframe(st.session_state["user_logs"][-10:], use_container_width=True) # Show last 10 logs
        else:
            st.info("No activity logs recorded yet.")
    st.markdown("---")

# Negeri filter
selected_negeri = st.selectbox(
    "Select or filter by Negeri (State):", 
    ["KLANG VALLEY (KUALA LUMPUR & SELANGOR)", "ALL", "SELANGOR", "KUALA LUMPUR", "JOHOR", "PENANG", "PERAK", "MELAKA", "NEGERI SEMBILAN", "PAHANG", "KELANTAN", "TERENGGANU", "KEDAH", "PERLIS", "SABAH", "SARAWAK"]
)

# Default setting is Exact Match
match_type = st.radio(
    "Select Search Match Type:", 
    ["Exact Match", "Similar (Partial Match)"], 
    horizontal=True
)

search_query = st.text_input("Enter Name, IC, or Phone to search:")

if search_query:
    # Check quota limit for non-admin users
    if not st.session_state["is_admin"]:
        if st.session_state["usage"].get(current_user, 0) >= st.session_state["quotas"].get(current_user, 500):
            st.error("You have exceeded your monthly search quota limit. Please contact the administrator.")
            st.stop()
        else:
            st.session_state["usage"][current_user] = st.session_state["usage"].get(current_user, 0) + 1

    # Log the user search action
    st.session_state["user_logs"].append({
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "User": current_user,
        "Query": search_query,
        "Match Type": match_type
    })

    safe_query = search_query.replace("'", "\\'")
    
    # Construct BigQuery SQL Statement based on Match Type
    if match_type == "Exact Match":
        sql_query = f"""
            SELECT * FROM `mysej-510709.mysej.combined_data`
            WHERE (LOWER(Nama) = '{safe_query.lower()}'
               OR CAST(nokp AS STRING) = '{safe_query}'
               OR LOWER(tel1) = '{safe_query.lower()}'
            )
        """
    else:
        sql_query = f"""
            SELECT * FROM `mysej-510709.mysej.combined_data`
            WHERE (LOWER(Nama) LIKE '%{safe_query.lower()}%'
               OR CAST(nokp AS STRING) LIKE '%{safe_query.lower()}%'
               OR LOWER(tel1) LIKE '%{safe_query.lower()}%'
            )
        """
    
    # Apply Negeri filter logic
    if selected_negeri == "KLANG VALLEY (KUALA LUMPUR & SELANGOR)":
        sql_query += f" AND UPPER(negeri) IN ('KUALA LUMPUR', 'SELANGOR')"
    elif selected_negeri != "ALL":
        sql_query += f" AND UPPER(negeri) = '{selected_negeri}'"
        
    sql_query += " LIMIT 100"

    # Initialize BigQuery Client (assuming function is defined in your script)
    # client = get_bq_client()

    try:
        with st.spinner("Querying BigQuery dataset..."):
            query_job = client.query(sql_query)
            df = query_job.to_dataframe()

            if not df.empty:
                # 1 & 2. Force IC/nokp to string format so it doesn't display as scientific notation (e.g. 6.20803E+11)
                if 'nokp' in df.columns:
                    df['nokp'] = df['nokp'].astype(str).str.replace(r'\.0$', '', regex=True)

                # 3. Expanded hidden columns list (Including Unnamed__0, Jastina/jantina, NamaDUN, name_tel, etc.)
                hidden_columns = [
                    'jantina', 'Jastina', 'Kodlokaliti', 'NamaParlimen', 
                    'NamaDM', 'NameDUN', 'NamaDUN', 'KategoriPemilih', 
                    'name_tel', 'Unnamed__0'
                ]
                
                available_cols = [col for col in df.columns if col not in hidden_columns]
                
                # Force order: nokp first, followed by Nama, tel1, and the rest
                front_cols = []
                for col_name in ['nokp', 'Nama', 'tel1']:
                    if col_name in available_cols:
                        front_cols.append(col_name)
                        
                display_cols = front_cols + [col for col in available_cols if col not in front_cols]
                filtered_df = df[display_cols]

                # Sort by IC (nokp) ascending
                if 'nokp' in filtered_df.columns:
                    filtered_df = filtered_df.sort_values(by='nokp', ascending=True)

                st.success(f"Found {len(filtered_df)} matching records.")
                st.dataframe(filtered_df, use_container_width=True)
            else:
                st.info("No matching records found in the database.")
    except Exception as e:
        st.error(f"An error occurred while executing the query: {e}")