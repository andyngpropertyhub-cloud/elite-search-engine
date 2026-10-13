import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd  # <-- ADD THIS IMPORT
import base64
import tempfile
import json
import os
import datetime

# ---------------------------------------------------------
# 1. Page Configuration
# ---------------------------------------------------------
import streamlit as st
import streamlit.components.v1 as components

# MUST be first! Set your desired page title and icon
st.set_page_config(page_title="Elite Search Engine", page_icon="🔍", layout="wide")

# Inject Open Graph Meta Tags for WhatsApp/Social Media
og_meta_tags = """
    <head>
      <!-- Optimized Title & Description -->
      <meta property="og:title" content="Elite Search Engine" />
      <meta property="og:description" content="Fast, reliable search tool for structured datasets with full data accuracy." />
      <meta property="og:type" content="website" />
      <meta property="og:url" content="https://elitesearch.streamlit.app/" />
      
      <!-- *** PASTE YOUR PUBLIC IMAGE URL HERE *** -->
      <meta property="og:image" content="https://raw.githubusercontent.com/andyngpropertyhub-cloud/elite-search-engine/main/preview.jpg" />
      
      <!-- Recommended Image Constraints: 1:1 Aspect Ratio (Square), <300KB -->
    </head>
"""

# Render hidden tags without space
components.html(og_meta_tags, height=0, width=0)

# pull live property news

import feedparser

with st.expander("📰 Latest Malaysia Property News"):
    st.caption("Live updates from Malaysian real estate portals")
    
    # Example RSS feed from a major property portal (e.g., EdgeProp Malaysia)
    rss_url = "https://www.edgeprop.my/rss.xml" # Or standard property news feed
    
    try:
        feed = feedparser.parse(rss_url)
        if feed.entries:
            for entry in feed.entries[:5]: # Show top 5 latest news items
                st.markdown(f"**[{entry.title}]({entry.link})**")
                st.text(f"Published: {entry.published[:16]}")
                st.markdown("---")
        else:
            st.info("No news feeds available at the moment.")
    except Exception as e:
        st.warning("Could not fetch live property news feeds.")
