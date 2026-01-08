import streamlit as st
import json
from pymongo import MongoClient
from openai import OpenAI
import anthropic
import pandas as pd
from datetime import datetime
import certifi
import config


# =============================================================================
# TEST USER CREDENTIALS & SECURITY ROLES
# =============================================================================
# 
# FSM System Role Hierarchy:
# 
# 1. SUPER SYSTEM4 ADMIN (Top Level Corporate - CEO, CTO, etc.)
#    - Highest level access with full control over everything
#    - Has System4 Admin permissions + additional privileges
#    - Can manage all 65+ franchises, users, and system settings
#
# 2. SYSTEM4 ADMIN (Corporate Staff)
#    - Company headquarters staff
#    - Can view/analyze data across ALL franchises
#    - Example: Corporate managers, analysts, support staff
#
# 3. FRANCHISE PARTNER (Franchise Owners)
#    - Actual franchise owners who own/operate location(s)
#    - Can see ALL data for their specific franchise location(s)
#    - Full access within their franchise scope
#
# 4. CLIENT ADMIN (Franchise Employees)
#    - Employees working at a franchise location
#    - Limited access - currently set to Franchise Partner security level
#    - Can view franchise data but with restricted permissions
#
# =============================================================================

# =============================================================================
# FRANCHISE TO STATE MAPPING
# =============================================================================
# Maps franchise names to their corresponding state codes for data filtering
# This ensures Franchise Partners and Client Admins only see their location data
FRANCHISE_STATE_MAPPING = {
    "Boston": ["MA"],           # Massachusetts
    "Cleveland": ["OH"],        # Ohio
    "Chicago": ["IL"],          # Illinois
    "Charleston": ["SC"],       # South Carolina
    "Columbia": ["SC"],         # South Carolina
    "Georgia": ["GA"],          # Georgia
    "Maryland": ["MD"],         # Maryland
    "Northern VA": ["VA"],      # Virginia
    "Richmond": ["VA"],         # Virginia
    "Washington DC": ["DC"],    # District of Columbia
}

# =============================================================================
# COLLECTION STATE FIELD MAPPING
# =============================================================================
# Maps collection names (case-insensitive) to their state field names
# Different collections use different field names for state
COLLECTION_STATE_FIELDS = {
    # Customer collections - use serviceAddressState
    "customeractive": "serviceAddressState",
    "customersactivation": "serviceAddressState",
    "customerssuspended": "serviceAddressState",
    "customersterminated": "serviceAddressState",
    # Leads
    "leads": "serviceAddressState",
    # Proposals
    "proposals": "serviceAddressState",
    # Service contracts - uses companyState
    "servicecontracts": "companyState",
    # Service providers - nested field
    "serviceproviders": "address.state",
    # RFPs - filter by serviceAddressState if available
    "rfps": "serviceAddressState",
    # Collections without location data (shared across all franchises)
    "spusers": None,
    "users_inspection": None,
    "general_ledger": None,
    "inspection_dashboard": None,
}


TEST_USERS = {
    # =========================================================================
    # SUPER SYSTEM4 ADMIN - Top Level Corporate (CEO, CTO, etc.)
    # Full control over everything
    # =========================================================================
    "ceo@system4.com": {
        "password": "ceo123",
        "name": "Robert Maxwell",
        "role": "Super System4 Admin",
        "permissions": ["all", "system_settings", "user_management", "franchise_management", "financial_reports", "audit_logs"],
        "franchise": "All Franchises",
        "avatar": "👑"
    },
    "cto@system4.com": {
        "password": "cto123",
        "name": "Jennifer Hayes",
        "role": "Super System4 Admin",
        "permissions": ["all", "system_settings", "user_management", "franchise_management", "financial_reports", "audit_logs"],
        "franchise": "All Franchises",
        "avatar": "🎯"
    },
    
    # =========================================================================
    # SYSTEM4 ADMIN - Corporate Staff
    # Can see data across ALL 65+ franchises
    # =========================================================================
    "manager@system4.com": {
        "password": "manager123",
        "name": "Sarah Mitchell",
        "role": "System4 Admin",
        "permissions": ["view_all_franchises", "reports", "analytics", "user_support"],
        "franchise": "All Franchises",
        "avatar": "🔧"
    },
    "analyst@system4.com": {
        "password": "analyst123",
        "name": "Tom Anderson",
        "role": "System4 Admin",
        "permissions": ["view_all_franchises", "reports", "analytics"],
        "franchise": "All Franchises",
        "avatar": "📊"
    },
    "support@system4.com": {
        "password": "support123",
        "name": "Emily Chen",
        "role": "System4 Admin",
        "permissions": ["view_all_franchises", "user_support", "basic_reports"],
        "franchise": "All Franchises",
        "avatar": "🛠️"
    },
    
    # =========================================================================
    # FRANCHISE PARTNER - Franchise Owners
    # Can see ALL data for their franchise location(s)
    # =========================================================================
    "owner.boston@franchise.com": {
        "password": "boston123",
        "name": "Michael O'Brien",
        "role": "Franchise Partner",
        "permissions": ["view_franchise", "manage_franchise", "franchise_reports", "manage_employees"],
        "franchise": "Boston",
        "avatar": "🏢"
    },
    "owner.cleveland@franchise.com": {
        "password": "cleveland123",
        "name": "David Kowalski",
        "role": "Franchise Partner",
        "permissions": ["view_franchise", "manage_franchise", "franchise_reports", "manage_employees"],
        "franchise": "Cleveland",
        "avatar": "🏛️"
    },
    "owner.chicago@franchise.com": {
        "password": "chicago123",
        "name": "Rachel Thompson",
        "role": "Franchise Partner",
        "permissions": ["view_franchise", "manage_franchise", "franchise_reports", "manage_employees"],
        "franchise": "Chicago",
        "avatar": "🌆"
    },
    "owner.charleston@franchise.com": {
        "password": "charleston123",
        "name": "William Parker",
        "role": "Franchise Partner",
        "permissions": ["view_franchise", "manage_franchise", "franchise_reports", "manage_employees"],
        "franchise": "Charleston",
        "avatar": "🌴"
    },
    "owner.columbia@franchise.com": {
        "password": "columbia123",
        "name": "Amanda Foster",
        "role": "Franchise Partner",
        "permissions": ["view_franchise", "manage_franchise", "franchise_reports", "manage_employees"],
        "franchise": "Columbia",
        "avatar": "🏛️"
    },
    "owner.georgia@franchise.com": {
        "password": "georgia123",
        "name": "James Wilson",
        "role": "Franchise Partner",
        "permissions": ["view_franchise", "manage_franchise", "franchise_reports", "manage_employees"],
        "franchise": "Georgia",
        "avatar": "🍑"
    },
    "owner.maryland@franchise.com": {
        "password": "maryland123",
        "name": "Patricia Brown",
        "role": "Franchise Partner",
        "permissions": ["view_franchise", "manage_franchise", "franchise_reports", "manage_employees"],
        "franchise": "Maryland",
        "avatar": "🦀"
    },
    "owner.nova@franchise.com": {
        "password": "nova123",
        "name": "Christopher Davis",
        "role": "Franchise Partner",
        "permissions": ["view_franchise", "manage_franchise", "franchise_reports", "manage_employees"],
        "franchise": "Northern VA",
        "avatar": "🏢"
    },
    "owner.richmond@franchise.com": {
        "password": "richmond123",
        "name": "Elizabeth Turner",
        "role": "Franchise Partner",
        "permissions": ["view_franchise", "manage_franchise", "franchise_reports", "manage_employees"],
        "franchise": "Richmond",
        "avatar": "🏰"
    },
    "owner.dc@franchise.com": {
        "password": "dc123",
        "name": "Robert Harris",
        "role": "Franchise Partner",
        "permissions": ["view_franchise", "manage_franchise", "franchise_reports", "manage_employees"],
        "franchise": "Washington DC",
        "avatar": "🏛️"
    },
    
    # =========================================================================
    # CLIENT ADMIN - Franchise Employees
    # Limited access (currently using Franchise Partner security level)
    # =========================================================================
    "staff.boston@franchise.com": {
        "password": "staff123",
        "name": "Lisa Martinez",
        "role": "Client Admin",
        "permissions": ["view_franchise", "basic_reports"],
        "franchise": "Boston",
        "avatar": "👤"
    },
    "staff.cleveland@franchise.com": {
        "password": "staff456",
        "name": "Kevin Johnson",
        "role": "Client Admin",
        "permissions": ["view_franchise", "basic_reports"],
        "franchise": "Cleveland",
        "avatar": "👨‍💼"
    },
    "staff.charleston@franchise.com": {
        "password": "staff789",
        "name": "Maria Rodriguez",
        "role": "Client Admin",
        "permissions": ["view_franchise", "basic_reports"],
        "franchise": "Charleston",
        "avatar": "👩‍💼"
    },
    "staff.columbia@franchise.com": {
        "password": "staff101",
        "name": "Daniel Lee",
        "role": "Client Admin",
        "permissions": ["view_franchise", "basic_reports"],
        "franchise": "Columbia",
        "avatar": "👤"
    },
    "staff.georgia@franchise.com": {
        "password": "staff102",
        "name": "Ashley Clark",
        "role": "Client Admin",
        "permissions": ["view_franchise", "basic_reports"],
        "franchise": "Georgia",
        "avatar": "👩"
    },
    "staff.maryland@franchise.com": {
        "password": "staff103",
        "name": "Ryan Moore",
        "role": "Client Admin",
        "permissions": ["view_franchise", "basic_reports"],
        "franchise": "Maryland",
        "avatar": "👨"
    },
    "staff.nova@franchise.com": {
        "password": "staff104",
        "name": "Jessica White",
        "role": "Client Admin",
        "permissions": ["view_franchise", "basic_reports"],
        "franchise": "Northern VA",
        "avatar": "👩‍💻"
    },
    "staff.richmond@franchise.com": {
        "password": "staff105",
        "name": "Brandon Taylor",
        "role": "Client Admin",
        "permissions": ["view_franchise", "basic_reports"],
        "franchise": "Richmond",
        "avatar": "👨‍💻"
    },
    "staff.dc@franchise.com": {
        "password": "staff106",
        "name": "Nicole Adams",
        "role": "Client Admin",
        "permissions": ["view_franchise", "basic_reports"],
        "franchise": "Washington DC",
        "avatar": "👩‍🏫"
    }
}


