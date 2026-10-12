import streamlit as st
from google.cloud import bigquery
import base64
import tempfile
import os
import datetime

# ---------------------------------------------------------
# 1. Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Elite Search Engine",
    page_icon="🔍",
    layout="wide"
)

# ---------------------------------------------------------
# 2. Initialize Session State
# ---------------------------------------------------------
if "usage" not in st.session_state:
    st.session_state["usage"] = {}
if "quotas" not in st.session_state:
    st.session_state["quotas"] = {}
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
# 3. BigQuery Client Authentication
# ---------------------------------------------------------
@st.cache_resource
def get_bq_client():
    project_id = "mysej-510709"
    
    if "gcp_service_account" in st.secrets:
        # Load credentials directly from secrets with explicit project ID
        creds_dict = dict(st.secrets["gcp_service_account"])
        return bigquery.Client.from_service_account_info(creds_dict, project=project_id)
    elif "GCP_SERVICE_ACCOUNT_BASE64" in os.environ:
        # Load encoded service account key if set
        encoded = os.environ["GCP_SERVICE_ACCOUNT_BASE64"]
        decoded = base64.b64decode(encoded).decode("utf-8")
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
            f.write(decoded)
            temp_path = f.name
        return bigquery.Client.from_service_account_json(temp_path, project=project_id)
    else:
        # Fallback to standard environment client with explicit project ID
        return bigquery.Client(project=project_id)

# ---------------------------------------------------------
# 4. Sidebar Controls
# ---------------------------------------------------------
st.sidebar.title("Admin Controls")
st.session_state["is_admin"] = st.sidebar.checkbox(
    "Enable Admin Mode", 
    value=st.session_state["is_admin"], 
    key="admin_mode_checkbox"
)

# ---------------------------------------------------------
# 5. Front Page Header & Announcements
# ---------------------------------------------------------
# Simple User Identifier
current_user = st.text_input("Enter Your User ID / Name:", value="Agent_01")

# Office Notification Banner (if configured by admin)
if st.session_state["office_notice"].strip():
    st.markdown(
        f"""
        <div style="background-color: #ff5252; padding: 12px; border-radius: 6px; text-align: center; color: #fff; margin-bottom: 15px; font-size: 16px; font-weight: bold;">
            ⚠️ NOTICE: {st.session_state["office_notice"]}
        </div>
        """,
        unsafe_allow_html=True
    )

# Dynamic Birthday Banner based on current month
current_month = datetime.date.today().month
current_month_birthdays = [
    b["name"] for b in st.session_state["team_birthdays"] 
    if datetime.datetime.strptime(b["dob"], "%Y-%m-%d").month == current_month
]

if current_month_birthdays:
    names_str = ", ".join(current_month_birthdays)
    banner_text = f"🎉 <b>Happy Birthday this month to: {names_str}!</b> Wishing you health, success, and happiness! 🎂"
else:
    banner_text = "🎉 <b>Happy Birthday to all team members celebrating their special day this month!</b> 🎂"

st.markdown(
    f"""
    <div style="background-color: #ffeb3b; padding: 12px; border-radius: 6px; text-align: center; color: #000; margin-bottom: 20px; font-size: 16px;">
        {banner_text}
    </div>
    """,
    unsafe_allow_html=True
)

st.title("🔍 Elite Search Engine")
st.write("Search across your BigQuery database records securely.")

