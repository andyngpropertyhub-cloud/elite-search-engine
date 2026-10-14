import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
import base64
import tempfile
import json
import os
import datetime
import feedparser
import math
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import urllib.parse

# -----------------------------------------------------------------------------
# 1. Page Configuration (MUST BE FIRST STREAMLIT CALL)
# -----------------------------------------------------------------------------
current_year = datetime.datetime.now().year

st.set_page_config(
    page_title="Elite Search Engine | Property Market Utilities",
    page_icon="🏢",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. Initialize Session State
# -----------------------------------------------------------------------------
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
    st.session_state["quotas"] = {u: (99999 if u == "admin" else 500) for u in st.session_state["users"]}

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "logged_user" not in st.session_state:
    st.session_state["logged_user"] = None
if "usage" not in st.session_state:
    st.session_state["usage"] = {u: 0 for u in st.session_state["users"]}
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

# -----------------------------------------------------------------------------
# 3. BigQuery Client Authentication Setup
# -----------------------------------------------------------------------------
@st.cache_resource
def get_bq_client():
    project_id = "mysej-510709"
    b64_key = os.environ.get("GCP_CREDENTIALS_B64") or os.environ.get("GCP_SERVICE_ACCOUNT_BASE64")
    
    if b64_key:
        decoded = base64.b64decode(b64_key).decode("utf-8")
        creds_dict = json.loads(decoded)
        return bigquery.Client(credentials=service_account.Credentials.from_service_account_info(creds_dict), project=project_id)
    elif "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        return bigquery.Client(credentials=service_account.Credentials.from_service_account_info(creds_dict), project=project_id)
    else:
        return None

client = get_bq_client()

# -----------------------------------------------------------------------------
# 4. App Header & Public Office Notice
# -----------------------------------------------------------------------------
st.title("🏢 Elite Property Hub & Search Engine")
st.caption("Real-time Malaysian property market intelligence, legal calculators, statutory scale rates, and RPGT tools.")

if st.session_state["office_notice"].strip():
    st.markdown(
        f"""
        <div style="background-color: #ff5252; padding: 12px; border-radius: 6px; text-align: center; color: #fff; margin-bottom: 15px; font-size: 16px; font-weight: bold;">
            ⚠️ OFFICE NOTICE: {st.session_state["office_notice"]}
        </div>
        """,
        unsafe_allow_html=True
    )

# -----------------------------------------------------------------------------
# 5. Main Navigation
# -----------------------------------------------------------------------------
tab_search, tab_news, tab_mortgage, tab_tenancy, tab_budget, tab_fees, tab_contacts = st.tabs([
    "🔍 Elite Search Engine",
    "📰 Latest Property News", 
    "🏦 Mortgage, RPGT & Upfront Fees", 
    "📜 Tenancy Stamp Duty Calculator",
    "📊 Malaysia Budget Highlights",
    "⚖️ Professional Scale Rates & Legal Quote",
    "📞 Professional Services Directory"
])

# =============================================================================
# TAB 0: ELITE SEARCH ENGINE
# =============================================================================
with tab_search:
    st.header("🔍 Commercial & Dataset Search Interface")

    if not st.session_state["authenticated"]:
        st.warning("🔒 You must log in to access secure database search records.")
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
    else:
        current_user = st.session_state["logged_user"]
        max_quota = st.session_state["quotas"].get(current_user, 500)
        user_usage = st.session_state["usage"].get(current_user, 0)

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

        if st.session_state["is_admin"]:
            with st.expander("📊 Admin Dashboard & Management", expanded=True):
                admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
                    "Usage & Search Logs", 
                    "Manage Users & Quota Limits", 
                    "Manage Birthdays", 
                    "Office Notice Logs"
                ])
                
                with admin_tab1:
                    st.subheader("📈 Search Analytics & Timeline")
                    all_log_users = ["ALL"] + list(st.session_state["users"].keys())
                    selected_analytics_user = st.selectbox("Filter Timeline by User:", all_log_users)
                    
                    filtered_logs = st.session_state["user_logs"]
                    if selected_analytics_user != "ALL":
                        filtered_logs = [log for log in st.session_state["user_logs"] if log.get("User") == selected_analytics_user]
                    
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        total_searches_metric = sum(st.session_state["usage"].values()) if selected_analytics_user == "ALL" else st.session_state["usage"].get(selected_analytics_user, 0)
                        st.metric("Total Searches Recorded", total_searches_metric)
                    with col_m2:
                        st.metric("Active Search Queries in View", len(filtered_logs))
                        
                    st.markdown("---")
                    st.write("### Recent Activity Logs")
                    if filtered_logs:
                        st.dataframe(pd.DataFrame(filtered_logs), use_container_width=True)
                    else:
                        st.info("No activity logs recorded for this selection yet.")

                with admin_tab2:
                    st.subheader("👥 User Account & Search Quota Management")
                    with st.form("adjust_quota_form"):
                        st.write("#### Adjust User Search Quota Limit")
                        target_quota_user = st.selectbox("Select User Account:", list(st.session_state["users"].keys()))
                        current_user_limit = st.session_state["quotas"].get(target_quota_user, 500)
                        new_limit_val = st.number_input("New Monthly Quota Limit:", min_value=1, value=int(current_user_limit))
                        if st.form_submit_button("Update Quota Limit"):
                            st.session_state["quotas"][target_quota_user] = new_limit_val
                            st.success(f"Successfully updated search limit for '{target_quota_user}' to {new_limit_val} searches.")
                            st.rerun()

                    st.markdown("---")
                    with st.form("add_user_form"):
                        st.write("#### Create New User")
                        nu = st.text_input("New Username:").strip().lower()
                        npw = st.text_input("New Password:", type="password")
                        n_quota = st.number_input("Initial Monthly Quota Limit:", value=500)
                        if st.form_submit_button("Create User") and nu and npw:
                            st.session_state["users"][nu] = npw
                            st.session_state["quotas"][nu] = n_quota
                            st.session_state["usage"][nu] = 0
                            st.success(f"User '{nu}' created successfully!")
                            st.rerun()

                with admin_tab3:
                    st.subheader("🎂 Team Birthday Management")
                    with st.form("add_bday"):
                        bname = st.text_input("Team Member Name (with Title):")
                        bdob = st.date_input("Date of Birth:", value=datetime.date(1990, 1, 1))
                        if st.form_submit_button("Add Birthday") and bname:
                            st.session_state["team_birthdays"].append({"name": bname, "dob": bdob.strftime("%Y-%m-%d")})
                            st.success(f"Added birthday for {bname}!")
                            st.rerun()
                            
                    st.markdown("---")
                    if st.session_state["team_birthdays"]:
                        bday_names = [b["name"] for b in st.session_state["team_birthdays"]]
                        selected_bday_to_edit = st.selectbox("Select Team Member to Edit/Remove:", bday_names)
                        current_bday_record = next((b for b in st.session_state["team_birthdays"] if b["name"] == selected_bday_to_edit), None)
                        
                        if current_bday_record:
                            with st.form("edit_bday_form"):
                                edit_name = st.text_input("Edit Name:", value=current_bday_record["name"])
                                edit_dob = st.date_input("Edit DOB:", value=datetime.datetime.strptime(current_bday_record["dob"], "%Y-%m-%d").date())
                                c_col1, c_col2 = st.columns(2)
                                with c_col1:
                                    update_btn = st.form_submit_button("Save Changes")
                                with c_col2:
                                    remove_btn = st.form_submit_button("Remove Birthday")
                                if update_btn:
                                    current_bday_record["name"] = edit_name
                                    current_bday_record["dob"] = edit_dob.strftime("%Y-%m-%d")
                                    st.success("Birthday record updated successfully!")
                                    st.rerun()
                                if remove_btn:
                                    st.session_state["team_birthdays"] = [b for b in st.session_state["team_birthdays"] if b["name"] != selected_bday_to_edit]
                                    st.success("Removed birthday successfully!")
                                    st.rerun()

                with admin_tab4:
                    st.subheader("📢 Office Notice & Announcement History Log")
                    with st.form("notice_f"):
                        not_in = st.text_area("Update Current Active Notice:", value=st.session_state["office_notice"])
                        if st.form_submit_button("Publish Notice"):
                            st.session_state["office_notice"] = not_in
                            st.success("Office notice updated and published live!")
                            st.rerun()

        selected_negeri = st.selectbox(
            "Select or filter by Negeri (State):", 
            ["ALL", "KLANG VALLEY (KUALA LUMPUR & SELANGOR)", "SELANGOR", "KUALA LUMPUR", "JOHOR", "PENANG", "PERAK", "MELAKA", "NEGERI SEMBILAN", "PAHANG", "KELANTAN", "TERENGGANU", "KEDAH", "PERLIS", "SABAH", "SARAWAK"],
            index=0
        )
        
        match_type = st.radio(
            "Select Search Match Type:", 
            ["Exact Match for name and ic", "Similar (Partial Match for phone search exclude 60 and road name)"], 
            horizontal=True
        )
        
        search_query = st.text_input("Enter Name, IC, Address (Jalan name) or Phone to search:")

        if search_query:
            if user_usage >= max_quota and not st.session_state["is_admin"]:
                st.error(f"⛔ Monthly limit of {max_quota} searches reached.")
                st.stop()

            st.session_state["usage"][current_user] = user_usage + 1
            st.session_state["user_logs"].append({
                "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                "User": current_user, 
                "Query": search_query, 
                "Match Type": match_type
            })

            safe_query = search_query.replace("'", "\\'")
            clean_phone_query = safe_query.lstrip('+').replace('60', '', 1) if safe_query.startswith(('60', '+60')) else safe_query

            if match_type == "Exact Match for name and ic":
                sql_query = f"""
                    SELECT * FROM `mysej-510709.mysej.combined_data` 
                    WHERE (LOWER(Nama) = '{safe_query.lower()}' 
                       OR CAST(IC AS STRING) = '{safe_query}' 
                       OR CAST(ICLama AS STRING) = '{safe_query}' 
                       OR LOWER(tel1) = '{safe_query.lower()}')
                """
            else:
                sql_query = f"""
                    SELECT * FROM `mysej-510709.mysej.combined_data` 
                    WHERE (LOWER(Nama) LIKE '%{safe_query.lower()}%' 
                       OR CAST(IC AS STRING) LIKE '%{safe_query.lower()}%' 
                       OR CAST(ICLama AS STRING) LIKE '%{safe_query.lower()}%' 
                       OR LOWER(NamaLokaliti) LIKE '%{safe_query.lower()}%' 
                       OR LOWER(Alamat1) LIKE '%{safe_query.lower()}%' 
                       OR LOWER(Alamat2) LIKE '%{safe_query.lower()}%' 
                       OR LOWER(Alamat3) LIKE '%{safe_query.lower()}%' 
                       OR LOWER(negeri) LIKE '%{safe_query.lower()}%' 
                       OR LOWER(tel1) LIKE '%{clean_phone_query.lower()}%')
                """
            
            if selected_negeri == "KLANG VALLEY (KUALA LUMPUR & SELANGOR)":
                sql_query += " AND UPPER(negeri) IN ('KUALA LUMPUR', 'SELANGOR')"
            elif selected_negeri != "ALL":
                sql_query += f" AND UPPER(negeri) = '{selected_negeri}'"
            
            sql_query += " LIMIT 100"

            if client:
                try:
                    with st.spinner("Querying BigQuery dataset..."):
                        query_job = client.query(sql_query)
                        raw_rows, columns = [], []
                        for row in query_job:
                            if not columns:
                                columns = list(row.keys())
                            row_dict = {}
                            for k, v in row.items():
                                if k in ['nokp', 'IC', 'ICLama', 'tel1', 'Poskod', 'poskod'] and v is not None:
                                    str_val = str(v).split('.')[0]
                                    row_dict[k] = str_val
                                else:
                                    row_dict[k] = "" if v is None else v
                            raw_rows.append(row_dict)

                        df = pd.DataFrame(raw_rows)
                        if not df.empty:
                            # Robust Multi-Column Fallback Age Calculation (Fixes missing Age issue)
                            def derive_age_from_row(row):
                                candidates = [row.get('IC'), row.get('nokp'), row.get('ICLama'), row.get('no_kp')]
                                for ic_val in candidates:
                                    if not ic_val:
                                        continue
                                    ic_str = re.sub(r'\D', '', str(ic_val))
                                    if len(ic_str) >= 6:
                                        try:
                                            yy = int(ic_str[0:2])
                                            mm = int(ic_str[2:4])
                                            dd = int(ic_str[4:6])
                                            if 1 <= mm <= 12 and 1 <= dd <= 31:
                                                curr_yr = datetime.datetime.now().year
                                                century = 2000 if yy <= (curr_yr % 100) else 1900
                                                birth_year = century + yy
                                                birth_date = datetime.date(birth_year, mm, dd)
                                                today = datetime.date.today()
                                                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                                                if 0 <= age <= 120:
                                                    return age
                                        except Exception:
                                            continue
                                return ""

                            df['Age'] = df.apply(derive_age_from_row, axis=1)

                            if 'Bandar' in df.columns:
                                unique_bandar = sorted([str(b) for b in df['Bandar'].dropna().unique() if str(b).strip() != ""])
                                if unique_bandar:
                                    selected_bandar = st.multiselect("📍 Filter by Bandar (Town/City):", unique_bandar, default=[])
                                    if selected_bandar:
                                        df = df[df['Bandar'].astype(str).isin(selected_bandar)]

                            # Explicitly hide NamaDUN along with other backend columns
                            hidden_columns = [
                                'nokp', 'Jastina', 'jantina', 'Jantina', 
                                'NameDUN', 'NamaDun', 'namaDun', 'namadun', 'NamaDUN',
                                'Poskod', 'poskod', 
                                'Bangsa', 'bangsa', 'nama_tel', 
                                'Kodlokaliti', 'NamaParlimen', 'NamaDM', 
                                'KategoriPemilih', 'Unnamed__0'
                            ]
                            available_cols = [col for col in df.columns if col not in hidden_columns]
                            
                            front_cols = []
                            for col_name in ['IC', 'Nama', 'tel1', 'Age', 'NamaLokaliti', 'Alamat2']:
                                if col_name in available_cols:
                                    front_cols.append(col_name)
                                    
                            display_cols = front_cols + [col for col in available_cols if col not in front_cols]
                            filtered_df = df[display_cols]

                            if 'IC' in filtered_df.columns:
                                filtered_df = filtered_df.sort_values(by='IC', ascending=True)

                            st.success(f"Found {len(filtered_df)} matching records.")
                            
                            st.dataframe(
                                filtered_df, 
                                use_container_width=True,
                                column_config={
                                    "IC": st.column_config.TextColumn("IC", width="medium"),
                                    "tel1": st.column_config.TextColumn("tel1", width="medium")
                                }
                            )
                        else:
                            st.info("No matching records found in the database.")
                except Exception as e:
                    st.error(f"Query Error: {e}")
            else:
                st.error("BigQuery client is offline. Verify your GCP credentials.")