# ---------------------------------------------------------
# 2. Initialize Session State (User Credentials & State)
# ---------------------------------------------------------
if "users" not in st.session_state:
    st.session_state["users"] = {
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

if "quotas" not in st.session_state:
    # Set default 500 searches per user (unlimited for admin)
    st.session_state["quotas"] = {u: (99999 if u == "admin" else 500) for u in st.session_state["users"]}

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "logged_user" not in st.session_state:
    st.session_state["logged_user"] = None
if "usage" not in st.session_state:
    st.session_state["usage"] = {}
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
if "user_logs" not in st.session_state:
    st.session_state["user_logs"] = []
if "office_notice" not in st.session_state:
    st.session_state["office_notice"] = ""

if "team_birthdays" not in st.session_state:
    st.session_state["team_birthdays"] = [
        {"name": "OOI SHUN HOONG (Derrick)", "dob": "1991-01-16"},
        {"name": "HOW KEAT HANG (Eric)", "dob": "1980-01-29"},
        {"name": "YAP YUNG KANG (Kent)", "dob": "1988-02-23"},
        {"name": "YAP SIEW PIN (Daniel)", "dob": "1979-03-07"},
        {"name": "TIEW CHEE HEONG (Rex)", "dob": "1985-03-15"},
        {"name": "NG WAI KEAT (Ted)", "dob": "1987-03-17"},
        {"name": "Lee Keng Ho (Benny)", "dob": "1977-03-11"},
        {"name": "RYAN CHAN PHUEI SUM", "dob": "2000-04-30"},
        {"name": "YOW KOK SENG", "dob": "1989-05-01"},
        {"name": "NG HON KEONG (Andy)", "dob": "1980-05-18"},
        {"name": "YEOW GUAT BEE", "dob": "1965-06-12"},
        {"name": "LO SHENG LOONG (Alex)", "dob": "1994-07-02"},
        {"name": "WONG WING CHOY (Tommy)", "dob": "1981-08-14"},
        {"name": "OOI KOK HING", "dob": "1984-08-31"},
        {"name": "LEONG CHEE CHUNG (Dom)", "dob": "1989-09-08"},
        {"name": "CHIN KOK LEONG (Eddie)", "dob": "1973-09-27"},
        {"name": "TONG WAI LEUNG (Daniel)", "dob": "1988-11-03"},
        {"name": "HOH CHENG YEE", "dob": "1974-11-10"},
        {"name": "SIEW KET TONG (Top Siew)", "dob": "1975-11-24"},
        {"name": "YAP YUNG MEI", "dob": "1984-12-18"}
    ]

# ---------------------------------------------------------
# 3. Login System Interface
# ---------------------------------------------------------
if not st.session_state["authenticated"]:
    st.title("🔒 Login to Elite Search Engine")
    
    with st.form("login_form"):
        username_input = st.text_input("Username:").strip().lower()
        password_input = st.text_input("Password:", type="password")
        submit_button = st.form_submit_button("Login")

        if submit_button:
            users_db = st.session_state["users"]
            if username_input in users_db and users_db[username_input] == password_input:
                st.session_state["authenticated"] = True
                st.session_state["logged_user"] = username_input
                if username_input not in st.session_state["usage"]:
                    st.session_state["usage"][username_input] = 0
                st.success(f"Welcome back, {username_input}!")
                st.rerun()
            else:
                st.error("Invalid Username or Password. Please try again.")
    st.stop()

current_user = st.session_state["logged_user"]
max_quota = st.session_state["quotas"].get(current_user, 500)
user_usage = st.session_state["usage"].get(current_user, 0)


# ---------------------------------------------------------
# 4. BigQuery Client Authentication
# ---------------------------------------------------------
@st.cache_resource
def get_bq_client():
    project_id = "mysej-510709"
    
    # Check for GCP_CREDENTIALS_B64 or GCP_SERVICE_ACCOUNT_BASE64 in Environment
    b64_key = os.environ.get("GCP_CREDENTIALS_B64") or os.environ.get("GCP_SERVICE_ACCOUNT_BASE64")
    
    if b64_key:
        decoded = base64.b64decode(b64_key).decode("utf-8")
        creds_dict = json.loads(decoded)
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        return bigquery.Client(credentials=credentials, project=project_id)
        
    # Option 2: Check Streamlit Secrets (.streamlit/secrets.toml)
    elif "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        return bigquery.Client(credentials=credentials, project=project_id)
        
    else:
        st.error("❌ BigQuery Service Account Credentials NOT found! Please set 'GCP_CREDENTIALS_B64' in environment variables or Streamlit Secrets.")
        st.stop()

try:
    client = get_bq_client()
except Exception as e:
    st.error(f"Failed to initialize BigQuery client: {e}")

# ---------------------------------------------------------
# 5. Sidebar & Logout
# ---------------------------------------------------------
st.sidebar.write(f"👤 Logged in as: **{current_user}**")
st.sidebar.write(f"📊 Usage: **{user_usage} / {max_quota} searches**")

if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.session_state["logged_user"] = None
    st.rerun()

st.sidebar.title("Admin Controls")
st.session_state["is_admin"] = st.sidebar.checkbox(
    "Enable Admin Mode", 
    value=st.session_state["is_admin"], 
    key="admin_mode_checkbox"
)

# ---------------------------------------------------------
# 6. Front Page Header & Announcements
# ---------------------------------------------------------
if st.session_state["office_notice"].strip():
    st.markdown(
        f"""
        <div style="background-color: #ff5252; padding: 12px; border-radius: 6px; text-align: center; color: #fff; margin-bottom: 15px; font-size: 16px; font-weight: bold;">
            ⚠️ NOTICE: {st.session_state["office_notice"]}
        </div>
        """,
        unsafe_allow_html=True
    )

current_month = datetime.date.today().month
current_month_birthdays = [
    b["name"] for b in st.session_state["team_birthdays"] 
    if datetime.datetime.strptime(b["dob"], "%Y-%m-%d").month == current_month
]

if current_month_birthdays:
    names_str = ", ".join(current_month_birthdays)
    banner_text = f"🎉 <b>Happy Birthday this month to: {names_str}!</b> Wishing you health, success, and happiness! 🎂"
else:
    banner_text = "🧧 <b>Heng Ong Huat Ah!</b> Wishing everyone prosperity and great success! 🧧"

st.markdown(
    f"""
    <div style="background-color: #ffeb3b; padding: 12px; border-radius: 6px; text-align: center; color: #000; margin-bottom: 20px; font-size: 16px;">
        {banner_text}
    </div>
    """,
    unsafe_allow_html=True
)

st.title("🔍 Elite Search Engine")
st.write("Search across Malaysia database records securely.")

# ---------------------------------------------------------
# 7. Admin Panel Dashboard & Management
# ---------------------------------------------------------
if st.session_state["is_admin"]:
    st.subheader("📊 Admin Dashboard & Management")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Usage & Logs", "Manage Users & Passwords", "Manage Birthdays", "Office Notice"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.write("### Monthly Search Usage")
            if st.session_state["usage"]:
                usage_data = [
                    {"User": u, "Searches Used": count, "Quota Limit": st.session_state["quotas"].get(u, 500)} 
                    for u, count in st.session_state["usage"].items()
                ]
                st.dataframe(usage_data, use_container_width=True)
                st.write(f"**Total Searches Across All Users:** {sum(st.session_state['usage'].values())}")
            else:
                st.info("No search usage recorded yet.")
                
        with col2:
            st.write("### Recent Activity Logs")
            if st.session_state["user_logs"]:
                st.dataframe(st.session_state["user_logs"][-10:], use_container_width=True)
            else:
                st.info("No activity logs recorded yet.")
                
    with tab2:
        st.write("### Add New User or Change Password")
        
        # Sub-form to Add New User
        with st.form("add_user_form"):
            st.write("#### Add New User")
            new_username = st.text_input("New Username:").strip().lower()
            new_password = st.text_input("New User Password:", type="password")
            new_quota = st.number_input("Monthly Search Quota:", value=500, min_value=1)
            submit_new_user = st.form_submit_button("Create User")
            
            if submit_new_user and new_username and new_password:
                if new_username in st.session_state["users"]:
                    st.error("User already exists!")
                else:
                    st.session_state["users"][new_username] = new_password
                    st.session_state["quotas"][new_username] = new_quota
                    st.success(f"User '{new_username}' created successfully!")
                    st.rerun()

        st.markdown("---")
        
        # Sub-form to Change User Password
        with st.form("change_password_form"):
            st.write("#### Change Existing User Password")
            target_user = st.selectbox("Select User:", list(st.session_state["users"].keys()))
            updated_password = st.text_input("New Password:", type="password")
            submit_change_pw = st.form_submit_button("Update Password")
            
            if submit_change_pw and updated_password:
                st.session_state["users"][target_user] = updated_password
                st.success(f"Password updated successfully for '{target_user}'!")
                st.rerun()

    with tab3:
        st.write("### Add New Team Member Birthday")
        with st.form("add_birthday_form"):
            new_name = st.text_input("Team Member Name (with Title):")
            new_dob = st.date_input("Date of Birth:", value=datetime.date(1990, 1, 1))
            submit_birthday = st.form_submit_button("Add Birthday")
            
            if submit_birthday and new_name:
                formatted_dob = new_dob.strftime("%Y-%m-%d")
                st.session_state["team_birthdays"].append({"name": new_name, "dob": formatted_dob})
                st.success(f"Added birthday for {new_name} successfully!")
                st.rerun()
                
        st.write("Current Team Birthday List:")
        st.dataframe(st.session_state["team_birthdays"], use_container_width=True)
        
    with tab4:
        st.write("### Office Status Notification Settings")
        with st.form("office_notice_form"):
            notice_input = st.text_area(
                "Office Announcement / Closure Notice (Leave blank if open normally):", 
                value=st.session_state["office_notice"]
            )
            submit_notice = st.form_submit_button("Update Notice Banner")
            
            if submit_notice:
                st.session_state["office_notice"] = notice_input
                st.success("Office notification updated!")
                st.rerun()
                
    st.markdown("---")

# ---------------------------------------------------------
# 8. Search Interface & Logic
# ---------------------------------------------------------
selected_negeri = st.selectbox(
    "Select or filter by Negeri (State):", 
    [
        "KLANG VALLEY (KUALA LUMPUR & SELANGOR)", "ALL", "SELANGOR", 
        "KUALA LUMPUR", "JOHOR", "PENANG", "PERAK", "MELAKA", 
        "NEGERI SEMBILAN", "PAHANG", "KELANTAN", "TERENGGANU", 
        "KEDAH", "PERLIS", "SABAH", "SARAWAK"
    ]
)

match_type = st.radio(
    "Select Search Match Type:", 
    ["Exact Match for name and ic", "Similar (Partial Match for phone search exclude 60)"], 
    horizontal=True
)

search_query = st.text_input("Enter Name, IC, or Phone to search:")

if search_query:
    if user_usage >= max_quota and not st.session_state["is_admin"]:
        st.error(f"⛔ You have reached your monthly limit of {max_quota} searches. Please contact the administrator.")
        st.stop()

    st.session_state["usage"][current_user] = user_usage + 1

    st.session_state["user_logs"].append({
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "User": current_user,
        "Query": search_query,
        "Match Type": match_type
    })

    safe_query = search_query.replace("'", "\\'")
    
    if match_type == "Exact Match for name and ic":
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
    
    if selected_negeri == "KLANG VALLEY (KUALA LUMPUR & SELANGOR)":
        sql_query += f" AND UPPER(negeri) IN ('KUALA LUMPUR', 'SELANGOR')"
    elif selected_negeri != "ALL":
        sql_query += f" AND UPPER(negeri) = '{selected_negeri}'"
        
    sql_query += " LIMIT 100"

    try:
        with st.spinner("Querying BigQuery dataset..."):
            query_job = client.query(sql_query)
            
            # Fetch raw rows and manually force nokp, IC, tel1 to raw strings
            raw_rows = []
            columns = []
            
            for row in query_job:
                if not columns:
                    columns = list(row.keys())
                
                row_dict = {}
                for key, value in row.items():
                    # Force ID and phone columns to clean unformatted strings
                    if key in ['nokp', 'IC', 'ICLama', 'tel1'] and value is not None:
                        # Convert float/int representations back to a clean flat string
                        str_val = str(value)
                        if '.' in str_val:
                            str_val = str_val.split('.')[0]
                        if 'E' in str_val or 'e' in str_val:
                            # If scientific notation slipped through, parse it safely
                            try:
                                str_val = f"{int(float(value))}"
                            except:
                                pass
                        row_dict[key] = str_val
                    else:
                        row_dict[key] = "" if value is None else value
                raw_rows.append(row_dict)

            df = pd.DataFrame(raw_rows)

            if not df.empty:
                hidden_columns = [
                    'Jastina', 'Kodlokaliti', 'NamaParlimen', 
                    'NamaDM', 'NameDUN', 'KategoriPemilih', 
                    'name_tel', 'Unnamed__0'
                ]
                available_cols = [col for col in df.columns if col not in hidden_columns]
                
                front_cols = []
                for col_name in ['nokp', 'Nama', 'tel1', 'IC']:
                    if col_name in available_cols:
                        front_cols.append(col_name)
                        
                display_cols = front_cols + [col for col in available_cols if col not in front_cols]
                filtered_df = df[display_cols]

                if 'nokp' in filtered_df.columns:
                    filtered_df = filtered_df.sort_values(by='nokp', ascending=True)

                st.success(f"Found {len(filtered_df)} matching records.")
                st.dataframe(
                    filtered_df, 
                    use_container_width=True,
                    column_config={
                        "nokp": st.column_config.TextColumn("nokp"),
                        "IC": st.column_config.TextColumn("IC"),
                        "tel1": st.column_config.TextColumn("tel1"),
                        "ICLama": st.column_config.TextColumn("ICLama")
                    }
                )
            else:
                st.info("No matching records found in the database.")
    except Exception as e:
        st.error(f"An error occurred while executing the query: {e}")