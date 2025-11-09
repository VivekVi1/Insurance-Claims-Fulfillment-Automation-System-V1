import streamlit as st
import pandas as pd
import pymysql
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Insurance Claim Processing",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for beautiful UI
st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding-top: 1rem;
    }
    
    /* Header styling */
    .header-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .header-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .header-subtitle {
        font-size: 1.2rem;
        opacity: 0.9;
        margin: 0;
    }
    
    /* Metric cards styling */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 4px solid;
        margin-bottom: 1rem;
        transition: transform 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }
    
    .metric-users { border-left-color: #4CAF50; }
    .metric-total { border-left-color: #2196F3; }
    .metric-pending { border-left-color: #FF9800; }
    .metric-completed { border-left-color: #9C27B0; }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        color: #333;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .metric-icon {
        font-size: 2rem;
        float: right;
        opacity: 0.7;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 8px;
        border-radius: 12px;
        margin-bottom: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        color: #666;
        font-weight: 600;
        padding: 12px 24px;
        border: none;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Data table styling */
    .stDataFrame {
        background: white;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* Status badges */
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .status-pending {
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }
    
    .status-completed {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    
    /* Section headers */
    .section-header {
        background: linear-gradient(90deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 2rem 0 1rem 0;
        border-left: 4px solid #667eea;
    }
    
    .section-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #333;
        margin: 0;
    }
    
    /* Service status styling */
    .service-status {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .service-name {
        font-weight: 600;
        color: #333;
    }
    
    .service-port {
        font-size: 0.9rem;
        color: #666;
    }
    
    /* Info boxes */
    .info-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #2196F3;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #FF9800;
        margin: 1rem 0;
    }
    
    .error-box {
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #f44336;
        margin: 1rem 0;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Database connection
@st.cache_resource
def get_db_connection():
    """Create database connection"""
    try:
        connection = pymysql.connect(
            host=os.getenv('RDS_HOST'),
            port=int(os.getenv('RDS_PORT', 3306)),
            user=os.getenv('RDS_USER'),
            password=os.getenv('RDS_PASSWORD'),
            database=os.getenv('RDS_DATABASE'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        st.error(f"Database connection failed: {str(e)}")
        return None

# API health check
def check_api_health(url):
    """Check if API is online"""
    try:
        response = requests.get(url, timeout=2)
        return response.status_code == 200
    except:
        return False

# Fetch data functions
@st.cache_data(ttl=30)  # Cache for 30 seconds
def fetch_fulfillments(_connection, status_filter=None):
    """Fetch fulfillment data"""
    try:
        with _connection.cursor() as cursor:
            if status_filter and status_filter != "All":
                query = """
                SELECT fulfillment_id, user_mail, claim_id, 
                       fulfillment_status, attachment_count, created_at
                FROM fulfillment 
                WHERE fulfillment_status = %s 
                ORDER BY created_at DESC 
                LIMIT 100
                """
                cursor.execute(query, (status_filter.lower(),))
            else:
                query = """
                SELECT fulfillment_id, user_mail, claim_id, 
                       fulfillment_status, attachment_count, created_at
                FROM fulfillment 
                ORDER BY created_at DESC 
                LIMIT 100
                """
                cursor.execute(query)
            
            results = cursor.fetchall()
            return pd.DataFrame(results) if results else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching fulfillments: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=10)  # Cache for 10 seconds to ensure fresh data
def fetch_users(_connection):
    """Fetch user data"""
    try:
        with _connection.cursor() as cursor:
            query = """
            SELECT mail_id, policy_type, policy_issued_date
            FROM user_details 
            ORDER BY id DESC 
            LIMIT 100
            """
            cursor.execute(query)
            results = cursor.fetchall()
            return pd.DataFrame(results) if results else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching users: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=60)  # Cache for 60 seconds
def fetch_mail_status(_connection):
    """Fetch last mail check status"""
    try:
        with _connection.cursor() as cursor:
            query = "SELECT * FROM last_mail_details_vv ORDER BY id DESC LIMIT 1"
            cursor.execute(query)
            return cursor.fetchone()
    except Exception as e:
        return None

@st.cache_data(ttl=10)  # Cache for 10 seconds to get updated metrics quickly
def get_kpi_metrics(_connection):
    """Get KPI metrics"""
    try:
        with _connection.cursor() as cursor:
            # Total users
            cursor.execute("SELECT COUNT(*) as count FROM user_details")
            total_users = cursor.fetchone()['count']
            
            # Total fulfillments
            cursor.execute("SELECT COUNT(*) as count FROM fulfillment")
            total_fulfillments = cursor.fetchone()['count']
            
            # Pending fulfillments
            cursor.execute("SELECT COUNT(*) as count FROM fulfillment WHERE fulfillment_status = 'pending'")
            pending_fulfillments = cursor.fetchone()['count']
            
            # Completed fulfillments
            cursor.execute("SELECT COUNT(*) as count FROM fulfillment WHERE fulfillment_status = 'completed'")
            completed_fulfillments = cursor.fetchone()['count']
            
            return {
                'total_users': total_users,
                'total_fulfillments': total_fulfillments,
                'pending_fulfillments': pending_fulfillments,
                'completed_fulfillments': completed_fulfillments
            }
    except Exception as e:
        return {
            'total_users': 0,
            'total_fulfillments': 0,
            'pending_fulfillments': 0,
            'completed_fulfillments': 0
        }

def clear_all_caches():
    """Clear all cached data to ensure fresh information"""
    try:
        get_db_connection.clear()
        fetch_users.clear()
        fetch_fulfillments.clear()
        get_kpi_metrics.clear()
        fetch_mail_status.clear()
        st.cache_data.clear()
    except:
        pass  # Ignore errors if caches don't exist

def add_user_to_database(email, policy_type, policy_date):
    """Add new user to database via API"""
    try:
        user_validator_url = "http://localhost:8000"
        
        user_data = {
            "mail_id": email,
            "policy_type": policy_type,
            "policy_issued_date": policy_date.strftime('%Y-%m-%d')
        }
        
        response = requests.post(f"{user_validator_url}/user", json=user_data, timeout=10)
        
        if response.status_code == 201:
            # Clear all caches to ensure fresh data
            clear_all_caches()
            return True, "User added successfully!"
        elif response.status_code == 400:
            error_data = response.json()
            return False, error_data.get('detail', 'User already exists or invalid data')
        else:
            return False, f"Failed to add user. Status code: {response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return False, f"API connection error: {str(e)}"
    except Exception as e:
        return False, f"Error adding user: {str(e)}"

# Beautiful header
st.markdown("""
<div class="header-container">
    <h1 class="header-title">🏥 Dashboard</h1>
    <p class="header-subtitle">Real-time monitoring and management of insurance claim processing</p>
</div>
""", unsafe_allow_html=True)

# Create tabs with icons
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📋 Claims", "👥 Users", "⚙️ System"])

connection = get_db_connection()

if connection:
    # Overview Tab
    with tab1:
        kpis = get_kpi_metrics(connection)
        
        # Beautiful KPI cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card metric-users">
                <div class="metric-icon">👥</div>
                <h2 class="metric-value">{kpis['total_users']:,}</h2>
                <p class="metric-label">Total Users</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card metric-total">
                <div class="metric-icon">📄</div>
                <h2 class="metric-value">{kpis['total_fulfillments']:,}</h2>
                <p class="metric-label">Total Claims</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card metric-pending">
                <div class="metric-icon">⏳</div>
                <h2 class="metric-value">{kpis['pending_fulfillments']:,}</h2>
                <p class="metric-label">Pending Claims</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card metric-completed">
                <div class="metric-icon">✅</div>
                <h2 class="metric-value">{kpis['completed_fulfillments']:,}</h2>
                <p class="metric-label">Completed Claims</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Section header for recent claims
        st.markdown("""
        <div class="section-header">
            <h2 class="section-title">🕒 Recent Claims Activity</h2>
        </div>
        """, unsafe_allow_html=True)
        
        recent_claims = fetch_fulfillments(connection)
        if not recent_claims.empty:
            display_cols = ['claim_id', 'user_mail', 'fulfillment_status', 'created_at']
            if all(col in recent_claims.columns for col in display_cols):
                recent_display = recent_claims[display_cols].head(10)
                recent_display['created_at'] = pd.to_datetime(recent_display['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                
                # Add status styling
                recent_display['fulfillment_status'] = recent_display['fulfillment_status'].apply(
                    lambda x: f"🟡 {x.title()}" if x == 'pending' else f"🟢 {x.title()}"
                )
                
                st.dataframe(
                    recent_display, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "claim_id": st.column_config.TextColumn("Claim ID", width="medium"),
                        "user_mail": st.column_config.TextColumn("User Email", width="large"),
                        "fulfillment_status": st.column_config.TextColumn("Status", width="small"),
                        "created_at": st.column_config.TextColumn("Created", width="medium")
                    }
                )
        else:
            st.markdown("""
            <div class="info-box">
                <h4>📝 No Claims Found</h4>
                <p>There are currently no claims in the system. New claims will appear here automatically.</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Claims Tab
    with tab2:
        # Filter section
        st.markdown("""
        <div class="section-header">
            <h2 class="section-title">🔍 Filter Claims</h2>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            status_filter = st.selectbox(
                "Filter by Status", 
                ["All", "Pending", "Completed"],
                help="Select a status to filter claims"
            )
        
        fulfillments_df = fetch_fulfillments(connection, status_filter)
        
        if not fulfillments_df.empty:
            st.markdown(f"""
            <div class="info-box">
                <h4>📊 Results</h4>
                <p>Found <strong>{len(fulfillments_df)}</strong> claims matching your criteria</p>
            </div>
            """, unsafe_allow_html=True)
            
            display_cols = ['claim_id', 'user_mail', 'fulfillment_status', 'attachment_count', 'created_at']
            if all(col in fulfillments_df.columns for col in display_cols):
                display_df = fulfillments_df[display_cols].copy()
                display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                
                # Enhanced status display
                display_df['fulfillment_status'] = display_df['fulfillment_status'].apply(
                    lambda x: f"🟡 {x.title()}" if x == 'pending' else f"🟢 {x.title()}"
                )
                
                st.dataframe(
                    display_df, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "claim_id": st.column_config.TextColumn("Claim ID", width="medium"),
                        "user_mail": st.column_config.TextColumn("User Email", width="large"),
                        "fulfillment_status": st.column_config.TextColumn("Status", width="small"),
                        "attachment_count": st.column_config.NumberColumn("Attachments", width="small"),
                        "created_at": st.column_config.TextColumn("Created", width="medium")
                    }
                )
        else:
            st.markdown("""
            <div class="warning-box">
                <h4>🔍 No Claims Found</h4>
                <p>No claims match the selected filter criteria. Try adjusting your search parameters.</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Users Tab
    with tab3:
        # Add User Section
        st.markdown("""
        <div class="section-header">
            <h2 class="section-title">➕ Add New User</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Create form columns
        col1, col2 = st.columns([2, 1])
        
        with col1:
            with st.form("add_user_form"):
                st.markdown("#### User Details")
                
                # Form fields
                email = st.text_input(
                    "Email Address *",
                    placeholder="user@example.com",
                    help="Enter a valid email address"
                )
                
                policy_type = st.selectbox(
                    "Policy Type *",
                    ["Health Insurance", "Life Insurance", "Auto Insurance", "Home Insurance", "Travel Insurance"],
                    help="Select the type of insurance policy"
                )
                
                policy_date = st.date_input(
                    "Policy Issued Date *",
                    value=datetime.now().date(),
                    help="Select when the policy was issued"
                )
                
                # Submit button
                submitted = st.form_submit_button("🔒 Add User", use_container_width=True)
                
                if submitted:
                    # Validation
                    if not email or "@" not in email:
                        st.error("❌ Please enter a valid email address")
                    elif not policy_type:
                        st.error("❌ Please select a policy type")
                    elif not policy_date:
                        st.error("❌ Please select a policy date")
                    else:
                        # Add user to database
                        with st.spinner("Adding user..."):
                            success, message = add_user_to_database(email, policy_type, policy_date)
                            
                            if success:
                                st.success(f"✅ {message}")
                                # Add a small delay to ensure database transaction is complete
                                import time
                                time.sleep(0.5)
                                # Force page refresh to show new user
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
        
        with col2:
            st.markdown("""
            <div class="info-box">
                <h4>ℹ️ Instructions</h4>
                <p><strong>Required Fields:</strong></p>
                <ul>
                    <li>Valid email address</li>
                    <li>Policy type selection</li>
                    <li>Policy issued date</li>
                </ul>
                <p><small>All fields marked with * are required</small></p>
            </div>
            """, unsafe_allow_html=True)
        
        # Divider
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Existing Users Section
        st.markdown("""
        <div class="section-header">
            <h2 class="section-title">👥 Registered Users</h2>
        </div>
        """, unsafe_allow_html=True)
        
        users_df = fetch_users(connection)
        
        if not users_df.empty:
            st.markdown(f"""
            <div class="info-box">
                <h4>📊 User Statistics</h4>
                <p>Total registered users: <strong>{len(users_df)}</strong></p>
            </div>
            """, unsafe_allow_html=True)
            
            if 'policy_issued_date' in users_df.columns:
                users_df['policy_issued_date'] = pd.to_datetime(users_df['policy_issued_date']).dt.strftime('%Y-%m-%d')
            
            st.dataframe(
                users_df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "mail_id": st.column_config.TextColumn("Email Address", width="large"),
                    "policy_type": st.column_config.TextColumn("Policy Type", width="medium"),
                    "policy_issued_date": st.column_config.TextColumn("Policy Date", width="medium")
                }
            )
        else:
            st.markdown("""
            <div class="warning-box">
                <h4>👥 No Users Found</h4>
                <p>No registered users found in the system. Add your first user above!</p>
            </div>
            """, unsafe_allow_html=True)
    
    # System Tab
    with tab4:
        st.markdown("""
        <div class="section-header">
            <h2 class="section-title">🌐 API Services Status</h2>
        </div>
        """, unsafe_allow_html=True)
        
        services = [
            {"name": "User Validator API", "url": "http://localhost:8000/", "port": 8000, "icon": "👤"},
            {"name": "Mail Service API", "url": "http://localhost:8001/", "port": 8001, "icon": "📧"},
            {"name": "Fulfillment API", "url": "http://localhost:8002/", "port": 8002, "icon": "📋"}
        ]
        
        for service in services:
            is_online = check_api_health(service['url'])
            status_color = "#d4edda" if is_online else "#f8d7da"
            status_text = "🟢 Online" if is_online else "🔴 Offline"
            status_icon = "✅" if is_online else "❌"
            
            st.markdown(f"""
            <div class="service-status" style="background-color: {status_color};">
                <div>
                    <span class="service-name">{service['icon']} {service['name']}</span>
                    <br>
                    <span class="service-port">Port: {service['port']}</span>
                </div>
                <div style="font-weight: bold; font-size: 1.1rem;">
                    {status_text}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="section-header">
            <h2 class="section-title">📧 Email Processing Status</h2>
        </div>
        """, unsafe_allow_html=True)
        
        mail_status = fetch_mail_status(connection)
        if mail_status:
            mail_count = mail_status.get('mail_count', 0)
            last_check = mail_status.get('last_connection_time', 'Unknown')
            
            st.markdown(f"""
            <div class="info-box">
                <h4>📊 Email Statistics</h4>
                <p><strong>📬 Emails Processed:</strong> {mail_count:,}</p>
                <p><strong>🕒 Last Check:</strong> {last_check}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="warning-box">
                <h4>📧 Email Status Unavailable</h4>
                <p>No email processing data is currently available.</p>
            </div>
            """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div class="error-box">
        <h4>❌ Database Connection Failed</h4>
        <p>Unable to connect to the database. Please check your connection settings and try again.</p>
    </div>
    """, unsafe_allow_html=True) 