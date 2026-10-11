import streamlit as st
from datetime import datetime
from google.cloud import bigquery
from google.oauth2 import service_account

# 1. Page Configuration
st.set_page_config(page_title="Elite Search Engine", page_icon="⚡", layout="wide")

# 2. Define Initial Users and Limits
if "users" not in st.session_state:
    st.session_state["users"] = {
        "admin": "admin123",
        "Rex": "105271",
        "Daniel": "566289",
        "Eric": "065303",
        "Alex": "126231",
        "Tommy": "085133",
        "Kokhing": "085853",
        "tony": "123456",
        "user1": "123456",
        "user2": "123456"
    }

# Monthly search limits per user (Default: 500 searches/month)
if "user_limits" not in st.session_state:
    st.session_state["user_limits"] = {user: 500 for user in st.session_state["users"]}

# Track searches and login logs: {username: {"search_count": int, "monthly_searches": { "2026-10": int }, "login_logs": [...]}}
if "user_stats" not in st.session_state:
    st.session_state["user_stats"] = {user: {"search_count": 0, "monthly_searches": {}, "login_logs": []} for user in st.session_state["users"]}

# 3. Initialize Authentication Session State
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# 4. Login Screen
def login_screen():
    st.title("🔒 Login to Elite Search Engine")
    st.write("Please enter your credentials to access the database.")

    with st.form("login_form"):
        username_input = st.text_input("Username").strip()
        password_input = st.text_input("Password", type="password").strip()
        submit_button = st.form_submit_button("Log In")

        if submit_button:
            users_dict = st.session_state["users"]
            # Case-insensitive username match check
            matched_user = next((u for u in users_dict if u.lower() == username_input.lower()), None)
            
            if matched_user and users_dict[matched_user] == password_input:
                st.session_state["authenticated"] = True
                st.session_state["username"] = matched_user
                
                # Log login timestamp
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if matched_user not in st.session_state["user_stats"]:
                    st.session_state["user_stats"][matched_user] = {"search_count": 0, "monthly_searches": {}, "login_logs": []}
                st.session_state["user_stats"][matched_user]["login_logs"].append(current_time)
                
                st.rerun()
            else:
                st.error("Invalid username or password. Please try again.")

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()

# ==============================================================================
# MAIN APP CONTENT
# ==============================================================================

current_user = st.session_state["username"]
current_month_key = datetime.now().strftime("%Y-%m")

st.sidebar.markdown(f"👤 **Logged in as:** `{current_user}`")
if st.sidebar.button("Log Out"):
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.rerun()

# User Password Change Expander (Available to all logged-in users)
with st.sidebar.expander("🔑 Change My Password"):
    old_pw = st.text_input("Current Password", type="password", key="old_pw")
    new_pw = st.text_input("New Password", type="password", key="new_pw")
    confirm_pw = st.text_input("Confirm New Password", type="password", key="confirm_pw")
    if st.button("Update My Password"):
        if old_pw == st.session_state["users"][current_user]:
            if new_pw and new_pw == confirm_pw:
                st.session_state["users"][current_user] = new_pw
                st.success("Password updated successfully!")
            else:
                st.error("New passwords do not match or are empty.")
        else:
            st.error("Incorrect current password.")

# Admin Panel (Only visible for admin)
if current_user == "admin":
    with st.sidebar.expander("🛠️ Admin Dashboard"):
        st.subheader("Manage Users & Limits")
        
        # Add User
        new_username = st.text_input("New Username").strip()
        new_password = st.text_input("New Password", type="password").strip()
        new_limit = st.number_input("Monthly Search Limit", min_value=1, value=500)
        if st.button("Add User"):
            if new_username and new_password:
                st.session_state["users"][new_username] = new_password
                st.session_state["user_limits"][new_username] = new_limit
                st.session_state["user_stats"][new_username] = {"search_count": 0, "monthly_searches": {}, "login_logs": []}
                st.success(f"User '{new_username}' added successfully!")
            else:
                st.error("Please enter both username and password.")
        
        st.divider()
        st.subheader("User Search Statistics & Quotas")
        for u, stats in st.session_state["user_stats"].items():
            monthly_count = stats["monthly_searches"].get(current_month_key, 0)
            limit = st.session_state["user_limits"].get(u, 500)
            st.markdown(f"**{u}** | Total: `{stats['search_count']}` | This Month (`{current_month_key}`): `{monthly_count}/{limit}`")
            
            # Allow admin to change limit
            updated_limit = st.number_input(f"Set limit for {u}", min_value=1, value=limit, key=f"limit_{u}")
            st.session_state["user_limits"][u] = updated_limit