# =============================================================================
# TAB 1: LIVE MALAYSIA PROPERTY NEWS (IMPROVED RSS IMAGE PARSING)
# =============================================================================
with tab_news:
    st.header("📰 Live Malaysian Property News & Insights")
    NEWS_FEED_URLS = [
        "https://news.google.com/rss/search?q=property+malaysia+real+estate&hl=en-MY&gl=MY&ceid=MY:en",
        "https://theedgemalaysia.com/rss/property",
        "https://www.starproperty.my/rss.xml"
    ]

    @st.cache_data(ttl=1800)
    def fetch_property_news():
        for url in NEWS_FEED_URLS:
            try:
                feed = feedparser.parse(url)
                if feed.entries:
                    return feed.entries
            except Exception:
                continue
        return []

    entries = fetch_property_news()
    if entries:
        for entry in entries[:6]:
            col_img, col_text = st.columns([1, 2.5])
            
            image_url = None
            if hasattr(entry, 'media_content') and entry.media_content:
                image_url = entry.media_content[0].get('url')
            elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                image_url = entry.media_thumbnail[0].get('url')
            elif hasattr(entry, 'enclosures') and entry.enclosures:
                for enc in entry.enclosures:
                    if 'image' in enc.get('type', ''):
                        image_url = enc.get('href')
                        break
            
            if not image_url and hasattr(entry, 'summary'):
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', entry.summary, re.IGNORECASE)
                if img_match:
                    image_url = img_match.group(1)

            with col_img:
                if image_url:
                    try:
                        st.image(image_url, use_column_width=True)
                    except Exception:
                        st.info("🖼️ Property News")
                else:
                    st.info("🖼️ Property News")

            with col_text:
                st.markdown(f"### [{entry.title}]({entry.link})")
                st.caption(f"🗓️ Published: {entry.get('published', entry.get('updated', 'Recent'))[:16]}")
                summary = entry.get('summary', '')
                if summary:
                    clean_summary = re.sub('<[^<]+?>', '', summary)[:180] + "..."
                    st.write(clean_summary)

            st.markdown("---")
    else:
        st.info("Live news feeds are currently updating. Please check back shortly.")


