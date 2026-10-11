import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
import datetime

# 1. Page Configuration
st.set_page_config(page_title="Elite Search Engine", layout="wide")

# 2. Secure BigQuery Client Initialization
import json
import tempfile
import os

def get_bq_client():
    if "gcp_service_account" in st.secrets:
        # Load credentials dict from st.secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Normalize private key newlines and whitespace
        if "private_key" in creds_dict:
            pk = creds_dict["private_key"]
            pk = pk.replace("\\\\n", "\n").replace("\\n", "\n").strip()
            creds_dict["private_key"] = pk
            
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        return bigquery.Client(credentials=credentials, project=credentials.project_id)
    else:
        return bigquery.Client.from_service_account_json("credentials.json")
    
client = get_bq_client()

# 3. User Credentials & Session State Setup
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
if "quotas" not in st.session_state:
    # Default monthly search quota tracking
    st.session_state["quotas"] = {
        "admin": 9999,
        "rex": 500,
        "daniel": 500,
        "eric": 500,
        "alex": 500,
        "tommy": 500,
        "kokhing": 500,
        "tony": 500,
        "user1": 500,
        "user2": 500
    }
if "usage" not in st.session_state:
    st.session_state["usage"] = {user: 0 for user in st.session_state["quotas"]}

# Simple User Database (Username: Password)
USERS = {
    "admin": "admin123",
    "rex": "rex123",
    "daniel": "daniel123",
    "eric": "eric123",
    "alex": "alex123",
    "tommy": "tommy123",
    "kokhing": "kokhing123",
    "tony": "tony123",
    "user1": "pass123",
    "user2": "pass123"
}

# 4. Login Screen Handler
def login_screen():
    st.title("🔐 Elite Search Engine - Login")
    with st.form("login_form"):
        username_input = st.text_input("Username").strip().lower()
        password_input = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if username_input in USERS and USERS[username_input] == password_input:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username_input
                st.session_state["is_admin"] = (username_input == "admin")
                st.success(f"Welcome back, {username_input}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

if not st.session_state["authenticated"]:
    login_screen()
else:
    # 5. Main Application Interface
    st.sidebar.title(f"👤 User: {st.session_state['username'].capitalize()}")
    
    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.session_state["is_admin"] = False
        st.rerun()

    current_user = st.session_state["username"]
    
    # Display Quota Tracker in Sidebar
    if not st.session_state["is_admin"]:
        used = st.session_state["usage"].get(current_user, 0)
        limit = st.session_state["quotas"].get(current_user, 500)
        st.sidebar.metric(label="Monthly Search Quota", value=f"{used} / {limit}")

    # Admin Dashboard Section
    if st.session_state["is_admin"] and st.sidebar.checkbox("🛠️ Open Admin Dashboard"):
        st.subheader("Admin Control Panel")
        st.write("Manage user search quotas and settings:")
        
        for u in st.session_state["quotas"]:
            if u != "admin":
                new_limit = st.sidebar.number_input(f"Quota for {u}", value=st.session_state["quotas"][u], key=f"quota_{u}")
                st.session_state["quotas"][u] = new_limit
        
        st.markdown("---")

    # 6. Search Panel
    st.title("🔍 Elite Search Engine")
    st.write("Search across your BigQuery database records securely.")

    search_query = st.text_input("Enter Name, IC, Phone, or Keyword to search:")

    if search_query:
        # Check quota limit for non-admin users
        if not st.session_state["is_admin"]:
            if st.session_state["usage"].get(current_user, 0) >= st.session_state["quotas"].get(current_user, 500):
                st.error("You have exceeded your monthly search quota limit. Please contact the administrator.")
                st.stop()
            else:
                st.session_state["usage"][current_user] += 1

        safe_query = search_query.replace("'", "\\'")
        
        # Construct BigQuery SQL Statement (Adjust table name as needed)
        sql_query = f"""
            SELECT * FROM `andyngpropertyhub-cloud.elite_search.dataset_table`
            WHERE LOWER(CONCAT_WS(' ', *)) LIKE '%{safe_query.lower()}%'
            LIMIT 100
        """

        try:
            with st.spinner("Querying BigQuery dataset..."):
                query_job = client.query(sql_query)
                df = query_job.to_dataframe()

                if not df.empty:
                    # 7. Column Hiding Privacy Filters
                    # Exclude sensitive columns from output view
                    hidden_columns = [
                        'jantina', 'Kodlokaliti', 'NamaParlimen', 
                        'NamaDM', 'NameDUN', 'KategoriPemilih', 
                        'nokp', 'name_tel'
                    ]
                    
                    display_columns = [col for col in df.columns if col not in hidden_columns]
                    filtered_df = df[display_columns]

                    st.success(f"Found {len(filtered_df)} matching records.")
                    st.dataframe(filtered_df, use_container_width=True)
                else:
                    st.info("No matching records found in the database.")
        except Exception as e:
            st.error(f"An error occurred while executing the query: {e}")