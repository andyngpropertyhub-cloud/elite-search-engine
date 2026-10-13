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

# -----------------------------------------------------------------------------
# 1. Page Configuration (MUST BE FIRST STREAMLIT CALL)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Elite Search Engine | Property Market Utilities",
    page_icon="🏢",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. Initialize Session State (User Credentials & State)
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

# -----------------------------------------------------------------------------
# 3. Login System Gate
# -----------------------------------------------------------------------------
if not st.session_state["authenticated"]:
    st.title("🔒 Login to Elite Search Engine & Property Hub")
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

# -----------------------------------------------------------------------------
# 4. BigQuery Client Authentication Setup
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
        st.error("❌ BigQuery Service Account Credentials NOT found!")
        st.stop()

try:
    client = get_bq_client()
except Exception as e:
    client = None

# -----------------------------------------------------------------------------
# 5. Sidebar Controls & Logout
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# 6. Main App Header & Banners
# -----------------------------------------------------------------------------
st.title("🏢 Elite Property Hub & Search Engine")
st.caption("Real-time Malaysian property market intelligence, calculators, legal tools, and directory.")

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

banner_text = f"🎉 <b>Happy Birthday this month to: {', '.join(current_month_birthdays)}!</b>" if current_month_birthdays else "🧧 <b>Heng Ong Huat Ah!</b> Wishing everyone prosperity and great success! 🧧"