# =============================================================================
# TAB 2: MORTGAGE, RPGT & UPFRONT FEES CALCULATOR
# =============================================================================
with tab_mortgage:
    st.header("🏦 Mortgage, RPGT & Upfront Fees Calculator")
    
    calc_sub_tab1, calc_sub_tab2 = st.tabs(["🏡 Mortgage & Upfront Costs", "🏷️ RPGT (Real Property Gains Tax) Calculator"])
    
    with calc_sub_tab1:
        @st.cache_data(ttl=86400)
        def get_daily_bank_rates():
            return {
                "Maybank": {"Residential": 3.85, "Commercial": 4.50},
                "Public Bank": {"Residential": 3.90, "Commercial": 4.60},
                "CIMB Bank": {"Residential": 3.88, "Commercial": 4.55},
                "Hong Leong Bank": {"Residential": 3.92, "Commercial": 4.65},
                "RHB Bank": {"Residential": 3.89, "Commercial": 4.55},
                "AmBank": {"Residential": 3.95, "Commercial": 4.70}
            }
        bank_rates_data = get_daily_bank_rates()

        col1, col2 = st.columns(2)
        with col1:
            prop_cat = st.radio("Property Category", ["Residential", "Commercial"], horizontal=True)
            financing_scheme = st.selectbox("Financing Scheme", ["Standard Commercial Bank", "LPPSA (Government Servant)", "SJKP (Housing Credit Guarantee)"])
            selected_bank = st.selectbox("Select Bank Profile", list(bank_rates_data.keys()))
            default_rate = float(bank_rates_data[selected_bank][prop_cat])

            prop_price = st.number_input("Property Purchase Price (RM)", min_value=50000, value=600000, step=50000)
            is_first_home = st.checkbox("First-Time Homebuyer (100% MOT & Loan Stamp Duty Exemption up to RM500k)", value=False)
            
            default_mof = 100.0 if financing_scheme in ["LPPSA (Government Servant)", "SJKP (Housing Credit Guarantee)"] else (90 if prop_cat == "Residential" else 85)
            max_mof_limit = 100.0 if financing_scheme in ["LPPSA (Government Servant)", "SJKP (Housing Credit Guarantee)"] else 90.0
            
            margin_finance = st.slider("Margin of Finance (%)", min_value=10.0, max_value=max_mof_limit, value=float(default_mof), step=1.0)
            
            loan_amt = prop_price * (margin_finance / 100.0)
            downpayment = prop_price - loan_amt
            interest_rate = st.number_input("Interest Rate (% p.a.)", min_value=1.0, value=default_rate, step=0.05)
            loan_tenure = st.slider("Loan Tenure (Years)", min_value=5, max_value=35, value=30, step=1)

        def calc_legal_fee(price):
            return max(500, price * 0.0125) if price <= 500000 else (500000 * 0.0125) + ((price - 500000) * 0.01)

        def calc_mot_stamp_duty(price):
            if price <= 100000: return price * 0.01
            elif price <= 500000: return 1000 + (price - 100000) * 0.02
            elif price <= 1000000: return 9000 + (price - 500000) * 0.03
            else: return 24000 + (price - 1000000) * 0.04

        spa_legal = calc_legal_fee(prop_price)
        loan_legal = calc_legal_fee(loan_amt)
        
        if is_first_home and prop_price <= 500000:
            mot_sd = 0.0
            loan_sd = 0.0
        else:
            mot_sd = calc_mot_stamp_duty(prop_price)
            loan_sd = loan_amt * 0.005

        sst_disb = (spa_legal + loan_legal) * 0.08 + 2000
        total_legal_and_stamp = spa_legal + loan_legal + mot_sd + loan_sd + sst_disb
        total_upfront_cash = max(0.0, downpayment + total_legal_and_stamp)
        
        monthly_i = (interest_rate / 100.0) / 12.0
        total_months = loan_tenure * 12
        m_pay = loan_amt * (monthly_i * (1 + monthly_i)**total_months) / ((1 + monthly_i)**total_months - 1) if monthly_i > 0 else loan_amt / total_months

        with col2:
            st.metric("Estimated Monthly Installment", f"RM {m_pay:,.2f}")
            st.metric("Total Upfront Cash Needed", f"RM {total_upfront_cash:,.2f}")
            
            st.markdown("### 📋 Upfront Payment Breakdown")
            cost_table = [
                {"Cost Item": "Downpayment", "Amount (RM)": f"RM {downpayment:,.2f}"},
                {"Cost Item": "SPA Legal Fee (SRO Scale)", "Amount (RM)": f"RM {spa_legal:,.2f}"},
                {"Cost Item": "Loan Agreement Legal Fee", "Amount (RM)": f"RM {loan_legal:,.2f}"},
                {"Cost Item": "MOT Stamp Duty (Transfer)", "Amount (RM)": f"RM {mot_sd:,.2f}"},
                {"Cost Item": "Loan Agreement Stamp Duty (0.5%)", "Amount (RM)": f"RM {loan_sd:,.2f}"},
                {"Cost Item": "SST (8%) & Disbursements", "Amount (RM)": f"RM {sst_disb:,.2f}"},
                {"Cost Item": "Total Upfront Cash Required", "Amount (RM)": f"RM {total_upfront_cash:,.2f}"}
            ]
            st.table(cost_table)
            
            # Export & WhatsApp Sharing including ALL loan info & complete upfront breakdown
            st.markdown("### 📤 Share Mortgage Breakdown")
            
            full_share_msg = (
                f"*Elite Property Financing Assessment*\n"
                f"----------------------------------------\n"
                f"• Property Price: RM {prop_price:,.2f}\n"
                f"• Bank Profile: {selected_bank}\n"
                f"• Financing Scheme: {financing_scheme}\n"
                f"• Interest Rate: {interest_rate:.2f}% p.a.\n"
                f"• Margin of Finance: {margin_finance:.1f}%\n"
                f"• Loan Tenure: {loan_tenure} Years\n"
                f"• Loan Amount: RM {loan_amt:,.2f}\n"
                f"----------------------------------------\n"
                f"*ESTIMATED MONTHLY INSTALLMENT:* RM {m_pay:,.2f}\n"
                f"*TOTAL UPFRONT CASH NEEDED:* RM {total_upfront_cash:,.2f}\n\n"
                f"*UPFRONT COST BREAKDOWN:*\n"
                f"- Downpayment: RM {downpayment:,.2f}\n"
                f"- SPA Legal Fee: RM {spa_legal:,.2f}\n"
                f"- Loan Legal Fee: RM {loan_legal:,.2f}\n"
                f"- MOT Stamp Duty: RM {mot_sd:,.2f}\n"
                f"- Loan Stamp Duty: RM {loan_sd:,.2f}\n"
                f"- SST (8%) & Disbursements: RM {sst_disb:,.2f}\n"
                f"----------------------------------------\n"
                f"*GRAND TOTAL REQUIRED:* RM {total_upfront_cash:,.2f}"
            )
            
            import urllib.parse
            encoded_msg = urllib.parse.quote(full_share_msg)
            wa_mortgage_url = f"https://wa.me/?text={encoded_msg}"
            
            st.markdown(f'<a href="{wa_mortgage_url}" target="_blank"><button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:4px; font-weight:bold; cursor:pointer;">💬 Share Complete Assessment on WhatsApp</button></a>', unsafe_allow_html=True)

    with calc_sub_tab2:
        st.subheader("🏷️ Real Property Gains Tax (RPGT) Calculator")
        
        r_col1, r_col2 = st.columns(2)
        with r_col1:
            acq_price = st.number_input("Acquisition Price (RM)", min_value=10000, value=500000, step=10000)
            disp_price = st.number_input("Disposal Selling Price (RM)", min_value=10000, value=750000, step=10000)
            
            # Acquisition Month/Year Inputs
            acq_col_m, acq_col_y = st.columns(2)
            with acq_col_m:
                acq_month = st.selectbox("Acquisition Month", list(range(1, 13)), index=0)
            with acq_col_y:
                acq_year = st.number_input("Acquisition Year", min_value=1970, max_value=current_year, value=2021)
                
            is_over_5_years = st.checkbox("Property holding period is explicitly over 5 years", value=((current_year - acq_year) >= 5))
            
            # Auto-calculate agent fees based on selection rate
            agent_fee_rate = st.slider("Select Real Estate Agent Commission Rate (%)", min_value=0.0, max_value=3.0, value=3.0, step=0.5)
            auto_agent_fee = disp_price * (agent_fee_rate / 100.0)
            st.info(f"Auto-calculated Agent Fee ({agent_fee_rate}%): RM {auto_agent_fee:,.2f}")
            
            other_incidental_costs = st.number_input("Other Incidental Costs (Legal, Stamp Duty, Renovation) (RM)", min_value=0, value=15000, step=1000)
            total_incidental = auto_agent_fee + other_incidental_costs
            
            disposer_type = st.selectbox("Disposer Category", ["Malaysian Citizen / PR", "Company", "Foreigner (Non-Citizen / Non-PR)"])

        net_gain = max(0.0, disp_price - acq_price - total_incidental)
        holding_years = 6 if is_over_5_years else max(1, current_year - acq_year)
        
        # RPGT Tax Scale Rates
        if disposer_type == "Foreigner (Non-Citizen / Non-PR)":
            rpgt_rate = 10.0 if holding_years > 5 else 30.0
        elif disposer_type == "Company":
            if holding_years <= 3: rpgt_rate = 30.0
            elif holding_years == 4: rpgt_rate = 20.0
            elif holding_years == 5: rpgt_rate = 15.0
            else: rpgt_rate = 10.0
        else: # Citizen / PR
            if holding_years <= 3: rpgt_rate = 30.0
            elif holding_years == 4: rpgt_rate = 20.0
            elif holding_years == 5: rpgt_rate = 15.0
            else: rpgt_rate = 0.0

        rpgt_payable = net_gain * (rpgt_rate / 100.0)

        with r_col2:
            st.metric("Net Realized Capital Gain", f"RM {net_gain:,.2f}")
            st.metric("Applicable RPGT Tax Rate", f"{rpgt_rate:.1f}%")
            st.metric("Total RPGT Tax Liability", f"RM {rpgt_payable:,.2f}")
            
            rpgt_summary_msg = f"""*RPGT Calculation Summary*
----------------------------------------
• Acquisition: {acq_month}/{acq_year} (Price: RM {acq_price:,.2f})
• Disposal Price: RM {disp_price:,.2f}
• Agent Commission ({agent_fee_rate}%): RM {auto_agent_fee:,.2f}
• Other Deductible Expenses: RM {other_incidental_costs:,.2f}
• Category: {disposer_type}
----------------------------------------
*Net Capital Gain:* RM {net_gain:,.2f}
*Applicable RPGT Rate:* {rpgt_rate:.1f}%
*RPGT TAX PAYABLE:* RM {rpgt_payable:,.2f}
"""
            wa_rpgt_url = f"https://wa.me/?text={rpgt_summary_msg.replace(' ', '%20').replace('\n', '%0A')}"
            st.markdown(f'<a href="{wa_rpgt_url}" target="_blank"><button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:4px; font-weight:bold; cursor:pointer;">💬 Share RPGT Summary on WhatsApp</button></a>', unsafe_allow_html=True)