def authenticate_user(email, password):
    """Authenticate user with test credentials"""
    if email in TEST_USERS and TEST_USERS[email]["password"] == password:
        user_data = TEST_USERS[email].copy()
        user_data["email"] = email
        del user_data["password"]  # Don't store password in session
        return user_data
    return None


def get_user_franchise_filter():
    """
    Get the franchise filter for the current logged-in user.
    Returns None if user can see all data, or a list of state codes to filter by.
    
    Currently disabled - all users can see all data regardless of role.
    """
    # Filtering disabled - all roles see all data
    return None


def get_state_field_for_collection(collection_name):
    """
    Get the state field name for a given collection.
    Returns None if the collection has no location data.
    """
    if not collection_name:
        return None
    
    # Normalize collection name for lookup (lowercase, remove underscores/hyphens)
    coll_lower = collection_name.lower().replace("_", "").replace("-", "")
    
    # Try exact match first
    if coll_lower in COLLECTION_STATE_FIELDS:
        return COLLECTION_STATE_FIELDS[coll_lower]
    
    # Try partial match for collections
    for key, field in COLLECTION_STATE_FIELDS.items():
        if key in coll_lower or coll_lower in key:
            return field
    
    # Default to serviceAddressState for unknown collections that might have location
    return "serviceAddressState"


def build_franchise_filter(franchise_states, state_field):
    """
    Build a MongoDB query filter for state-based filtering.
    Returns None if no filter needed or no state field.
    
    Args:
        franchise_states: List of state codes (e.g., ["MA", "OH"])
        state_field: The field name containing state data
    
    Returns:
        MongoDB filter condition or None
    """
    if not franchise_states or not state_field:
        return None
    
    # Handle nested fields like "address.state"
    if len(franchise_states) == 1:
        return {state_field: {"$regex": f"^{franchise_states[0]}$", "$options": "i"}}
    else:
        return {
            "$or": [
                {state_field: {"$regex": f"^{state}$", "$options": "i"}} 
                for state in franchise_states
            ]
        }


def apply_franchise_filter_to_query(query, franchise_states, collection_name):
    """
    Apply franchise state filter to an existing MongoDB query.
    
    Args:
        query: The original MongoDB query dict
        franchise_states: List of state codes to filter by
        collection_name: Name of the collection being queried
    
    Returns:
        Modified query with franchise filter applied, or original query if no filter needed
    """
    if not franchise_states:
        return query
    
    state_field = get_state_field_for_collection(collection_name)
    if not state_field:
        return query  # Collection has no location data
    
    franchise_filter = build_franchise_filter(franchise_states, state_field)
    if not franchise_filter:
        return query
    
    # Combine with existing query
    if query:
        return {"$and": [query, franchise_filter]}
    else:
        return franchise_filter


