#!/usr/bin/env python
"""
Test script to verify that profile views work correctly
"""
import os
import sys
import django

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User
from Login.models import Profile
from Login.views import get_or_create_user_profile

def test_profile_creation():
    """Test the profile creation functionality"""
    print("Testing profile creation...")
    
    # Test with existing admin user
    try:
        admin_user = User.objects.get(username='admin')
        profile = get_or_create_user_profile(admin_user)
        print(f"✅ Profile for admin user: {profile.full_name} ({profile.user_status})")
    except User.DoesNotExist:
        print("❌ Admin user not found")
    
    # Check all users have profiles
    users_without_profile = User.objects.filter(profile__isnull=True)
    if users_without_profile.count() == 0:
        print("✅ All users have profiles")
    else:
        print(f"⚠️  {users_without_profile.count()} users without profiles:")
        for user in users_without_profile:
            print(f"   - {user.username}")
    
    print("\nProfile creation test completed!")

if __name__ == "__main__":
    test_profile_creation()