# =============================================================================
# TAB 3: TENANCY STAMP DUTY CALCULATOR (DUPLICATE COPY & LATE PENALTY INFO)
# =============================================================================
with tab_tenancy:
    st.header("📜 Tenancy Agreement Stamp Duty Calculator")
    
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        m_rent = st.number_input("Monthly Rental Amount (RM)", min_value=100, value=2500, step=100)
        lease_term = st.selectbox("Lease Duration", ["1 Year or less", "1 to 3 Years", "3 to 5 Years", "Above 5 Years"])
        duplicate_copies = st.number_input("Number of Duplicate Copies (RM 10 per copy)", min_value=0, value=1, step=1)
        
        annual_r = m_rent * 12
        units = math.ceil(annual_r / 250)
        rate = 1.0 if "1 Year" in lease_term else (3.0 if "1 to 3" in lease_term else (5.0 if "3 to 5" in lease_term else 7.0))
        
        original_stamp_duty = max(10.0, units * rate)
        duplicate_cost = duplicate_copies * 10.0
        total_tenancy_duty = original_stamp_duty + duplicate_cost

    with t_col2:
        st.metric("Original Stamp Duty Fee", f"RM {original_stamp_duty:,.2f}")
        st.metric("Duplicate Copies Fee", f"RM {duplicate_cost:,.2f}")
        st.metric("Total LHDN Payment Required", f"RM {total_tenancy_duty:,.2f}")

    st.markdown("---")
    st.markdown("""
    ### ⚠️ LHDN Late Stamping Penalty Reference
    Tenancy agreements must be submitted for stamping within **30 days** of execution (or within 30 days of arrival in Malaysia if executed abroad).
    
    * **Stamped within 3 months late:** **RM 25.00** or **5%** of the deficient duty (whichever is higher).
    * **Stamped between 3 to 6 months late:** **RM 50.00** or **10%** of the deficient duty (whichever is higher).
    * **Stamped after 6 months late:** **RM 100.00** or **20%** of the deficient duty (whichever is higher).
    """)