st.markdown(
    f"""
    <div style="background-color: #ffeb3b; padding: 12px; border-radius: 6px; text-align: center; color: #000; margin-bottom: 20px; font-size: 16px;">
        {banner_text}
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# 7. Main Navigation (6 Tabs View)
# -----------------------------------------------------------------------------
tab_search, tab_news, tab_mortgage, tab_tenancy, tab_budget, tab_contacts = st.tabs([
    "🔍 Elite Search Engine",
    "📰 Latest Property News", 
    "🏦 Mortgage, Legal Fees & Stamp Duty", 
    "📜 Tenancy Stamp Duty Calculator",
    "📊 Malaysia Budget Highlights",
    "📞 Professional Services Directory"
])

# =============================================================================
# TAB 0: ELITE SEARCH ENGINE (BIGQUERY INTERFACE)
# =============================================================================
with tab_search:
    st.header("🔍 Commercial & Dataset Search Interface")
    
    if st.session_state["is_admin"]:
        with st.expander("📊 Admin Dashboard & Management"):
            admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs(["Usage & Logs", "Manage Users", "Manage Birthdays", "Office Notice"])
            with admin_tab1:
                if st.session_state["usage"]:
                    st.dataframe([{"User": u, "Searches Used": c, "Quota": st.session_state["quotas"].get(u, 500)} for u, c in st.session_state["usage"].items()], use_container_width=True)
                if st.session_state["user_logs"]:
                    st.dataframe(st.session_state["user_logs"][-10:], use_container_width=True)
            with admin_tab2:
                with st.form("add_user_form"):
                    nu = st.text_input("New Username:").strip().lower()
                    npw = st.text_input("New Password:", type="password")
                    if st.form_submit_button("Create User") and nu and npw:
                        st.session_state["users"][nu] = npw
                        st.session_state["quotas"][nu] = 500
                        st.success(f"User {nu} created!")
                        st.rerun()
            with admin_tab3:
                with st.form("add_bday"):
                    bname = st.text_input("Name:")
                    bdob = st.date_input("DOB:")
                    if st.form_submit_button("Add") and bname:
                        st.session_state["team_birthdays"].append({"name": bname, "dob": bdob.strftime("%Y-%m-%d")})
                        st.rerun()
            with admin_tab4:
                with st.form("notice_f"):
                    not_in = st.text_area("Notice:", value=st.session_state["office_notice"])
                    if st.form_submit_button("Update"):
                        st.session_state["office_notice"] = not_in
                        st.rerun()

    selected_negeri = st.selectbox(
        "Select or filter by Negeri (State):", 
        ["KLANG VALLEY (KUALA LUMPUR & SELANGOR)", "ALL", "SELANGOR", "KUALA LUMPUR", "JOHOR", "PENANG", "PERAK", "MELAKA", "NEGERI SEMBILAN", "PAHANG", "KELANTAN", "TERENGGANU", "KEDAH", "PERLIS", "SABAH", "SARAWAK"]
    )
    match_type = st.radio("Select Search Match Type:", ["Exact Match for name and ic", "Similar (Partial Match for phone search exclude 60)"], horizontal=True)
    search_query = st.text_input("Enter Name, IC, or Phone to search:")

    if search_query:
        if user_usage >= max_quota and not st.session_state["is_admin"]:
            st.error(f"⛔ Monthly limit of {max_quota} searches reached.")
            st.stop()

        st.session_state["usage"][current_user] = user_usage + 1
        st.session_state["user_logs"].append({"Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "User": current_user, "Query": search_query, "Match Type": match_type})

        safe_query = search_query.replace("'", "\\'")
        if match_type == "Exact Match for name and ic":
            sql_query = f"SELECT * FROM `mysej-510709.mysej.combined_data` WHERE (LOWER(Nama) = '{safe_query.lower()}' OR CAST(nokp AS STRING) = '{safe_query}' OR LOWER(tel1) = '{safe_query.lower()}')"
        else:
            sql_query = f"SELECT * FROM `mysej-510709.mysej.combined_data` WHERE (LOWER(Nama) LIKE '%{safe_query.lower()}%' OR CAST(nokp AS STRING) LIKE '%{safe_query.lower()}%' OR LOWER(tel1) LIKE '%{safe_query.lower()}%')"
        
        if selected_negeri == "KLANG VALLEY (KUALA LUMPUR & SELANGOR)":
            sql_query += " AND UPPER(negeri) IN ('KUALA LUMPUR', 'SELANGOR')"
        elif selected_negeri != "ALL":
            sql_query += f" AND UPPER(negeri) = '{selected_negeri}'"
        sql_query += " LIMIT 100"

        try:
            with st.spinner("Querying BigQuery..."):
                query_job = client.query(sql_query)
                raw_rows, columns = [], []
                for row in query_job:
                    if not columns:
                        columns = list(row.keys())
                    row_dict = {}
                    for k, v in row.items():
                        if k in ['nokp', 'IC', 'ICLama', 'tel1'] and v is not None:
                            str_val = str(v).split('.')[0]
                            row_dict[k] = str_val
                        else:
                            row_dict[k] = "" if v is None else v
                    raw_rows.append(row_dict)

                df = pd.DataFrame(raw_rows)
                if not df.empty:
                    st.success(f"Found {len(df)} records.")
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No records found.")
        except Exception as e:
            st.error(f"Query Error: {e}")


# =============================================================================
# TAB 1: LIVE MALAYSIA PROPERTY NEWS
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

    for entry in fetch_property_news()[:6]:
        col_img, col_text = st.columns([1, 2.5])
        image_url = entry.media_content[0].get('url') if 'media_content' in entry and entry.media_content else None
        with col_img:
            if image_url:
                st.image(image_url, use_column_width=True)
            else:
                st.info("🖼️ Property News")
        with col_text:
            st.markdown(f"### [{entry.title}]({entry.link})")
            st.caption(f"🗓️ Published: {entry.get('published', 'Recent')[:16]}")
        st.markdown("---")


# =============================================================================
# TAB 2: MORTGAGE + LEGAL FEES + STAMP DUTY
# =============================================================================
with tab_mortgage:
    st.header("🏦 Mortgage, Legal Fees & Stamp Duty Calculator")
    
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
        selected_bank = st.selectbox("Select Bank Profile", list(bank_rates_data.keys()))
        default_rate = float(bank_rates_data[selected_bank][prop_cat])

        prop_price = st.number_input("Property Purchase Price (RM)", min_value=50000, value=600000, step=50000)
        margin_finance = st.slider("Margin of Finance (%)", min_value=10, max_value=90, value=90, step=5)
        loan_amt = prop_price * (margin_finance / 100)
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
    mot_sd = calc_mot_stamp_duty(prop_price)
    loan_sd = loan_amt * 0.005
    total_fees = spa_legal + loan_legal + mot_sd + loan_sd + ((spa_legal + loan_legal) * 0.08 + 2000)
    
    monthly_i = (interest_rate / 100) / 12
    m_pay = loan_amt * (monthly_i * (1 + monthly_i)**(loan_tenure * 12)) / ((1 + monthly_i)**(loan_tenure * 12) - 1) if monthly_i > 0 else loan_amt / (loan_tenure * 12)

    with col2:
        st.metric("Estimated Monthly Installment", f"RM {m_pay:,.2f}")
        st.metric("Total Upfront Cash Needed", f"RM {(prop_price - loan_amt + total_fees):,.2f}")


# =============================================================================
# TAB 3: TENANCY STAMP DUTY CALCULATOR
# =============================================================================
with tab_tenancy:
    st.header("📜 Tenancy Agreement Stamp Duty Calculator")
    m_rent = st.number_input("Monthly Rental Amount (RM)", min_value=100, value=2500, step=100)
    lease_term = st.selectbox("Lease Duration", ["1 Year or less", "1 to 3 Years", "3 to 5 Years", "Above 5 Years"])
    annual_r = m_rent * 12
    units = math.ceil(annual_r / 250)
    rate = 1.0 if "1 Year" in lease_term else (3.0 if "1 to 3" in lease_term else (5.0 if "3 to 5" in lease_term else 7.0))
    st.metric("Total LHDN Stamp Duty Payable", f"RM {max(10, units * rate):,.2f}")


# =============================================================================
# TAB 4: MALAYSIA BUDGET HIGHLIGHTS
# =============================================================================
with tab_budget:
    st.header("📊 Malaysia Budget Real Estate Highlights")
    st.markdown("""
    * **First-Time Homebuyers:** 100% Stamp Duty Exemption on MOT & Loan Agreements for homes up to RM500,000.
    * **SJKP Housing Scheme:** Government guarantees expanded to RM10 Billion for gig-workers and freelancers.
    * **Commercial Conversion:** Special 10% tax deduction on qualifying expenses for commercial-to-residential conversions.
    """)


# =============================================================================
# TAB 5: PROFESSIONAL SERVICES DIRECTORY
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