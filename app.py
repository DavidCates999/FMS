import streamlit as st
import json
from pymongo import MongoClient
from openai import OpenAI
import anthropic
import pandas as pd
from datetime import datetime
import certifi
import config


def get_secret(key, default=None):
    """Get secret from environment variables or Streamlit secrets"""
    # First try config (environment variables)
    value = getattr(config, key, None)
    if value:
        return value
    # Then try Streamlit secrets
    try:
        return st.secrets.get(key, default)
    except (KeyError, FileNotFoundError):
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
        mongodb_uri = config.MONGODB_URI
        
        # Try Streamlit secrets if env var not set
        if not mongodb_uri:
            try:
                mongodb_uri = st.secrets["MONGODB_URI"]
            except (KeyError, FileNotFoundError):
                mongodb_uri = None
        
        if not mongodb_uri:
            st.error("❌ MONGODB_URI not configured. Please set it in environment variables or Streamlit secrets.")
            return None
        
        # Use certifi's CA bundle for SSL certificate verification
        # This fixes SSL handshake errors on Streamlit Cloud and other platforms
        client = MongoClient(
            mongodb_uri,
            tlsCAFile=certifi.where()
        )
        client.admin.command('ping')
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


# Execute MongoDB query
def execute_query(db, query_obj):
    try:
        raw_collection_name = query_obj["collection"]
        available_collections = db.list_collection_names()
        collection_name = normalize_collection_name(raw_collection_name, available_collections)
        print("collection_name: ", collection_name)
        operation = query_obj.get("operation", "find")
        
        # Check if this is a customer-related query that should search all customer collections
        is_customer_query = "customer" in raw_collection_name.lower()
        
        if operation == "find":
            query = query_obj.get("query", {})
            # Make query case-insensitive
            query = make_case_insensitive(query)
            print("query: ", query)
            projection = query_obj.get("projection", None)
            print("projection: ", projection)
            all_results = []
            
            if is_customer_query:
                # Search across all customer collections
                for coll_name in CUSTOMER_COLLECTIONS:
                    if coll_name in db.list_collection_names():
                        collection = db[coll_name]
                        cursor = collection.find(query, projection).limit(50)
                        for doc in cursor:
                            doc['_source_collection'] = coll_name
                            all_results.append(doc)
            else:
                # Search single collection
                collection = db[collection_name]
                cursor = collection.find(query, projection).limit(100)
                all_results = list(cursor)
                print("all_results: ", all_results)
            
            # Convert ObjectId to string for display
            for doc in all_results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            return {"success": True, "data": all_results, "count": len(all_results)}
        
        elif operation == "aggregate":
            pipeline = query_obj.get("pipeline", [])
            
            all_results = []
            if is_customer_query:
                # Aggregate across all customer collections
                for coll_name in CUSTOMER_COLLECTIONS:
                    if coll_name in db.list_collection_names():
                        collection = db[coll_name]
                        cursor = collection.aggregate(pipeline)
                        for doc in cursor:
                            doc['_source_collection'] = coll_name
                            all_results.append(doc)
            else:
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
                for coll_name in CUSTOMER_COLLECTIONS:
                    if coll_name in db.list_collection_names():
                        collection = db[coll_name]
                        total_count += collection.count_documents(query)
            else:
                collection = db[collection_name]
                total_count = collection.count_documents(query)
            
            return {"success": True, "data": [{"count": total_count}], "count": 1}
        
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


# Generate natural language summary of results
def generate_summary(user_question, query_obj, results, ai_provider="openai", model_name="gpt-4o-mini"):
    # Limit results for summary
    sample_data = results["data"][:10]
    results_str = json.dumps(sample_data, indent=2, default=str)
    
    prompt = f"""Summarize these query results concisely.

Question: {user_question}
Records found: {results['count']}
Sample data: {results_str}

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
    # Initialize MongoDB first
    mongo_client = init_mongodb()
    
    if mongo_client is None:
        st.error("⚠️ Cannot connect to MongoDB. Please ensure MongoDB is running.")
        return
    
    db = mongo_client[config.MONGODB_DATABASE]
    collections = db.list_collection_names()
    
    # Hero Header
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">⚡ FMS Query Engine</h1>
        <p class="hero-subtitle">Transform natural language into powerful database insights with AI</p>
        <div class="hero-badge">System Online • MongoDB Connected</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        # Logo/Brand
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0 1.5rem 0;">
            <div style="font-size: 2rem; margin-bottom: 0.25rem;">⚡</div>
            <div style="font-size: 1.1rem; font-weight: 600; color: #f1f5f9;">FMS Query</div>
            <div style="font-size: 0.75rem; color: #64748b;">Enterprise Analytics</div>
        </div>
        """, unsafe_allow_html=True)
        
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
        
        # Database Stats
        total_docs = sum(db[c].count_documents({}) for c in collections)
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
                count = db[coll].count_documents({})
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
                st.session_state.user_question = q
    
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
        value=st.session_state.get("user_question", ""),
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
            st.session_state.user_question = ""
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
            # Generated Query Display
            st.markdown("""
            <div class="glass-card">
                <div class="card-title">
                    <div class="card-title-icon">⚙️</div>
                    Generated MongoDB Query
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.code(json.dumps(query_obj, indent=2), language="json")
            
            # Execute query
            with st.spinner("⚡ Executing query on database..."):
                results = execute_query(db, query_obj)
            
            if results["success"]:
                st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
                
                # Results section - Two columns
                result_col1, result_col2 = st.columns([1.2, 1])
                
                with result_col1:
                    st.markdown("""
                    <div class="glass-card">
                        <div class="card-title">
                            <div class="card-title-icon">📊</div>
                            Query Results
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.success(f"✅ Found **{results['count']}** records")
                    
                    if results["data"]:
                        df = pd.DataFrame(results["data"])
                        st.dataframe(df, use_container_width=True, height=400)
                        
                        # Download buttons
                        col_a, col_b = st.columns(2)
                        with col_a:
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="📥 Download CSV",
                                data=csv,
                                file_name=f"fms_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        with col_b:
                            json_str = df.to_json(orient='records', indent=2)
                            st.download_button(
                                label="📥 Download JSON",
                                data=json_str,
                                file_name=f"fms_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                
                with result_col2:
                    st.markdown("""
                    <div class="glass-card">
                        <div class="card-title">
                            <div class="card-title-icon">💬</div>
                            AI Insights
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.spinner("🧠 Generating insights..."):
                        summary = generate_summary(user_question, query_obj, results, ai_provider)
                    
                    st.markdown(f"""
                    <div class="result-box">
                        {summary}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error(f"❌ Query execution failed: {results['error']}")
    
    # Footer
    st.markdown("""
    <div class="footer">
        <div class="footer-brand">
            <span>⚡ FMS Query Engine</span>
        </div>
        <div>Powered by OpenAI GPT-4 & Anthropic Claude • MongoDB Backend</div>
        <div style="margin-top: 0.5rem; font-size: 0.75rem; color: #475569;">
            © 2025 Enterprise Analytics Suite • Version 2.0
        </div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