# =============================================================================
# TAB 4: MALAYSIA BUDGET HIGHLIGHTS (MULTI-YEAR SELECTOR)
# =============================================================================
with tab_budget:
    st.header("📊 Malaysia Budget Real Estate & Property Policy Archive")
    
    selected_budget_year = st.selectbox("Select Malaysia Budget Year:", ["2027", "2026", "2025", "2024"], index=0)
    
    if selected_budget_year == "2027":
        st.markdown("""
        ### 🇲🇾 Malaysia Budget 2027 Key Property Highlights
        * **First-Time Homebuyer Incentives:** Continued 100% Stamp Duty Exemption on MOT and Loan Agreements for homes priced **up to RM500,000**.
        * **SJKP Housing Guarantee Scheme:** Expanded government guarantee limit up to **RM20 Billion** for gig-economy professionals and self-employed buyers.
        * **RPGT Policies:** Maintained 0% RPGT for individual citizens disposing of residential homes held for over 5 years.
        * **Urban Redevelopment:** Tax relief for commercial-to-residential adaptive reuse projects in urban city centres.
        """)
    elif selected_budget_year == "2026":
        st.markdown("""
        ### 🇲🇾 Malaysia Budget 2026 Summary
        * Full MOT stamp duty exemptions for residential property under RM500k.
        * Expanded SJKP liquidity facilities up to RM10 Billion.
        """)
    else:
        st.markdown(f"### 🇲🇾 Malaysia Budget {selected_budget_year} Highlights\nStandard housing subsidy schemes and stamp duty exemptions applied.")


