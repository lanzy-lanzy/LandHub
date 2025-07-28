#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LandHub.settings')
django.setup()

from django.contrib.auth.models import User
from landmarket.models import UserProfile

print("=== Fixing Test User Roles ===")

# Fix admin_test
try:
    admin_user = User.objects.get(username='admin_test')
    admin_user.profile.role = 'admin'
    admin_user.profile.save()
    print(f"✅ Fixed admin_test role to 'admin'")
except User.DoesNotExist:
    print("❌ admin_test user not found")

# Fix seller_test
try:
    seller_user = User.objects.get(username='seller_test')
    seller_user.profile.role = 'seller'
    seller_user.profile.save()
    print(f"✅ Fixed seller_test role to 'seller'")
except User.DoesNotExist:
    print("❌ seller_test user not found")

# Fix buyer_test
try:
    buyer_user = User.objects.get(username='buyer_test')
    buyer_user.profile.role = 'buyer'
    buyer_user.profile.save()
    print(f"✅ Fixed buyer_test role to 'buyer'")
except User.DoesNotExist:
    print("❌ buyer_test user not found")

print("\n=== Final Test User Status ===")
for username in ['admin_test', 'seller_test', 'buyer_test']:
    try:
        user = User.objects.get(username=username)
        print(f"{user.username}: {user.profile.role}")
    except User.DoesNotExist:
        print(f"{username}: Not found")
