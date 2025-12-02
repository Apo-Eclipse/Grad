import sys
import os
sys.path.insert(0, r'd:\Grad Project\Multi-Agent System\Grad\api')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_config.settings')

# Force Django setup
import django
django.setup()

print("Django setup complete!")

try:
    print("Importing api_config.urls...")
    from api_config import urls
    print("SUCCESS! URLs imported successfully!")
    print(f"API object: {urls.api}")
    print("\nAll routers registered:")
    for route in urls.api._routers:
        print(f"  - {route}")

    print("\nSimulating request to /api/docs...")
    from django.test import Client
    client = Client()
    response = client.get('/api/docs')
    print(f"Response status: {response.status_code}")
    if response.status_code != 200:
        print(f"Response content: {response.content.decode('utf-8')}")
        
except Exception as e:
    print(f"ERROR: {e}")
    print("\nFull traceback:")
    import traceback
    traceback.print_exc()