# =============================================================================
# TAB 5: STATUTORY SCALE RATES & LEGAL QUOTATION GENERATOR (SRO 2023)
# =============================================================================
with tab_fees:
    st.header("⚖️ Official Scale Rates & Legal Quotation Engine")
    
    f_sub1, f_sub2 = st.tabs(["📜 Legal & Conveyancing Quotation Generator (SRO 2023)", "🏢 Statutory Fee Scales (BOVAEP & Valuers)"])
    
    with f_sub1:
        st.subheader("📝 Complete SPA & Loan Legal Fee Quotation Generator")
        
        q_col1, q_col2 = st.columns(2)
        with q_col1:
            q_price = st.number_input("Property Sale Price (RM)", min_value=100000, value=600000, step=50000)
            q_loan = st.number_input("Loan Financing Amount (RM)", min_value=0, value=540000, step=50000)
            
            # Interactive Property Parameters
            prop_tenure = st.selectbox("Property Tenure", ["Freehold", "Leasehold"])
            prop_encumbrance = st.selectbox("Encumbrance Status", ["Charged (With Bank Encumbrance / Redemption needed)", "Free from Encumbrances"])
            prop_title_type = st.selectbox("Property Title Type", ["Individual Title", "Strata Title", "Master Title (Under Developer)"])
            
            # SRO 2023 Legal Scale Fee Calculation
            def calc_sro_2023(price):
                if price <= 500000:
                    return max(500, price * 0.0125)
                elif price <= 7500000:
                    return 6250 + ((price - 500000) * 0.01)
                else:
                    return 76250 + ((price - 7500000) * 0.005)

            spa_legal_q = calc_sro_2023(q_price)
            loan_legal_q = calc_sro_2023(q_loan) if q_loan > 0 else 0.0
            
            def calc_mot_q(price):
                if price <= 100000: return price * 0.01
                elif price <= 500000: return 1000 + (price - 100000) * 0.02
                elif price <= 1000000: return 9000 + (price - 500000) * 0.03
                else: return 24000 + (price - 1000000) * 0.04

            mot_sd_q = calc_mot_q(q_price)
            loan_sd_q = q_loan * 0.005
            
            # Additional Charges based on Title & Tenure Selection
            leasehold_consent_fee = 500.0 if prop_tenure == "Leasehold" else 0.0
            discharge_charge_fee = 400.0 if "Charged" in prop_encumbrance else 0.0
            master_title_fee = 350.0 if prop_title_type == "Master Title (Under Developer)" else 0.0
            
            # Standard Disbursements & RPGT Retention Calculation
            land_search = 150.0
            bankruptcy_search = 100.0
            adjudication_ckht = 200.0  # LHDN Adjudication & CKHT Filing
            statutory_decl = 100.0
            misc_disbursements = 1200.0  # Printing, Courier & Travelling
            
            sst_8_percent = (spa_legal_q + loan_legal_q + leasehold_consent_fee + discharge_charge_fee) * 0.08
            rpgt_retention_3pct = q_price * 0.03  # Statutory 3% RPGT Retention withheld by buyer's solicitor
            
            grand_total_legal = (
                spa_legal_q + loan_legal_q + mot_sd_q + loan_sd_q + 
                leasehold_consent_fee + discharge_charge_fee + master_title_fee +
                land_search + bankruptcy_search + adjudication_ckht + 
                statutory_decl + misc_disbursements + sst_8_percent
            )

        with q_col2:
            st.markdown("### Itemized Quotation Breakdown")
            q_data = [
                {"Item Description": "SPA Scale Legal Fee (SRO 2023)", "Amount (RM)": f"RM {spa_legal_q:,.2f}"},
                {"Item Description": "Loan Agreement Legal Fee (SRO 2023)", "Amount (RM)": f"RM {loan_legal_q:,.2f}"},
                {"Item Description": "MOT / Transfer Stamp Duty", "Amount (RM)": f"RM {mot_sd_q:,.2f}"},
                {"Item Description": "Loan Agreement Stamp Duty", "Amount (RM)": f"RM {loan_sd_q:,.2f}"},
                {"Item Description": "Leasehold Consent Legal Charges", "Amount (RM)": f"RM {leasehold_consent_fee:,.2f}"},
                {"Item Description": "Discharge / Redemption Legal Work", "Amount (RM)": f"RM {discharge_charge_fee:,.2f}"},
                {"Item Description": "Developer Consent / Master Title Fee", "Amount (RM)": f"RM {master_title_fee:,.2f}"},
                {"Item Description": "Land & Title Search Fees", "Amount (RM)": f"RM {land_search:,.2f}"},
                {"Item Description": "Insolvency / Bankruptcy Searches", "Amount (RM)": f"RM {bankruptcy_search:,.2f}"},
                {"Item Description": "CKHT & Adjudication Stamping Fees", "Amount (RM)": f"RM {adjudication_ckht:,.2f}"},
                {"Item Description": "Statutory Declarations & Affirmations", "Amount (RM)": f"RM {statutory_decl:,.2f}"},
                {"Item Description": "Miscellaneous Printing, Courier & Travelling", "Amount (RM)": f"RM {misc_disbursements:,.2f}"},
                {"Item Description": "SST (8% Service Tax on Legal Fees)", "Amount (RM)": f"RM {sst_8_percent:,.2f}"},
                {"Item Description": "ESTIMATED TOTAL LEGAL COST", "Amount (RM)": f"RM {grand_total_legal:,.2f}"}
            ]
            st.table(q_data)
            
            st.info(f"💡 **Statutory 3% RPGT Retention Sum (Withheld by Buyer's Solicitor):** RM {rpgt_retention_3pct:,.2f}")
            
            st.caption("📌 *Remark: This quotation is an estimated guideline based on standard SRO 2023 scale rates. Actual legal fees and disbursements may vary across different legal firms.*")
            
            # WhatsApp Sharing Code
            import urllib.parse
            
            quote_wa_msg = f"""*ESTIMATED LEGAL & CONVEYANCING QUOTATION*
----------------------------------------
• Property Price: RM {q_price:,.2f}
• Loan Amount: RM {q_loan:,.2f}
• Tenure: {prop_tenure}
• Encumbrance: {prop_encumbrance}
• Title Type: {prop_title_type}
----------------------------------------
*LEGAL & STAMP DUTY BREAKDOWN:*
- SPA Legal Fee: RM {spa_legal_q:,.2f}
- Loan Legal Fee: RM {loan_legal_q:,.2f}
- MOT Stamp Duty: RM {mot_sd_q:,.2f}
- Loan Stamp Duty: RM {loan_sd_q:,.2f}
- Consent & Discharge Fees: RM {leasehold_consent_fee + discharge_charge_fee + master_title_fee:,.2f}
- Searches & CKHT Stamping: RM {land_search + bankruptcy_search + adjudication_ckht:,.2f}
- SST (8%): RM {sst_8_percent:,.2f}
----------------------------------------
*ESTIMATED TOTAL LEGAL FEES:* RM {grand_total_legal:,.2f}
*3% RPGT RETENTION WITHHELD:* RM {rpgt_retention_3pct:,.2f}

_Remark: This is an estimated cost and may vary depending on the selected law firm._"""

            encoded_quote_msg = urllib.parse.quote(quote_wa_msg)
            wa_quote_url = f"https://wa.me/?text={encoded_quote_msg}"
            st.markdown(f'<a href="{wa_quote_url}" target="_blank"><button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:4px; font-weight:bold; cursor:pointer;">💬 Share Legal Quotation on WhatsApp</button></a>', unsafe_allow_html=True)

    with f_sub2:
        st.subheader("Official BOVAEP Fee Scale (LPEPH Seventh Schedule)")
        st.markdown("""
        *Source: Official Board of Valuers, Appraisers, Estate Agents and Property Managers (lpeph.gov.my/fees)*
        
        #### 1. Estate Agency Scale Fees (Sales & Purchases)
        * Maximum Cap: **3.0%** of property transacted price.
        * Minimum Fee: **RM 1,000** per property.
        
        #### 2. Lettings & Tenancies Scale Fees
        * Tenancies up to 3 years: **Up to 1.25 months gross rent**
        * Exceeding 3 years up to 4 years: **Up to 1.50 months gross rent**
        * Exceeding 4 years up to 5 years: **Up to 1.75 months gross rent**
        * Minimum Fee: **1 month gross rent**
        """)


