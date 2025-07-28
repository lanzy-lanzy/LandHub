#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LandHub.settings')
django.setup()

from django.contrib.auth.models import User
from landmarket.models import UserProfile

print("=== Checking User Profiles ===")

# Check all users
for user in User.objects.all():
    print(f"\nUser: {user.username}")
    try:
        profile = user.profile
        print(f"  Profile role: {profile.role}")
    except UserProfile.DoesNotExist:
        print(f"  No profile found - creating one...")
        # Create missing profile based on username
        if 'admin' in user.username:
            role = 'admin'
        elif 'seller' in user.username:
            role = 'seller'
        elif 'buyer' in user.username:
            role = 'buyer'
        else:
            role = 'buyer'  # default
        
        profile = UserProfile.objects.create(
            user=user,
            role=role,
            phone=f'+1-555-{user.id:04d}',
            bio=f'Auto-created profile for {role} user.'
        )
        print(f"  Created profile with role: {role}")

print("\n=== Final User Status ===")
for user in User.objects.all():
    print(f"{user.username}: {user.profile.role}")