st.title("⚡ Elite Search Engine")
st.write("Search across your 18.5M record dataset instantly via BigQuery.")

# Initialize BigQuery Client using local service account credentials file
@st.cache_resource
def get_bq_client():
    key_path = "credentials.json"
    credentials = service_account.Credentials.from_service_account_file(key_path)
    return bigquery.Client(credentials=credentials, project=credentials.project_id)

client = get_bq_client()

# Fetch unique Negeri list for the dropdown filter (cached for speed)
@st.cache_data
def get_negeri_options():
    try:
        query = "SELECT DISTINCT Negeri FROM `mysej-510709.mysej.combined_data` WHERE Negeri IS NOT NULL ORDER BY Negeri"
        df_negeri = client.query(query).to_dataframe()
        return ["ALL"] + df_negeri['Negeri'].tolist()
    except Exception:
        return ["ALL"]

negeri_list = get_negeri_options()

# Search Filters Sidebar
st.sidebar.header("Search Filters")

# State (Negeri) Dropdown with ALL option
selected_negeri = st.sidebar.selectbox("Filter by State (Negeri)", negeri_list)

# Name search fields & match type option
search_nama = st.sidebar.text_input("Search by Name (Nama)").strip().upper()
name_match_type = st.sidebar.radio("Name Match Type", ["Similar Name (Contains)", "Exact Match"])

# Other search fields
search_ic = st.sidebar.text_input("Search by IC Number").strip()
search_tel = st.sidebar.text_input("Search by Phone Number").strip()

if st.sidebar.button("Search Database"):
    # Check monthly limits before running query
    user_limit = st.session_state["user_limits"].get(current_user, 500)
    current_month_searches = st.session_state["user_stats"][current_user]["monthly_searches"].get(current_month_key, 0)
    
    if current_user != "admin" and current_month_searches >= user_limit:
        st.error(f"❌ Monthly search limit reached ({current_month_searches}/{user_limit}). Please contact admin.")
    elif not any([search_nama, search_ic, search_tel]) and selected_negeri == "ALL":
        st.warning("Please select a State (Negeri) or enter at least one search criterion.")
    else:
        with st.spinner("Executing fast BigQuery search..."):
            where_clauses = []
            
            # State filter
            if selected_negeri != "ALL":
                where_clauses.append(f"Negeri = '{selected_negeri}'")

            # Name filter with exact vs similar option
            if search_nama:
                if name_match_type == "Exact Match":
                    where_clauses.append(f"UPPER(Nama) = '{search_nama}'")
                else:
                    where_clauses.append(f"UPPER(Nama) LIKE '%{search_nama}%'")

            # IC filter
            if search_ic:
                where_clauses.append(f"IC LIKE '%{search_ic}%'")

            # Phone filter
            if search_tel:
                where_clauses.append(f"tel1 LIKE '%{search_tel}%'")

            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            # tel1 is right after Nama in the SELECT column list
            query = f"""
                SELECT 
                    IC, 
                    ICLama, 
                    Nama, 
                    tel1, 
                    NoRumah, 
                    NamaLokaliti, 
                    Negeri, 
                    Bangsa, 
                    Alamat1, 
                    Alamat2, 
                    Alamat3, 
                    Poskod, 
                    Bandar
                FROM `mysej-510709.mysej.combined_data`
                {where_sql}
                ORDER BY IC ASC
            """
            
            try:
                df_results = client.query(query).to_dataframe()
                
                # Increment user search statistics
                st.session_state["user_stats"][current_user]["search_count"] += 1
                if current_month_key not in st.session_state["user_stats"][current_user]["monthly_searches"]:
                    st.session_state["user_stats"][current_user]["monthly_searches"][current_month_key] = 0
                st.session_state["user_stats"][current_user]["monthly_searches"][current_month_key] += 1

                st.subheader(f"Search Results ({len(df_results):,} matches found)")
                if not df_results.empty:
                    st.dataframe(df_results, use_container_width=True)
                else:
                    st.info("No records matched your search query.")
            except Exception as e:
                st.error(f"Error executing BigQuery search: {e}")
else:
    st.info("👈 Select your filters in the sidebar and click **Search Database**.")