# =============================================================================
# TAB 6: PROFESSIONAL SERVICES DIRECTORY
# =============================================================================
with tab_contacts:
    st.header("📞 Professional Property Services Directory")
    services = [
        ("⚡ Utility Application (TNB & Syabas)", "Rex", "+60163600369", "60163600369", "Hello Rex, I would like to inquire about utility application services."),
        ("📑 LHDN Stamping Service", "Rex", "+60163600369", "60163600369", "Hello Rex, I need assistance with document stamping services."),
        ("📐 Property Valuation Service", "Tony Chin", "+60123718228", "60123718228", "Hello Tony, I would like to request a property valuation check."),
        ("💳 Mortgage & Loan Consultant", "Ms. Jovell Khor", "+60162725908", "60162725908", "Hello Ms. Jovell, I would like to consult on loan eligibility."),
        ("🔨 Renovation, Plumbing & Repairs", "Tonni Yu", "+60129108392", "60129108392", "Hello Tonni, I am looking for property renovation and repair services.")
    ]
    for s_name, contact, phone, clean_p, msg in services:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader(s_name)
            st.write(f"**Contact:** {contact} ({phone})")
        with c2:
            st.link_button(f"💬 WhatsApp {contact}", f"https://wa.me/{clean_p}?text={msg.replace(' ', '%20')}", use_container_width=True)
        st.markdown("---")