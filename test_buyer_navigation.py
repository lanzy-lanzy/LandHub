#!/usr/bin/env python
"""
Test script to verify buyer navigation links are working properly.
Run this script to test all buyer dashboard navigation functionality.
"""

import os
import sys

# Setup Django before importing Django modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LandHub.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse

from landmarket.models import UserProfile, Land, Favorite, SavedSearch, Inquiry

def create_test_buyer():
    """Create a test buyer user"""
    try:
        user = User.objects.get(username='test_buyer')
        print("✓ Using existing test buyer")
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='test_buyer',
            email='buyer@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Buyer'
        )
        profile = UserProfile.objects.create(
            user=user,
            role='buyer',
            phone='+1234567890',
            bio='Test buyer for navigation testing'
        )
        print("✓ Created test buyer user")
    
    return user

def test_buyer_navigation():
    """Test all buyer navigation links"""
    print("\n🧪 Testing Buyer Navigation Links")
    print("=" * 50)
    
    # Create test buyer
    user = create_test_buyer()
    
    # Create client and login
    client = Client()
    login_success = client.login(username='test_buyer', password='testpass123')
    
    if not login_success:
        print("❌ Failed to login test buyer")
        return False
    
    print("✓ Logged in as test buyer")
    
    # Test URLs to check
    test_urls = [
        ('dashboard', 'Buyer Dashboard'),
        ('buyer_browse_listings', 'Browse Listings'),
        ('buyer_favorites', 'Favorites'),
        ('buyer_saved_searches', 'Saved Searches'),
        ('buyer_create_saved_search', 'Create Saved Search'),
        ('buyer_inquiries', 'My Inquiries'),
        ('buyer_profile', 'Profile'),
    ]
    
    results = []
    
    for url_name, description in test_urls:
        try:
            url = reverse(url_name)
            response = client.get(url)
            
            if response.status_code == 200:
                print(f"✓ {description}: {url} - OK")
                results.append(True)
            elif response.status_code == 302:
                print(f"⚠ {description}: {url} - Redirect (might be expected)")
                results.append(True)
            else:
                print(f"❌ {description}: {url} - Status {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"❌ {description}: Error - {str(e)}")
            results.append(False)
    
    # Test API endpoints
    api_urls = [
        ('buyer_api_dashboard_stats', 'Dashboard Stats API'),
    ]
    
    for url_name, description in api_urls:
        try:
            url = reverse(url_name)
            response = client.get(url)
            
            if response.status_code == 200:
                print(f"✓ {description}: {url} - OK")
                results.append(True)
            else:
                print(f"❌ {description}: {url} - Status {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"❌ {description}: Error - {str(e)}")
            results.append(False)
    
    # Summary
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n📊 Test Results: {success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        print("🎉 All buyer navigation links are working!")
        return True
    else:
        print("⚠️  Some buyer navigation links have issues")
        return False

def test_sidebar_navigation():
    """Test that sidebar navigation is properly configured"""
    print("\n🔍 Testing Sidebar Navigation Configuration")
    print("=" * 50)
    
    # Check if sidebar template exists and has buyer navigation
    sidebar_path = 'templates/components/sidebar.html'
    
    if os.path.exists(sidebar_path):
        print("✓ Sidebar template exists")
        
        with open(sidebar_path, 'r') as f:
            content = f.read()
            
        # Check for buyer navigation URLs
        buyer_urls = [
            'buyer_browse_listings',
            'buyer_favorites', 
            'buyer_saved_searches',
            'buyer_inquiries',
            'buyer_profile'
        ]
        
        missing_urls = []
        for url in buyer_urls:
            if url in content:
                print(f"✓ Found {url} in sidebar")
            else:
                print(f"❌ Missing {url} in sidebar")
                missing_urls.append(url)
        
        if not missing_urls:
            print("🎉 All buyer URLs found in sidebar!")
            return True
        else:
            print(f"⚠️  Missing URLs in sidebar: {missing_urls}")
            return False
    else:
        print("❌ Sidebar template not found")
        return False

if __name__ == '__main__':
    print("🚀 Starting Buyer Navigation Tests")
    
    # Test navigation functionality
    nav_success = test_buyer_navigation()
    
    # Test sidebar configuration
    sidebar_success = test_sidebar_navigation()
    
    print("\n" + "=" * 50)
    if nav_success and sidebar_success:
        print("✅ ALL TESTS PASSED - Buyer navigation is working correctly!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Please check the issues above")
        sys.exit(1)