# ---------------------------------------------------------
# 6. Admin Panel Dashboard (Visible when Admin Mode is Enabled)
# ---------------------------------------------------------
if st.session_state["is_admin"]:
    st.subheader("📊 Admin Dashboard & Management")
    
    tab1, tab2, tab3 = st.tabs(["Usage & Logs", "Manage Birthdays", "Office Notice Settings"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.write("### Monthly & Current Search Usage")
            if st.session_state["usage"]:
                usage_data = [{"User": u, "Searches Used": count} for u, count in st.session_state["usage"].items()]
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
        st.write("### Add New Team Member Birthday")
        with st.form("add_birthday_form"):
            new_name = st.text_input("Team Member Name:")
            new_dob = st.date_input("Date of Birth:", value=datetime.date(1990, 1, 1))
            submit_birthday = st.form_submit_button("Add Birthday")
            
            if submit_birthday and new_name:
                formatted_dob = new_dob.strftime("%Y-%m-%d")
                st.session_state["team_birthdays"].append({"name": new_name, "dob": formatted_dob})
                st.success(f"Added birthday for {new_name} successfully!")
                st.rerun()
                
        st.write("Current Team Birthday List:")
        st.dataframe(st.session_state["team_birthdays"], use_container_width=True)
        
    with tab3:
        st.write("### Office Status Notification Settings")
        with st.form("office_notice_form"):
            notice_input = st.text_area(
                "Office Announcement / Closure Notice (Leave blank if open normally):", 
                value=st.session_state["office_notice"]
            )
            submit_notice = st.form_submit_button("Update Notice")
            
            if submit_notice:
                st.session_state["office_notice"] = notice_input
                st.success("Office notification updated!")
                st.rerun()
                
    st.markdown("---")

# ---------------------------------------------------------
# 7. Search Interface & Logic
# ---------------------------------------------------------
# Default Negeri Selection
selected_negeri = st.selectbox(
    "Select or filter by Negeri (State):", 
    [
        "KLANG VALLEY (KUALA LUMPUR & SELANGOR)", "ALL", "SELANGOR", 
        "KUALA LUMPUR", "JOHOR", "PENANG", "PERAK", "MELAKA", 
        "NEGERI SEMBILAN", "PAHANG", "KELANTAN", "TERENGGANU", 
        "KEDAH", "PERLIS", "SABAH", "SARAWAK"
    ]
)

# Default Search Match Type (Exact Match)
match_type = st.radio(
    "Select Search Match Type:", 
    ["Exact Match", "Similar (Partial Match)"], 
    horizontal=True
)

search_query = st.text_input("Enter Name, IC, or Phone to search:")

if search_query:
    # Quota check for non-admin users
    if not st.session_state["is_admin"]:
        if st.session_state["usage"].get(current_user, 0) >= st.session_state["quotas"].get(current_user, 500):
            st.error("You have exceeded your monthly search quota limit. Please contact the administrator.")
            st.stop()
        else:
            st.session_state["usage"][current_user] = st.session_state["usage"].get(current_user, 0) + 1

    # Log search activity
    st.session_state["user_logs"].append({
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "User": current_user,
        "Query": search_query,
        "Match Type": match_type
    })

    safe_query = search_query.replace("'", "\\'")
    
    # Construct SQL Query
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
    
    # Apply Negeri Filter
    if selected_negeri == "KLANG VALLEY (KUALA LUMPUR & SELANGOR)":
        sql_query += f" AND UPPER(negeri) IN ('KUALA LUMPUR', 'SELANGOR')"
    elif selected_negeri != "ALL":
        sql_query += f" AND UPPER(negeri) = '{selected_negeri}'"
        
    sql_query += " LIMIT 100"

    try:
        with st.spinner("Querying BigQuery dataset..."):
            query_job = client.query(sql_query)
            df = query_job.to_dataframe()

            if not df.empty:
                # 1. Convert IC/nokp to string to stop scientific notation formatting
                if 'nokp' in df.columns:
                    df['nokp'] = df['nokp'].astype(str).str.replace(r'\.0$', '', regex=True)

                # 2. Exclude all requested hidden columns
                hidden_columns = [
                    'jantina', 'Jastina', 'Kodlokaliti', 'NamaParlimen', 
                    'NamaDM', 'NameDUN', 'NamaDUN', 'KategoriPemilih', 
                    'name_tel', 'Unnamed__0'
                ]
                available_cols = [col for col in df.columns if col not in hidden_columns]
                
                # 3. Position nokp first, followed by Nama, tel1, and the remaining columns
                front_cols = []
                for col_name in ['nokp', 'Nama', 'tel1']:
                    if col_name in available_cols:
                        front_cols.append(col_name)
                        
                display_cols = front_cols + [col for col in available_cols if col not in front_cols]
                filtered_df = df[display_cols]

                # 4. Sort by IC (nokp) ascending
                if 'nokp' in filtered_df.columns:
                    filtered_df = filtered_df.sort_values(by='nokp', ascending=True)

                st.success(f"Found {len(filtered_df)} matching records.")
                st.dataframe(filtered_df, use_container_width=True)
            else:
                st.info("No matching records found in the database.")
    except Exception as e:
        st.error(f"An error occurred while executing the query: {e}")