# Configuration file for FMS Query Engine
# Loads sensitive data from environment variables

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys (loaded from .env)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# MongoDB Configuration (loaded from .env or Streamlit secrets)
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "FMS")

# Available Collections (populated from your data)
COLLECTIONS = [
    "leads",
    "proposals", 
    "ServiceContracts",
    "rfps",
    "customers_activation",
    "customers_active",
    "customers_suspended",
    "customers_terminated",
    "serviceproviders",
    "spusers",
    "inspection_dashboard",
    "UsersInspection",
    "GeneralLedger"
]