def show_login_page():
    """Display the login page - Professional & User-Friendly Interface"""
    
    # Custom CSS for login page
    st.markdown("""
    <style>
        /* Login Page Specific Styles */
        .login-wrapper {
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem;
        }
        
        .login-hero {
            text-align: center;
            padding: 3rem 1rem 2rem;
            margin-bottom: 1.5rem;
            background: linear-gradient(180deg, rgba(99, 102, 241, 0.1) 0%, transparent 100%);
            border-radius: 24px;
        }
        
        .login-logo-container {
            width: 100px;
            height: 100px;
            margin: 0 auto 1.5rem;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
            border-radius: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
            box-shadow: 0 20px 60px rgba(99, 102, 241, 0.4);
            animation: float 3s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
        
        .login-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #f1f5f9;
            margin: 0 0 0.75rem 0;
            letter-spacing: -0.025em;
        }
        
        .login-subtitle {
            color: #94a3b8;
            font-size: 1.1rem;
            margin: 0 0 1rem 0;
        }
        
        .login-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(34, 197, 94, 0.15);
            border: 1px solid rgba(34, 197, 94, 0.3);
            padding: 8px 16px;
            border-radius: 50px;
            font-size: 0.85rem;
            color: #22c55e;
        }
        
        .login-badge::before {
            content: '';
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            animation: pulse-dot 2s ease-in-out infinite;
        }
        
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.8); }
        }
        
        /* Manual Login Section */
        .manual-login-section {
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 1.5rem;
            margin-top: 1rem;
        }
        
        .manual-login-header {
            text-align: center;
            margin-bottom: 1.5rem;
        }
        
        .manual-login-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #f1f5f9;
            margin: 0 0 0.5rem 0;
        }
        
        .manual-login-desc {
            font-size: 0.875rem;
            color: #64748b;
            margin: 0;
        }
        
        /* Credential Card Styles */
        .cred-section {
            margin-bottom: 1.5rem;
        }
        
        .cred-section-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .cred-section-icon {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
        }
        
        .cred-section-title {
            font-size: 0.9rem;
            font-weight: 600;
            color: #f1f5f9;
            margin: 0;
        }
        
        .cred-section-desc {
            font-size: 0.75rem;
            color: #64748b;
            margin: 0;
        }
        
        .cred-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0.75rem;
            background: rgba(15, 23, 42, 0.5);
            border-radius: 8px;
            margin-bottom: 0.5rem;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.2s ease;
        }
        
        .cred-item:hover {
            background: rgba(99, 102, 241, 0.1);
            border-color: rgba(99, 102, 241, 0.2);
        }
        
        .cred-email {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: #a5b4fc;
        }
        
        .cred-password {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: #fcd34d;
            background: rgba(251, 191, 36, 0.1);
            padding: 2px 8px;
            border-radius: 4px;
        }
        
        /* Divider */
        .divider-pro {
            display: flex;
            align-items: center;
            margin: 1.5rem 0;
            gap: 1rem;
        }
        
        .divider-pro::before,
        .divider-pro::after {
            content: '';
            flex: 1;
            height: 1px;
            background: linear-gradient(90deg, transparent, #334155, transparent);
        }
        
        .divider-pro span {
            color: #64748b;
            font-size: 0.8rem;
            white-space: nowrap;
        }
        
        /* Footer */
        .login-footer {
            text-align: center;
            padding: 2rem 1rem;
            color: #64748b;
            font-size: 0.8rem;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            margin-top: 2rem;
        }
        
        .login-footer p {
            margin: 0.25rem 0;
        }
        
        .login-footer a {
            color: #6366f1;
            text-decoration: none;
        }
        
        /* Login Tabs Styling */
        .stTabs [data-baseweb="tab-list"] {
            justify-content: center;
            gap: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Hero Section
    st.markdown('''
    <div class="login-hero">
        <div class="login-logo-container">⚡</div>
        <h1 class="login-title">FMS Query Engine</h1>
        <p class="login-subtitle">AI-Powered Franchise Management Analytics</p>
        <div class="login-badge">System Online • Ready to Connect</div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Create tabs for different login methods
    tab1, tab2 = st.tabs(["👥 Select Account", "🔐 Manual Login"])
    
    with tab1:
        # Clean centered layout
        col1, col2, col3 = st.columns([1, 2.5, 1])
        
        with col2:
            st.markdown("""
            <div style="text-align: center; margin-bottom: 1.5rem;">
                <p style="color: #f1f5f9; font-size: 1.1rem; font-weight: 500; margin: 0 0 0.5rem 0;">Quick Account Selection</p>
                <p style="color: #64748b; font-size: 0.875rem; margin: 0;">Choose a role and select an account to sign in instantly</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Build user options for selectbox
            user_options = {}
            for email, user in TEST_USERS.items():
                franchise_info = f" ({user['franchise']})" if user.get('franchise') and user['franchise'] != "All Franchises" else ""
                display_name = f"{user['name']} - {user['role']}{franchise_info}"
                user_options[display_name] = email
            
            # Role filter with icon
            st.markdown('<p style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;"><span>🏷️</span> Filter by role:</p>', unsafe_allow_html=True)
            
            role_filter = st.selectbox(
                "Filter by role",
                ["All Roles", "Super System4 Admin", "System4 Admin", "Franchise Partner", "Client Admin"],
                label_visibility="collapsed"
            )
            
            # Filter users based on selected role
            filtered_users = {}
            for email, user in TEST_USERS.items():
                if role_filter == "All Roles" or user['role'] == role_filter:
                    franchise_info = f" ({user['franchise']})" if user.get('franchise') and user['franchise'] != "All Franchises" else ""
                    display_name = f"{user['avatar']} {user['name']} - {user['role']}{franchise_info}"
                    filtered_users[display_name] = email
            
            st.markdown("")
            st.markdown('<p style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;"><span>👤</span> Select an account:</p>', unsafe_allow_html=True)
            
            # User selection dropdown
            selected_display = st.selectbox(
                "Select account",
                list(filtered_users.keys()),
                label_visibility="collapsed"
            )
            
            if selected_display:
                selected_email = filtered_users[selected_display]
                selected_user = TEST_USERS[selected_email]
                
                # Role color mapping
                role_colors = {
                    "Super System4 Admin": ("linear-gradient(135deg, #fbbf24, #f59e0b)", "#fbbf24"),
                    "System4 Admin": ("linear-gradient(135deg, #6366f1, #8b5cf6)", "#a78bfa"),
                    "Franchise Partner": ("linear-gradient(135deg, #10b981, #059669)", "#34d399"),
                    "Client Admin": ("linear-gradient(135deg, #0ea5e9, #0284c7)", "#38bdf8")
                }
                bg_gradient, text_color = role_colors.get(selected_user["role"], ("linear-gradient(135deg, #6366f1, #8b5cf6)", "#a78bfa"))
                
                # Show selected user info card
                st.markdown(f'''
                <div style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 16px; padding: 1.5rem; margin: 1.5rem 0; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);">
                    <div style="display: flex; align-items: center; gap: 1.25rem;">
                        <div style="width: 64px; height: 64px; background: {bg_gradient}; border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 2rem; box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);">{selected_user["avatar"]}</div>
                        <div style="flex: 1;">
                            <p style="color: #f1f5f9; font-size: 1.25rem; font-weight: 600; margin: 0;">{selected_user["name"]}</p>
                            <p style="color: {text_color}; font-size: 0.9rem; font-weight: 500; margin: 0.25rem 0 0 0;">{selected_user["role"]}</p>
                            <p style="color: #64748b; font-size: 0.8rem; margin: 0.5rem 0 0 0; font-family: monospace;">{selected_email}</p>
                        </div>
                    </div>
                    <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.1);">
                        <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                            <span style="background: rgba(99, 102, 241, 0.15); color: #a5b4fc; padding: 4px 12px; border-radius: 6px; font-size: 0.75rem;">📍 {selected_user.get("franchise", "N/A")}</span>
                            <span style="background: rgba(34, 197, 94, 0.15); color: #86efac; padding: 4px 12px; border-radius: 6px; font-size: 0.75rem;">✓ Ready to sign in</span>
                        </div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
                
                # Login button
                if st.button("🚀 Sign In Now", key="quick_login_btn", use_container_width=True, type="primary"):
                    user_data = authenticate_user(selected_email, selected_user['password'])
                    if user_data:
                        st.session_state.logged_in = True
                        st.session_state.user = user_data
                        st.rerun()
    
    with tab2:
        st.markdown("")  # Spacing
        
        # Center the manual login form
        col1, col2, col3 = st.columns([1, 2.5, 1])
        
        with col2:
            st.markdown("""
            <div class="manual-login-header">
                <div style="width: 56px; height: 56px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; margin: 0 auto 1rem; box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);">🔐</div>
                <p class="manual-login-title">Sign in with your credentials</p>
                <p class="manual-login-desc">Enter your email and password to access the system</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Manual Login Form
            with st.form("login_form", clear_on_submit=False):
                st.markdown('<p style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 0.25rem;">📧 Email Address</p>', unsafe_allow_html=True)
                email = st.text_input(
                    "Email Address",
                    placeholder="Enter your email address",
                    help="Use one of the test account emails",
                    label_visibility="collapsed"
                )
                
                st.markdown('<p style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 0.25rem; margin-top: 1rem;">🔑 Password</p>', unsafe_allow_html=True)
                password = st.text_input(
                    "Password", 
                    type="password",
                    placeholder="Enter your password",
                    help="Password for the test account",
                    label_visibility="collapsed"
                )
                
                st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
                submitted = st.form_submit_button("🚀 Sign In", use_container_width=True, type="primary")
                
                if submitted:
                    if email and password:
                        user_data = authenticate_user(email, password)
                        if user_data:
                            st.session_state.logged_in = True
                            st.session_state.user = user_data
                            st.rerun()
                        else:
                            st.error("❌ Invalid email or password. Please try again.")
                    else:
                        st.warning("⚠️ Please enter both email and password.")
            
            # Credentials reference - All Test Accounts
            with st.expander("📋 View All Test Account Credentials", expanded=False):
                st.markdown("""
                <div class="cred-section">
                    <div class="cred-section-header">
                        <div class="cred-section-icon" style="background: linear-gradient(135deg, #fbbf24, #f59e0b);">👑</div>
                        <div>
                            <p class="cred-section-title">Super System4 Admin</p>
                            <p class="cred-section-desc">Full system access • All franchises • Complete control</p>
                        </div>
                    </div>
                    <div class="cred-item"><span class="cred-email">ceo@system4.com</span><span class="cred-password">ceo123</span></div>
                    <div class="cred-item"><span class="cred-email">cto@system4.com</span><span class="cred-password">cto123</span></div>
                </div>
                
                <div class="cred-section">
                    <div class="cred-section-header">
                        <div class="cred-section-icon" style="background: linear-gradient(135deg, #6366f1, #8b5cf6);">🔧</div>
                        <div>
                            <p class="cred-section-title">System4 Admin</p>
                            <p class="cred-section-desc">Corporate staff • View all franchises • Reports & analytics</p>
                        </div>
                    </div>
                    <div class="cred-item"><span class="cred-email">manager@system4.com</span><span class="cred-password">manager123</span></div>
                    <div class="cred-item"><span class="cred-email">analyst@system4.com</span><span class="cred-password">analyst123</span></div>
                    <div class="cred-item"><span class="cred-email">support@system4.com</span><span class="cred-password">support123</span></div>
                </div>
                
                <div class="cred-section">
                    <div class="cred-section-header">
                        <div class="cred-section-icon" style="background: linear-gradient(135deg, #10b981, #059669);">🏢</div>
                        <div>
                            <p class="cred-section-title">Franchise Partner</p>
                            <p class="cred-section-desc">Franchise owners • Full franchise access • Manage employees</p>
                        </div>
                    </div>
                    <div class="cred-item"><span class="cred-email">owner.boston@franchise.com</span><span class="cred-password">boston123</span></div>
                    <div class="cred-item"><span class="cred-email">owner.cleveland@franchise.com</span><span class="cred-password">cleveland123</span></div>
                    <div class="cred-item"><span class="cred-email">owner.chicago@franchise.com</span><span class="cred-password">chicago123</span></div>
                    <div class="cred-item"><span class="cred-email">owner.charleston@franchise.com</span><span class="cred-password">charleston123</span></div>
                    <div class="cred-item"><span class="cred-email">owner.columbia@franchise.com</span><span class="cred-password">columbia123</span></div>
                    <div class="cred-item"><span class="cred-email">owner.georgia@franchise.com</span><span class="cred-password">georgia123</span></div>
                    <div class="cred-item"><span class="cred-email">owner.maryland@franchise.com</span><span class="cred-password">maryland123</span></div>
                    <div class="cred-item"><span class="cred-email">owner.nova@franchise.com</span><span class="cred-password">nova123</span></div>
                    <div class="cred-item"><span class="cred-email">owner.richmond@franchise.com</span><span class="cred-password">richmond123</span></div>
                    <div class="cred-item"><span class="cred-email">owner.dc@franchise.com</span><span class="cred-password">dc123</span></div>
                </div>
                
                <div class="cred-section">
                    <div class="cred-section-header">
                        <div class="cred-section-icon" style="background: linear-gradient(135deg, #0ea5e9, #0284c7);">👤</div>
                        <div>
                            <p class="cred-section-title">Client Admin</p>
                            <p class="cred-section-desc">Franchise employees • Limited access • Basic reports</p>
                        </div>
                    </div>
                    <div class="cred-item"><span class="cred-email">staff.boston@franchise.com</span><span class="cred-password">staff123</span></div>
                    <div class="cred-item"><span class="cred-email">staff.cleveland@franchise.com</span><span class="cred-password">staff456</span></div>
                    <div class="cred-item"><span class="cred-email">staff.charleston@franchise.com</span><span class="cred-password">staff789</span></div>
                    <div class="cred-item"><span class="cred-email">staff.columbia@franchise.com</span><span class="cred-password">staff101</span></div>
                    <div class="cred-item"><span class="cred-email">staff.georgia@franchise.com</span><span class="cred-password">staff102</span></div>
                    <div class="cred-item"><span class="cred-email">staff.maryland@franchise.com</span><span class="cred-password">staff103</span></div>
                    <div class="cred-item"><span class="cred-email">staff.nova@franchise.com</span><span class="cred-password">staff104</span></div>
                    <div class="cred-item"><span class="cred-email">staff.richmond@franchise.com</span><span class="cred-password">staff105</span></div>
                    <div class="cred-item"><span class="cred-email">staff.dc@franchise.com</span><span class="cred-password">staff106</span></div>
                </div>
                """, unsafe_allow_html=True)
    
    # Footer
    st.markdown('''
    <div class="login-footer">
        <p style="font-size: 1rem; color: #f1f5f9; font-weight: 600; margin-bottom: 0.5rem;">⚡ FMS Query Engine v2.0</p>
        <p>Powered by OpenAI GPT-4 & Anthropic Claude • MongoDB Backend</p>
        <p style="margin-top: 0.75rem;">© 2025 System4 Enterprise Analytics Suite</p>
    </div>
    ''', unsafe_allow_html=True)


def get_secret(key, default=None):
    """Get secret from environment variables or Streamlit secrets"""
    # First try config (environment variables)
    value = getattr(config, key, None)
    if value:
        return value
    # Then try Streamlit secrets
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default

# Page Configuration
st.set_page_config(
    page_title="FMS Query Engine | AI-Powered Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Custom CSS - Professional Enterprise Design
st.markdown("""
<style>
    /* Import Premium Fonts */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Root Variables */
    :root {
        --primary: #6366f1;
        --primary-dark: #4f46e5;
        --secondary: #0ea5e9;
        --accent: #10b981;
        --bg-dark: #0f172a;
        --bg-card: #1e293b;
        --bg-card-hover: #334155;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --border: #334155;
        --success: #22c55e;
        --warning: #f59e0b;
        --error: #ef4444;
        --gradient-1: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
        --gradient-2: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%);
        --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
        --shadow-glow: 0 0 40px rgba(99, 102, 241, 0.15);
    }
    
    /* Global Styles */
    .stApp {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        font-family: 'DM Sans', sans-serif;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main Container */
    .main .block-container {
        padding: 2rem 3rem;
        max-width: 1400px;
    }
    
    /* Hero Header */
    .hero-container {
        background: var(--gradient-1);
        border-radius: 20px;
        padding: 2.5rem 3rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
        box-shadow: var(--shadow-glow);
    }
    
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 60%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
        animation: pulse 4s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 0.5; transform: scale(1); }
        50% { opacity: 0.8; transform: scale(1.05); }
    }
    
    .hero-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: white;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.025em;
        position: relative;
        z-index: 1;
    }
    
    .hero-subtitle {
        font-size: 1.1rem;
        color: rgba(255,255,255,0.85);
        margin: 0;
        font-weight: 400;
        position: relative;
        z-index: 1;
    }
    
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(10px);
        padding: 6px 14px;
        border-radius: 50px;
        font-size: 0.8rem;
        color: white;
        margin-top: 1rem;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .hero-badge::before {
        content: '';
        width: 8px;
        height: 8px;
        background: #22c55e;
        border-radius: 50%;
        animation: blink 2s ease-in-out infinite;
    }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    
    /* Card Styles */
    .glass-card {
        background: rgba(30, 41, 59, 0.8);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.75rem;
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
        box-shadow: var(--shadow-md);
    }
    
    .glass-card:hover {
        border-color: rgba(99, 102, 241, 0.3);
        box-shadow: var(--shadow-lg), 0 0 30px rgba(99, 102, 241, 0.1);
        transform: translateY(-2px);
    }
    
    .card-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .card-title-icon {
        width: 32px;
        height: 32px;
        background: var(--gradient-1);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
    }
    
    /* Stats Cards */
    .stat-card {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.05) 100%);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .stat-card:hover {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.1) 100%);
        transform: scale(1.02);
    }
    
    .stat-value {
        font-size: 2.25rem;
        font-weight: 700;
        background: var(--gradient-1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.2;
    }
    
    .stat-label {
        font-size: 0.85rem;
        color: var(--text-secondary);
        margin-top: 0.25rem;
        font-weight: 500;
    }
    
    /* Query Input */
    .stTextArea textarea {
        background: var(--bg-card) !important;
        border: 2px solid var(--border) !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextArea textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2) !important;
    }
    
    .stTextArea textarea::placeholder {
        color: var(--text-secondary) !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: var(--gradient-1) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.875rem 2rem !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        font-family: 'DM Sans', sans-serif !important;
        letter-spacing: 0.025em !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.35) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 25px rgba(99, 102, 241, 0.45) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Sidebar Styles */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        border-right: 1px solid var(--border);
    }
    
    [data-testid="stSidebar"] .block-container {
        padding: 2rem 1.5rem;
    }
    
    .sidebar-header {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--primary);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin: 1.5rem 0 0.75rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border);
    }
    
    /* Sample Question Buttons */
    .sample-btn {
        background: rgba(99, 102, 241, 0.1) !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
        font-size: 0.875rem !important;
        padding: 0.75rem 1rem !important;
        text-align: left !important;
        transition: all 0.2s ease !important;
        margin-bottom: 0.5rem !important;
    }
    
    .sample-btn:hover {
        background: rgba(99, 102, 241, 0.2) !important;
        border-color: var(--primary) !important;
        transform: translateX(4px) !important;
    }
    
    /* Results Box */
    .result-box {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(34, 197, 94, 0.05) 100%);
        border: 1px solid rgba(34, 197, 94, 0.2);
        border-left: 4px solid var(--accent);
        border-radius: 12px;
        padding: 1.5rem;
        color: var(--text-primary);
        font-size: 1rem;
        line-height: 1.7;
    }
    
    /* Code Block Styling */
    .stCodeBlock {
        border-radius: 12px !important;
        border: 1px solid var(--border) !important;
    }
    
    pre {
        background: #0d1117 !important;
        border-radius: 12px !important;
        padding: 1.25rem !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.875rem !important;
    }
    
    /* Dataframe Styling */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--border);
    }
    
    /* Select Box */
    .stSelectbox > div > div {
        background: var(--bg-card) !important;
        border-color: var(--border) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
        font-weight: 500 !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        background: var(--gradient-1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    [data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
    }
    
    /* Success/Error Messages */
    .stSuccess {
        background: rgba(34, 197, 94, 0.1) !important;
        border: 1px solid rgba(34, 197, 94, 0.3) !important;
        border-radius: 12px !important;
        color: #22c55e !important;
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.1) !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        border-radius: 12px !important;
    }
    
    /* Info Box */
    .stAlert {
        background: rgba(99, 102, 241, 0.1) !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-color: var(--primary) transparent transparent transparent !important;
    }
    
    /* Download Button */
    .stDownloadButton > button {
        background: transparent !important;
        border: 2px solid var(--primary) !important;
        color: var(--primary) !important;
        box-shadow: none !important;
    }
    
    .stDownloadButton > button:hover {
        background: rgba(99, 102, 241, 0.1) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Section Divider */
    .section-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--border), transparent);
        margin: 2rem 0;
    }
    
    /* Tabs Styling */
    .stTabs {
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(30, 41, 59, 0.6);
        border-radius: 16px;
        padding: 6px;
        gap: 6px;
        border: 1px solid var(--border);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border-radius: 12px !important;
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        padding: 0.75rem 1.5rem !important;
        border: none !important;
        transition: all 0.3s ease !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(99, 102, 241, 0.1) !important;
        color: var(--text-primary) !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--gradient-1) !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
    }
    
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }
    
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }
    
    .stTabs [data-baseweb="tab-panel"] {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.5rem;
        margin-top: 1rem;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem 0;
        color: var(--text-secondary);
        font-size: 0.85rem;
        border-top: 1px solid var(--border);
        margin-top: 3rem;
    }
    
    .footer-brand {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    .footer-brand span {
        background: var(--gradient-1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 600;
    }
    
    /* Animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .animate-in {
        animation: fadeInUp 0.5s ease forwards;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-dark);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--border);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary);
    }
</style>
""", unsafe_allow_html=True)


# Initialize MongoDB connection
@st.cache_resource
def init_mongodb():
    try:
        # Get MongoDB URI from config or Streamlit secrets
        mongodb_uri = get_secret("MONGODB_URI")

        if not mongodb_uri:
            st.error("❌ MONGODB_URI not configured. Please set it in Streamlit Cloud Secrets (Settings → Secrets).")
            st.info("""
**How to configure:**
1. Go to your Streamlit Cloud app dashboard
2. Click **Settings** → **Secrets**
3. Add your secrets in TOML format:
```
MONGODB_URI = "mongodb+srv://user:pass@cluster0.rdt20jh.mongodb.net/?retryWrites=true&w=majority"
OPENAI_API_KEY = "sk-..."
```
4. Click **Save** and reboot the app
            """)
            return None

        # Strip any accidental whitespace/newlines from the URI
        mongodb_uri = mongodb_uri.strip()

        # Use certifi's CA bundle for SSL certificate verification.
        # This fixes SSL handshake errors on Streamlit Cloud and other platforms.
        client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=30000,
        )
        client.admin.command("ping")
        return client
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {e}")
        return None


# Get collection schema (simplified - just field names and types)
def get_collection_schema(db, collection_name):
    try:
        collection = db[collection_name]
        sample = collection.find_one()
        if sample:
            # Simplify schema to just field names and types (not full values)
            def simplify_schema(doc, max_depth=2, current_depth=0):
                if current_depth >= max_depth:
                    return "..."
                if isinstance(doc, dict):
                    result = {}
                    for key, value in list(doc.items())[:15]:  # Limit fields
                        if key == '_id':
                            result[key] = "ObjectId"
                        elif isinstance(value, dict):
                            result[key] = simplify_schema(value, max_depth, current_depth + 1)
                        elif isinstance(value, list):
                            result[key] = f"Array[{len(value)} items]"
                        elif isinstance(value, str):
                            result[key] = "String"
                        elif isinstance(value, (int, float)):
                            result[key] = "Number"
                        elif isinstance(value, bool):
                            result[key] = "Boolean"
                        elif value is None:
                            result[key] = "Null"
                        else:
                            result[key] = type(value).__name__
                    return result
                return type(doc).__name__
            return simplify_schema(sample)
        return {}
    except Exception as e:
        return {"error": str(e)}


# Get all collections and their schemas
def get_database_schema(db):
    schema = {}
    collections = db.list_collection_names()
    for coll in collections:
        schema[coll] = get_collection_schema(db, coll)
    return schema


# Cache database stats to avoid slow queries on every rerun
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_database_stats(_db, _collections):
    """Get total document count and per-collection counts (cached)"""
    collection_counts = {}
    total = 0
    for coll in _collections:
        count = _db[coll].count_documents({})
        collection_counts[coll] = count
        total += count
    return total, collection_counts


# Generate MongoDB query using AI
def generate_mongo_query(user_question, schema, ai_provider="openai", model_name="gpt-4o-mini"):
    schema_str = json.dumps(schema, indent=2, default=str)
    
    system_prompt = f"""You are a MongoDB query expert. Convert natural language to MongoDB queries.

COLLECTIONS AND FIELDS:
{schema_str}

RULES:
1. Return ONLY valid JSON: {{"collection": "name", "operation": "find|aggregate|count", "query": {{}}, "projection": {{}}, "pipeline": []}}
2. For simple queries: "operation": "find"
3. For aggregation: "operation": "aggregate" with "pipeline"
4. For counting: "operation": "count"
5. No explanations, just JSON
6. there are 4 customer collections. so in case user query is related with customer, consider all these 4 collections

EXAMPLES:
- "How many leads?" -> {{"collection": "leads", "operation": "count", "query": {{}}}}
- "Show active customers" -> {{"collection": "customers_active", "operation": "find", "query": {{}}}}
"""

    user_prompt = f"Convert to MongoDB query: {user_question}"

    try:
        if ai_provider == "openai":
            client = OpenAI(api_key=get_secret("OPENAI_API_KEY"), timeout=30.0)
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            result = response.choices[0].message.content
        else:  # Claude
            client = anthropic.Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model=model_name,
                max_tokens=500,
                messages=[
                    {"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}
                ]
            )
            result = response.content[0].text

        # Clean up the response
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()
        
        return json.loads(result)
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse AI response", "raw": result}
    except Exception as e:
        return {"error": f"API Error: {str(e)}"}


# Make query case-insensitive for string values
def make_case_insensitive(query):
    """Convert string values in query to case-insensitive regex"""
    if isinstance(query, dict):
        new_query = {}
        for key, value in query.items():
            if key.startswith("$"):
                # MongoDB operators
                if isinstance(value, list):
                    new_query[key] = [make_case_insensitive(v) for v in value]
                else:
                    new_query[key] = make_case_insensitive(value)
            elif isinstance(value, str) and not key.startswith("$"):
                # Convert string to case-insensitive regex
                import re
                new_query[key] = {"$regex": re.escape(value), "$options": "i"}
            elif isinstance(value, dict):
                new_query[key] = make_case_insensitive(value)
            else:
                new_query[key] = value
        return new_query
    return query


# Customer collection names (actual names in MongoDB)
CUSTOMER_COLLECTIONS = ["CustomerActive", "CustomersActivation", "CustomersSuspended", "CustomersTerminated"]

# Mapping of customer type keywords to specific collections
# Order matters: more specific keywords should be checked first
CUSTOMER_TYPE_KEYWORDS = {
    "active": "CustomerActive",
    "activation": "CustomersActivation",
    "suspended": "CustomersSuspended",
    "terminated": "CustomersTerminated",
}

# Collection name mapping (handles case variations)
def normalize_collection_name(name, available_collections):
    """Map collection name to actual collection (case-insensitive)"""
    name_lower = name.lower().replace(" ", "_")
    for coll in available_collections:
        if coll.lower() == name_lower:
            return coll
    # Try partial match
    for coll in available_collections:
        if name_lower in coll.lower() or coll.lower() in name_lower:
            return coll
    return name  # Return original if no match


def get_customer_collections_for_query(collection_name):
    """
    Determine which customer collection(s) to query based on the collection name.
    
    Returns:
        - List with single collection if specific type keyword is found (active, activation, suspended, terminated)
        - List of all customer collections if generic "customer" is mentioned
        - None if not a customer-related query
    
    Examples:
        - "customer_active" or "active_customer" → ["CustomerActive"]
        - "customers_activation" → ["CustomersActivation"]
        - "suspended_customers" → ["CustomersSuspended"]
        - "terminated_customer" → ["CustomersTerminated"]
        - "customer" or "customers" (generic) → all 4 collections
        - "leads" → None (not a customer query)
    """
    name_lower = collection_name.lower()
    
    # Check if this is a customer-related query
    if "customer" not in name_lower:
        return None  # Not a customer query
    
    # Check for specific customer type keywords
    # Important: Check "activation" before "active" since "activation" contains "active"
    for keyword in ["activation", "suspended", "terminated", "active"]:
        if keyword in name_lower:
            return [CUSTOMER_TYPE_KEYWORDS[keyword]]
    
    # Generic "customer" query without specific type - return all collections
    return CUSTOMER_COLLECTIONS


# Execute MongoDB query
def execute_query(db, query_obj):
    try:
        raw_collection_name = query_obj["collection"]
        available_collections = db.list_collection_names()
        collection_name = normalize_collection_name(raw_collection_name, available_collections)
        print("collection_name: ", collection_name)
        operation = query_obj.get("operation", "find")
        
        # Determine which customer collections to query (if any)
        customer_collections = get_customer_collections_for_query(raw_collection_name)
        is_customer_query = customer_collections is not None
        
        print("is_customer_query: ", is_customer_query)
        print("customer_collections: ", customer_collections)
        
        # Get franchise filter for role-based data access
        franchise_states = get_user_franchise_filter()
        print("franchise_states filter: ", franchise_states)
        
        if operation == "find":
            query = query_obj.get("query", {})
            # Make query case-insensitive
            query = make_case_insensitive(query)
            print("query: ", query)
            projection = query_obj.get("projection", None)
            print("projection: ", projection)
            all_results = []
            
            if is_customer_query:
                # Search across the determined customer collection(s)
                for coll_name in customer_collections:
                    if coll_name in db.list_collection_names():
                        # Apply franchise filter for this collection
                        filtered_query = apply_franchise_filter_to_query(query, franchise_states, coll_name)
                        print(f"filtered_query for {coll_name}: ", filtered_query)
                        
                        collection = db[coll_name]
                        cursor = collection.find(filtered_query, projection).limit(50)
                        for doc in cursor:
                            doc['_source_collection'] = coll_name
                            all_results.append(doc)
            else:
                # Apply franchise filter for single collection
                filtered_query = apply_franchise_filter_to_query(query, franchise_states, collection_name)
                print("filtered_query: ", filtered_query)
                
                # Search single collection
                collection = db[collection_name]
                cursor = collection.find(filtered_query, projection).limit(100)
                all_results = list(cursor)
                print("all_results count: ", len(all_results))
            
            # Convert ObjectId to string for display
            for doc in all_results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            return {"success": True, "data": all_results, "count": len(all_results)}
        
        elif operation == "aggregate":
            pipeline = query_obj.get("pipeline", [])
            
            all_results = []
            if is_customer_query:
                # Aggregate across the determined customer collection(s)
                for coll_name in customer_collections:
                    if coll_name in db.list_collection_names():
                        # Inject franchise filter as first $match stage
                        state_field = get_state_field_for_collection(coll_name)
                        franchise_filter = build_franchise_filter(franchise_states, state_field)
                        if franchise_filter:
                            coll_pipeline = [{"$match": franchise_filter}] + pipeline
                        else:
                            coll_pipeline = pipeline
                        
                        collection = db[coll_name]
                        cursor = collection.aggregate(coll_pipeline)
                        for doc in cursor:
                            doc['_source_collection'] = coll_name
                            all_results.append(doc)
            else:
                # Inject franchise filter as first $match stage for single collection
                state_field = get_state_field_for_collection(collection_name)
                franchise_filter = build_franchise_filter(franchise_states, state_field)
                if franchise_filter:
                    pipeline = [{"$match": franchise_filter}] + pipeline
                    print("Injected franchise filter into aggregate pipeline")
                
                collection = db[collection_name]
                cursor = collection.aggregate(pipeline)
                all_results = list(cursor)
            
            for doc in all_results:
                if '_id' in doc and not isinstance(doc['_id'], (str, int, float)):
                    doc['_id'] = str(doc['_id'])
            return {"success": True, "data": all_results, "count": len(all_results)}
        
        elif operation == "count":
            query = query_obj.get("query", {})
            query = make_case_insensitive(query)
            
            total_count = 0
            if is_customer_query:
                for coll_name in customer_collections:
                    if coll_name in db.list_collection_names():
                        # Apply franchise filter for this collection
                        filtered_query = apply_franchise_filter_to_query(query, franchise_states, coll_name)
                        collection = db[coll_name]
                        total_count += collection.count_documents(filtered_query)
            else:
                # Apply franchise filter for single collection
                filtered_query = apply_franchise_filter_to_query(query, franchise_states, collection_name)
                collection = db[collection_name]
                total_count = collection.count_documents(filtered_query)
            
            return {"success": True, "data": [{"count": total_count}], "count": 1}
        
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


# Truncate data for AI summary to prevent context length errors
def truncate_data_for_summary(data, max_records=5, max_string_length=100, max_total_chars=8000):
    """
    Truncate data to fit within AI context limits.
    - Limits number of records
    - Truncates long string values
    - Limits nested depth
    - Caps total output size
    """
    def truncate_value(value, depth=0):
        if depth > 2:  # Limit nesting depth
            return "..." if value else value
        
        if isinstance(value, str):
            if len(value) > max_string_length:
                return value[:max_string_length] + "..."
            return value
        elif isinstance(value, dict):
            # Limit to first 10 keys and truncate values
            truncated = {}
            for i, (k, v) in enumerate(value.items()):
                if i >= 10:
                    truncated["..."] = f"({len(value) - 10} more fields)"
                    break
                truncated[k] = truncate_value(v, depth + 1)
            return truncated
        elif isinstance(value, list):
            if len(value) > 3:
                return [truncate_value(v, depth + 1) for v in value[:3]] + [f"... ({len(value) - 3} more items)"]
            return [truncate_value(v, depth + 1) for v in value]
        else:
            return value
    
    # Take only first few records
    truncated_data = []
    for record in data[:max_records]:
        truncated_record = truncate_value(record)
        truncated_data.append(truncated_record)
    
    # Convert to string and check total size
    result_str = json.dumps(truncated_data, indent=2, default=str)
    
    # If still too large, truncate the string itself
    if len(result_str) > max_total_chars:
        result_str = result_str[:max_total_chars] + "\n... (data truncated for brevity)"
    
    return result_str


# Generate natural language summary of results
def generate_summary(user_question, query_obj, results, ai_provider="openai", model_name="gpt-4o-mini"):
    # Truncate results to prevent context length errors
    results_str = truncate_data_for_summary(
        results["data"], 
        max_records=5,           # Only 5 sample records
        max_string_length=100,   # Truncate long strings
        max_total_chars=8000     # Max ~2000 tokens worth of data
    )
    
    prompt = f"""Summarize these query results concisely.

Question: {user_question}
Records found: {results['count']}
Sample data (truncated): {results_str}

Provide a brief 2-3 sentence summary answering the question with key facts and numbers."""

    try:
        if ai_provider == "openai":
            client = OpenAI(api_key=get_secret("OPENAI_API_KEY"), timeout=30.0)
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            return response.choices[0].message.content
        else:  # Claude
            client = anthropic.Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model=model_name,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
    except Exception as e:
        return f"Summary generation error: {str(e)}"


# Main Application
def main():
    # Initialize session state for login
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    # Show login page if not logged in
    if not st.session_state.logged_in:
        show_login_page()
        return
    
    # Get current user
    user = st.session_state.user
    
    # Initialize MongoDB first
    mongo_client = init_mongodb()
    
    if mongo_client is None:
        st.error("⚠️ Cannot connect to MongoDB. Please ensure MongoDB is running.")
        return
    
    db = mongo_client[config.MONGODB_DATABASE]
    collections = db.list_collection_names()
    
    # Hero Header with user info
    st.markdown(f"""
    <div class="hero-container">
        <h1 class="hero-title">⚡ FMS Query Engine</h1>
        <p class="hero-subtitle">Transform natural language into powerful database insights with AI</p>
        <div class="hero-badge">System Online • MongoDB Connected • {user['role']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        # User Profile Section
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.1) 100%); 
                    border: 1px solid rgba(99, 102, 241, 0.3); 
                    border-radius: 16px; 
                    padding: 1.25rem; 
                    margin-bottom: 1.5rem;
                    text-align: center;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">{user['avatar']}</div>
            <div style="font-size: 1.1rem; font-weight: 600; color: #f1f5f9;">{user['name']}</div>
            <div style="font-size: 0.8rem; color: #a78bfa; margin-top: 0.25rem;">{user['role']}</div>
            <div style="font-size: 0.7rem; color: #64748b; margin-top: 0.25rem;">{user['email']}</div>
            {f'<div style="font-size: 0.7rem; color: #94a3b8; margin-top: 0.5rem;">🏢 {user["franchise"]}</div>' if user.get('franchise') else ''}
        </div>
        """, unsafe_allow_html=True)
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
        
        st.markdown('<div class="sidebar-header">⚙️ Configuration</div>', unsafe_allow_html=True)
        
        # AI Model Selection - 6 options (3 OpenAI + 3 Claude)
        ai_model = st.selectbox(
            "AI Model",
            [
                "OpenAI GPT-5",
                "OpenAI GPT-5-mini", 
                "OpenAI gpt-5-chat-latest",
                "OpenAI GPT-4o",
                "OpenAI GPT-4o-mini",
                "OpenAI GPT-4-turbo"
            ],
            index=1,  # Default to GPT-4o-mini (fast & cheap)
            help="Select the AI model for query generation"
        )
        
        # Map selection to provider and model
        MODEL_MAP = {
            "OpenAI GPT-5": ("openai", "gpt-5"),
            "OpenAI GPT-5-mini": ("openai", "gpt-5-mini"),
            "OpenAI gpt-5-chat-latest": ("openai", "gpt-5-chat-latest"),
            "OpenAI GPT-4o": ("openai", "gpt-4o"),
            "OpenAI GPT-4o-mini": ("openai", "gpt-4o-mini"),
            "OpenAI GPT-4-turbo": ("openai", "gPT-4-turbo")
        }
        ai_provider, model_name = MODEL_MAP[ai_model]
        
        st.markdown('<div class="sidebar-header">📊 Database</div>', unsafe_allow_html=True)
        
        # Database Stats (cached to avoid slow reloads)
        total_docs, collection_counts = get_database_stats(db, tuple(collections))
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{total_docs:,}</div>
                <div class="stat-label">Documents</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{len(collections)}</div>
                <div class="stat-label">Collections</div>
            </div>
            """, unsafe_allow_html=True)
        
        with st.expander("📁 View Collections", expanded=False):
            for coll in sorted(collections):
                count = collection_counts.get(coll, 0)
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #334155;">
                    <span style="color: #f1f5f9; font-size: 0.85rem;">{coll}</span>
                    <span style="color: #6366f1; font-weight: 600; font-size: 0.85rem;">{count:,}</span>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-header">💡 Quick Queries</div>', unsafe_allow_html=True)
        
        # Sample Questions
        sample_questions = [
            ("", "How many leads are there?"),
            ("", "Show all active customers"),
            ("", "List all service providers"),
            ("", "Count proposals by status"),
            ("", "Show customers in Cleveland"),
            ("", "What is total revenue?"),
        ]
        for icon, q in sample_questions:
            if st.button(f"{icon}  {q}", key=f"sample_{q}", use_container_width=True):
                st.session_state.question_input = q  # Use the same key as the text_area widget
                st.rerun()  # Refresh UI to show the new value
    
    # Main Content Area
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # Query Input Section
    st.markdown("""
    <div class="glass-card">
        <div class="card-title">
            <div class="card-title-icon">🔍</div>
            Ask Your Question
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    user_question = st.text_area(
        "Enter your question in plain English:",
        height=120,
        placeholder="Example: How many active customers do we have? Show me all proposals from last month...",
        key="question_input",
        label_visibility="collapsed"
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        submit_button = st.button("🚀 Execute Query", type="primary", use_container_width=True)
    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.question_input = ""  # Use the same key as the text_area widget
            st.rerun()
    
    # Process query
    if submit_button and user_question:
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Progress indicator
        progress_container = st.empty()
        
        with progress_container:
            with st.spinner("🤖 AI is analyzing your question..."):
                schema = get_database_schema(db)
                query_obj = generate_mongo_query(user_question, schema, ai_provider)
        
        if "error" in query_obj:
            st.error(f"❌ Error generating query: {query_obj['error']}")
            if "raw" in query_obj:
                st.code(query_obj["raw"], language="text")
        else:
            # Execute query first to get results
            with st.spinner("⚡ Executing query on database..."):
                results = execute_query(db, query_obj)
            
            # Generate AI insights
            summary = ""
            if results["success"]:
                with st.spinner("🧠 Generating insights..."):
                    summary = generate_summary(user_question, query_obj, results, ai_provider)
            
            # Results Header with status
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            
            if results["success"]:
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem; padding: 1rem 1.5rem; background: linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px;">
                    <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #22c55e, #10b981); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.5rem;">✓</div>
                    <div>
                        <div style="font-size: 1.25rem; font-weight: 600; color: #f1f5f9;">Query Executed Successfully</div>
                        <div style="font-size: 0.9rem; color: #94a3b8;">Found <span style="color: #22c55e; font-weight: 600;">{results['count']}</span> records in <span style="color: #6366f1; font-weight: 500;">{query_obj.get('collection', 'N/A')}</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem; padding: 1rem 1.5rem; background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(220, 38, 38, 0.05) 100%); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 12px;">
                    <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #ef4444, #dc2626); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.5rem;">✗</div>
                    <div>
                        <div style="font-size: 1.25rem; font-weight: 600; color: #f1f5f9;">Query Execution Failed</div>
                        <div style="font-size: 0.9rem; color: #fca5a5;">{results.get('error', 'Unknown error')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Create 3 tabs for organized results display (MongoDB Query first, then Results, then AI Insights)
            tab1, tab2, tab3 = st.tabs(["⚙️ MongoDB Query", "📊 Query Results", "💬 AI Insights"])
            
            # Tab 1: Generated MongoDB Query
            with tab1:
                st.markdown("""
                <div style="margin-bottom: 1rem;">
                    <h4 style="color: #f1f5f9; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
                        <span style="font-size: 1.25rem;">🔧</span> Generated MongoDB Query
                    </h4>
                    <p style="color: #94a3b8; font-size: 0.875rem; margin: 0;">AI-generated query based on your natural language input</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.code(json.dumps(query_obj, indent=2), language="json")
                
                # Query Details Cards
                st.markdown("""
                <div style="margin-top: 1.5rem; margin-bottom: 1rem;">
                    <h4 style="color: #f1f5f9; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                        <span style="font-size: 1.25rem;">📋</span> Query Parameters
                    </h4>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.08) 100%); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 12px; padding: 1rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Collection</div>
                        <div style="font-size: 1.1rem; font-weight: 600; color: #a5b4fc;">{query_obj.get("collection", "N/A")}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(14, 165, 233, 0.15) 0%, rgba(6, 182, 212, 0.08) 100%); border: 1px solid rgba(14, 165, 233, 0.3); border-radius: 12px; padding: 1rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Operation</div>
                        <div style="font-size: 1.1rem; font-weight: 600; color: #7dd3fc;">{query_obj.get("operation", "N/A")}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(34, 197, 94, 0.08) 100%); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 1rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Limit</div>
                        <div style="font-size: 1.1rem; font-weight: 600; color: #6ee7b7;">{query_obj.get("limit", "N/A")}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col4:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(251, 191, 36, 0.08) 100%); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 12px; padding: 1rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Results</div>
                        <div style="font-size: 1.1rem; font-weight: 600; color: #fcd34d;">{results.get('count', 0)}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Tab 2: Query Results
            with tab2:
                if results["success"]:
                    if results["data"]:
                        df = pd.DataFrame(results["data"])
                        # Remove internal/metadata columns from display
                        columns_to_hide = ['_id', '_importedAt', '_source', '_source_collection', 'businessLocationId', 'businessLocationDateCreated', 'customerKey']
                        df_display = df.drop(columns=[col for col in columns_to_hide if col in df.columns])
                        
                        # Results info bar
                        st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; padding: 0.75rem 1rem; background: rgba(30, 41, 59, 0.6); border-radius: 10px; border: 1px solid #334155;">
                            <div style="display: flex; align-items: center; gap: 1rem;">
                                <span style="color: #94a3b8; font-size: 0.875rem;">📊 Showing <span style="color: #f1f5f9; font-weight: 600;">{len(df_display)}</span> records</span>
                                <span style="color: #475569;">|</span>
                                <span style="color: #94a3b8; font-size: 0.875rem;">📁 <span style="color: #a5b4fc; font-weight: 500;">{len(df_display.columns)}</span> columns</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.dataframe(df_display, use_container_width=True, height=450)
                        
                        # Export section
                        st.markdown("""
                        <div style="margin-top: 1.5rem; margin-bottom: 1rem;">
                            <h4 style="color: #f1f5f9; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                                <span style="font-size: 1.25rem;">📥</span> Export Data
                            </h4>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col_a, col_b, col_c = st.columns([1, 1, 2])
                        with col_a:
                            csv = df_display.to_csv(index=False)
                            st.download_button(
                                label="📄 Download CSV",
                                data=csv,
                                file_name=f"fms_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        with col_b:
                            json_str = df_display.to_json(orient='records', indent=2)
                            st.download_button(
                                label="📋 Download JSON",
                                data=json_str,
                                file_name=f"fms_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                    else:
                        st.markdown("""
                        <div style="text-align: center; padding: 3rem 2rem; background: rgba(30, 41, 59, 0.5); border-radius: 12px; border: 1px dashed #475569;">
                            <div style="font-size: 3rem; margin-bottom: 1rem;">📭</div>
                            <div style="font-size: 1.1rem; color: #f1f5f9; font-weight: 500; margin-bottom: 0.5rem;">No Data Found</div>
                            <div style="font-size: 0.875rem; color: #94a3b8;">The query executed successfully but returned no results.</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.error(f"❌ Query execution failed: {results['error']}")
            
            # Tab 3: AI Insights
            with tab3:
                if results["success"]:
                    st.markdown("""
                    <div style="margin-bottom: 1rem;">
                        <h4 style="color: #f1f5f9; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.25rem;">🧠</span> AI Analysis & Insights
                        </h4>
                        <p style="color: #94a3b8; font-size: 0.875rem; margin: 0;">Intelligent summary generated by AI based on your query results</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.04) 100%); border: 1px solid rgba(99, 102, 241, 0.2); border-left: 4px solid #6366f1; border-radius: 12px; padding: 1.5rem; color: #f1f5f9; font-size: 1rem; line-height: 1.8;">
                        {summary}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Quick stats from AI
                    st.markdown("""
                    <div style="margin-top: 1.5rem; padding: 1rem; background: rgba(30, 41, 59, 0.5); border-radius: 10px; border: 1px solid #334155;">
                        <div style="display: flex; align-items: center; gap: 0.5rem; color: #94a3b8; font-size: 0.8rem;">
                            <span>💡</span>
                            <span>AI insights are generated based on the query results and may provide additional context and analysis.</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="text-align: center; padding: 3rem 2rem; background: rgba(30, 41, 59, 0.5); border-radius: 12px; border: 1px dashed #475569;">
                        <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
                        <div style="font-size: 1.1rem; color: #f1f5f9; font-weight: 500; margin-bottom: 0.5rem;">Insights Unavailable</div>
                        <div style="font-size: 0.875rem; color: #94a3b8;">AI insights cannot be generated due to query execution error.</div>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div class="footer">
        <div class="footer-brand">
            <span>⚡ FMS Query Engine</span>
        </div>
        <div>Powered by OpenAI GPT-4 & Anthropic Claude • MongoDB Backend</div>
        <div style="margin-top: 0.5rem; font-size: 0.75rem; color: #475
        569;">
            © 2025 Enterprise Analytics Suite • Version 2.0
        </div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

