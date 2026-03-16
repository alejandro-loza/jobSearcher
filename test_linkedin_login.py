import os
from dotenv import load_dotenv
from linkedin_api import Linkedin

# Load environment variables
load_dotenv('.env')

email = os.environ.get('LINKEDIN_EMAIL')
password = os.environ.get('LINKEDIN_PASSWORD')

if not email or not password:
    print("Error: Credentials not found in .env")
    exit(1)

try:
    print(f"Attempting login for {email}...")
    # Attempt authentication
    api = Linkedin(email, password, authenticate=True)
    
    # Try a simple API call to verify it works
    profile = api.get_user_profile()
    print("SUCCESS: Login successful!")
    print(f"Profile: {profile.get('summary', 'Found profile')}")
    
except Exception as e:
    print(f"FAILED: Login failed. Error: {str(e)}")
