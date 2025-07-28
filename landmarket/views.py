from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.models import User
from django.db.models import Count, Q, Avg
from django.db import models
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Land, UserProfile, Inquiry, LandImage, Favorite, SavedSearch
from .forms import (
    LandListingForm, LandImageFormSet, InquiryResponseForm, UserProfileForm, ListingSearchForm,
    PropertySearchForm, SavedSearchForm, BuyerInquiryForm, BuyerProfileForm
)


def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Set user role based on URL parameter
            role = request.GET.get('role', 'buyer')
            if role in ['admin', 'seller', 'buyer']:
                user.profile.role = role
                user.profile.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()

    context = {
        'form': form,
        'role': request.GET.get('role', 'buyer')
    }
    return render(request, 'auth/register.html', context)


def landing(request):
    """Landing page view with real database statistics"""
    # Get featured listings
    featured_listings = Land.objects.filter(
        status='approved',
        is_approved=True
    ).select_related('owner').prefetch_related('images').order_by('-created_at')[:6]

    # Calculate real statistics
    total_listings = Land.objects.filter(status='approved', is_approved=True).count()
    total_buyers = UserProfile.objects.filter(role='buyer').count()
    total_sellers = UserProfile.objects.filter(role='seller').count()

    # Property type counts
    property_type_counts = Land.objects.filter(
        status='approved',
        is_approved=True
    ).values('property_type').annotate(count=Count('id'))

    # Convert to dictionary for easy template access
    property_counts = {item['property_type']: item['count'] for item in property_type_counts}

    # Calculate states covered (assuming location contains state info)
    # This is a simplified calculation - you might want to add a separate state field
    states_covered = Land.objects.filter(
        status='approved',
        is_approved=True
    ).values_list('location', flat=True).distinct().count()

    # Limit states to a reasonable number (many locations might be cities, not states)
    states_covered = min(states_covered, 50)  # Cap at 50 for realism

    context = {
        'featured_listings': featured_listings,
        'total_listings': total_listings,
        'total_buyers': total_buyers,
        'total_sellers': total_sellers,
        'states_covered': states_covered,
        'property_counts': property_counts,
        # Individual property type counts with fallbacks
        'residential_count': property_counts.get('residential', 0),
        'commercial_count': property_counts.get('commercial', 0),
        'agricultural_count': property_counts.get('agricultural', 0),
        'recreational_count': property_counts.get('recreational', 0),
    }
    return render(request, 'landing.html', context)


@login_required
def dashboard(request):
    """Role-based dashboard redirect"""
    user_role = request.user.profile.role

    if user_role == 'admin':
        return admin_dashboard(request)
    elif user_role == 'seller':
        return seller_dashboard(request)
    elif user_role == 'buyer':
        return buyer_dashboard(request)
    else:
        return render(request, 'landing.html')


@login_required
def admin_dashboard(request):
    """Admin dashboard view with comprehensive analytics"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return redirect('landing')

    # Calculate date ranges for analytics
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)

    # User statistics
    total_users = User.objects.count()
    buyer_count = UserProfile.objects.filter(role='buyer').count()
    seller_count = UserProfile.objects.filter(role='seller').count()
    admin_count = UserProfile.objects.filter(role='admin').count()
    daily_new_users = User.objects.filter(date_joined__date=today).count()

    # Listing statistics
    total_listings = Land.objects.count()
    pending_listings = Land.objects.filter(status='pending').count()
    approved_listings = Land.objects.filter(status='approved', is_approved=True).count()
    draft_listings = Land.objects.filter(status='draft').count()
    rejected_listings = Land.objects.filter(status='rejected').count()
    daily_new_listings = Land.objects.filter(created_at__date=today).count()

    # Inquiry statistics
    total_inquiries = Inquiry.objects.count()
    monthly_inquiries = Inquiry.objects.filter(created_at__date__gte=thirty_days_ago).count()
    daily_inquiries = Inquiry.objects.filter(created_at__date=today).count()

    # Recent pending listings for quick review
    recent_pending_listings = Land.objects.filter(
        status='pending'
    ).select_related('owner').order_by('-created_at')[:5]

    # Property type distribution
    property_type_stats = Land.objects.filter(
        status='approved', is_approved=True
    ).values('property_type').annotate(count=Count('id'))

    # Calculate percentages for property types
    total_approved = approved_listings
    property_distribution = {}
    for stat in property_type_stats:
        property_distribution[stat['property_type']] = {
            'count': stat['count'],
            'percentage': round((stat['count'] / total_approved * 100) if total_approved > 0 else 0, 1)
        }

    context = {
        # User metrics
        'total_users': total_users,
        'buyer_count': buyer_count,
        'seller_count': seller_count,
        'admin_count': admin_count,
        'daily_new_users': daily_new_users,

        # Listing metrics
        'total_listings': total_listings,
        'pending_listings': pending_listings,
        'approved_listings': approved_listings,
        'draft_listings': draft_listings,
        'rejected_listings': rejected_listings,
        'daily_new_listings': daily_new_listings,

        # Inquiry metrics
        'total_inquiries': total_inquiries,
        'monthly_inquiries': monthly_inquiries,
        'daily_inquiries': daily_inquiries,

        # Additional data
        'recent_pending_listings': recent_pending_listings,
        'property_distribution': property_distribution,
        'daily_page_views': 1250,  # This would come from analytics service
    }

    return render(request, 'dashboards/admin.html', context)


# ============================================================================
# ADMIN MANAGEMENT VIEWS
# ============================================================================

@login_required
def admin_user_management(request):
    """Admin view for managing users"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return redirect('landing')

    # Get all users with their profiles
    users = User.objects.select_related('profile').order_by('-date_joined')

    # Filter by role if requested
    role_filter = request.GET.get('role')
    if role_filter and role_filter in ['buyer', 'seller', 'admin']:
        users = users.filter(profile__role=role_filter)

    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(users, 20)  # Show 20 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    total_users = User.objects.count()
    buyer_count = UserProfile.objects.filter(role='buyer').count()
    seller_count = UserProfile.objects.filter(role='seller').count()
    admin_count = UserProfile.objects.filter(role='admin').count()

    context = {
        'users': page_obj,
        'total_users': total_users,
        'buyer_count': buyer_count,
        'seller_count': seller_count,
        'admin_count': admin_count,
        'role_filter': role_filter,
        'search_query': search_query,
    }
    return render(request, 'admin/user_management.html', context)


@login_required
def admin_listing_management(request):
    """Admin view for managing property listings"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return redirect('landing')

    # Get all listings
    listings = Land.objects.select_related('owner').prefetch_related('images').order_by('-created_at')

    # Filter by status if requested
    status_filter = request.GET.get('status')
    if status_filter:
        listings = listings.filter(status=status_filter)

    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        listings = listings.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(owner__username__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(listings, 15)  # Show 15 listings per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    total_listings = Land.objects.count()
    pending_listings = Land.objects.filter(status='pending').count()
    approved_listings = Land.objects.filter(status='approved', is_approved=True).count()
    rejected_listings = Land.objects.filter(status='rejected').count()
    draft_listings = Land.objects.filter(status='draft').count()

    context = {
        'listings': page_obj,
        'total_listings': total_listings,
        'pending_listings': pending_listings,
        'approved_listings': approved_listings,
        'rejected_listings': rejected_listings,
        'draft_listings': draft_listings,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'admin/listing_management.html', context)


@login_required
def admin_listing_detail(request, listing_id):
    """Admin view for detailed listing review and approval"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return redirect('landing')

    listing = get_object_or_404(
        Land.objects.select_related('owner').prefetch_related('images'),
        id=listing_id
    )

    # Handle approval/rejection
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            listing.status = 'approved'
            listing.is_approved = True
            listing.save()
            messages.success(request, f'Listing "{listing.title}" has been approved.')
        elif action == 'reject':
            listing.status = 'rejected'
            listing.is_approved = False
            listing.save()
            messages.success(request, f'Listing "{listing.title}" has been rejected.')

        return redirect('admin_listing_detail', listing_id=listing.id)

    context = {
        'listing': listing,
    }
    return render(request, 'admin/listing_detail.html', context)


@login_required
def admin_analytics(request):
    """Admin analytics and reporting view"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return redirect('landing')

    # Calculate date ranges
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)

    # User analytics
    total_users = User.objects.count()
    new_users_30d = User.objects.filter(date_joined__date__gte=thirty_days_ago).count()
    new_users_7d = User.objects.filter(date_joined__date__gte=seven_days_ago).count()

    # Listing analytics
    total_listings = Land.objects.count()
    new_listings_30d = Land.objects.filter(created_at__date__gte=thirty_days_ago).count()
    approved_listings = Land.objects.filter(status='approved', is_approved=True).count()

    # Inquiry analytics
    total_inquiries = Inquiry.objects.count()
    new_inquiries_30d = Inquiry.objects.filter(created_at__date__gte=thirty_days_ago).count()

    # Property type distribution
    property_type_stats = Land.objects.filter(
        status='approved', is_approved=True
    ).values('property_type').annotate(count=Count('id')).order_by('-count')

    # Monthly user registration trend (last 6 months)
    user_trend_data = []
    for i in range(6):
        month_start = today.replace(day=1) - timedelta(days=i*30)
        month_end = month_start + timedelta(days=30)
        count = User.objects.filter(
            date_joined__date__gte=month_start,
            date_joined__date__lt=month_end
        ).count()
        user_trend_data.append({
            'month': month_start.strftime('%b %Y'),
            'count': count
        })
    user_trend_data.reverse()

    context = {
        'total_users': total_users,
        'new_users_30d': new_users_30d,
        'new_users_7d': new_users_7d,
        'total_listings': total_listings,
        'new_listings_30d': new_listings_30d,
        'approved_listings': approved_listings,
        'total_inquiries': total_inquiries,
        'new_inquiries_30d': new_inquiries_30d,
        'property_type_stats': property_type_stats,
        'user_trend_data': user_trend_data,
    }
    return render(request, 'admin/analytics.html', context)


@login_required
def admin_settings(request):
    """Admin system settings view"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return redirect('landing')

    # This would typically load system settings from a settings model
    # For now, we'll show some basic system information

    # System statistics
    total_users = User.objects.count()
    total_listings = Land.objects.count()
    total_inquiries = Inquiry.objects.count()

    # Recent activity
    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_listings = Land.objects.select_related('owner').order_by('-created_at')[:5]

    context = {
        'total_users': total_users,
        'total_listings': total_listings,
        'total_inquiries': total_inquiries,
        'recent_users': recent_users,
        'recent_listings': recent_listings,
    }
    return render(request, 'admin/settings.html', context)


@login_required
def admin_profile(request):
    """Admin profile management view"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return redirect('landing')

    if request.method == 'POST':
        # Use the existing UserProfileForm for admin profile management
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('admin_profile')
    else:
        form = UserProfileForm(instance=request.user.profile, user=request.user)

    # Admin statistics for profile display
    managed_users = User.objects.count()
    managed_listings = Land.objects.count()
    pending_approvals = Land.objects.filter(status='pending').count()

    context = {
        'form': form,
        'managed_users': managed_users,
        'managed_listings': managed_listings,
        'pending_approvals': pending_approvals,
    }
    return render(request, 'admin/profile.html', context)


@login_required
def admin_api_dashboard_stats(request):
    """HTMX endpoint for refreshing admin dashboard statistics"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    # Calculate fresh statistics
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)

    # User statistics
    total_users = User.objects.count()
    buyer_count = UserProfile.objects.filter(role='buyer').count()
    seller_count = UserProfile.objects.filter(role='seller').count()
    daily_new_users = User.objects.filter(date_joined__date=today).count()

    # Listing statistics
    total_listings = Land.objects.count()
    pending_listings = Land.objects.filter(status='pending').count()
    approved_listings = Land.objects.filter(status='approved', is_approved=True).count()
    daily_new_listings = Land.objects.filter(created_at__date=today).count()

    # Inquiry statistics
    total_inquiries = Inquiry.objects.count()
    monthly_inquiries = Inquiry.objects.filter(created_at__date__gte=thirty_days_ago).count()
    daily_inquiries = Inquiry.objects.filter(created_at__date=today).count()

    context = {
        'total_users': total_users,
        'buyer_count': buyer_count,
        'seller_count': seller_count,
        'daily_new_users': daily_new_users,
        'total_listings': total_listings,
        'pending_listings': pending_listings,
        'approved_listings': approved_listings,
        'daily_new_listings': daily_new_listings,
        'total_inquiries': total_inquiries,
        'monthly_inquiries': monthly_inquiries,
        'daily_inquiries': daily_inquiries,
    }
    return render(request, 'components/admin_dashboard_stats.html', context)


def test_modal(request):
    """Test page for authentication modal functionality"""
    return render(request, 'test_modal.html')


@login_required
def seller_dashboard(request):
    """Seller dashboard view with comprehensive seller analytics"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'seller':
        return redirect('landing')

    # Calculate date ranges for analytics
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)

    # Get user's listings
    user_listings = Land.objects.filter(owner=request.user)

    # Listing statistics
    total_listings = user_listings.count()
    active_listings = user_listings.filter(status='approved').count()
    draft_listings = user_listings.filter(status='draft').count()
    pending_listings = user_listings.filter(status='pending').count()

    # Calculate views (mock data for now - would come from analytics system)
    total_views = total_listings * 45  # Mock calculation
    monthly_views = total_listings * 15  # Mock calculation
    daily_views = 8  # Mock data

    # Calculate inquiries (mock data - would come from inquiry system)
    total_inquiries = total_listings * 3  # Mock calculation
    pending_inquiries = 2  # Mock data
    daily_inquiries = 1  # Mock data
    response_rate = 85  # Mock percentage

    # Calculate pricing statistics
    if user_listings.exists():
        prices = [listing.price for listing in user_listings if listing.price]
        average_price = sum(prices) / len(prices) if prices else 0

        # Calculate price per acre
        total_acres = sum([listing.size_acres for listing in user_listings if listing.size_acres])
        price_per_acre = average_price / (total_acres / total_listings) if total_acres > 0 else 0
    else:
        average_price = 0
        price_per_acre = 0

    # Mock data for additional metrics
    daily_profile_views = 12

    context = {
        'user_listings': user_listings,
        'total_listings': total_listings,
        'active_listings': active_listings,
        'draft_listings': draft_listings,
        'pending_listings': pending_listings,
        'total_views': total_views,
        'monthly_views': monthly_views,
        'daily_views': daily_views,
        'total_inquiries': total_inquiries,
        'pending_inquiries': pending_inquiries,
        'daily_inquiries': daily_inquiries,
        'response_rate': response_rate,
        'average_price': average_price,
        'price_per_acre': price_per_acre,
        'daily_profile_views': daily_profile_views,
    }
    return render(request, 'dashboards/seller.html', context)


@login_required
def buyer_dashboard(request):
    """Buyer dashboard view with comprehensive buyer analytics"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return redirect('landing')

    # Calculate date ranges for analytics
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)

    # Saved searches statistics
    saved_searches = request.user.saved_searches.all()
    total_saved_searches = saved_searches.count()
    active_searches = saved_searches.filter(email_alerts=True).count()
    recent_searches = saved_searches.filter(created_at__date__gte=seven_days_ago).count()

    # Favorite properties statistics
    favorites = request.user.favorites.select_related('land').all()
    total_favorites = favorites.count()
    recent_favorites = favorites.filter(created_at__date__gte=seven_days_ago).count()

    # Calculate average price of favorite properties
    favorite_prices = [fav.land.price for fav in favorites if fav.land.price]
    avg_favorite_price = sum(favorite_prices) / len(favorite_prices) if favorite_prices else 0

    # Inquiries statistics
    inquiries = request.user.inquiries_sent.select_related('land').all()
    total_inquiries = inquiries.count()
    pending_responses = inquiries.filter(seller_response='').count()
    responded_inquiries = inquiries.exclude(seller_response='').count()
    response_rate = round((responded_inquiries / total_inquiries * 100) if total_inquiries > 0 else 0, 1)
    recent_inquiries = inquiries.filter(created_at__date__gte=seven_days_ago).count()

    # Mock property viewing data (would come from analytics system)
    total_properties_viewed = total_inquiries * 8 + total_favorites * 3 + 25  # Mock calculation
    monthly_views = total_properties_viewed // 3  # Mock calculation
    weekly_views = monthly_views // 4  # Mock calculation

    # Property type preferences based on favorites and inquiries
    favorite_property_types = {}
    inquiry_property_types = {}

    for fav in favorites:
        prop_type = fav.land.property_type
        favorite_property_types[prop_type] = favorite_property_types.get(prop_type, 0) + 1

    for inquiry in inquiries:
        prop_type = inquiry.land.property_type
        inquiry_property_types[prop_type] = inquiry_property_types.get(prop_type, 0) + 1

    # Combine and calculate preferences
    all_interactions = total_favorites + total_inquiries
    property_preferences = {}
    for prop_type in ['agricultural', 'residential', 'recreational', 'commercial']:
        fav_count = favorite_property_types.get(prop_type, 0)
        inq_count = inquiry_property_types.get(prop_type, 0)
        total_count = fav_count + inq_count
        percentage = round((total_count / all_interactions * 100) if all_interactions > 0 else 0, 1)
        property_preferences[prop_type] = {
            'count': total_count,
            'percentage': percentage
        }

    # Recent activity data
    recent_favorites_list = favorites.order_by('-created_at')[:5]
    recent_inquiries_list = inquiries.order_by('-created_at')[:5]

    # Mock data for additional metrics
    search_alerts = active_searches  # Number of searches with email alerts
    daily_views = 12  # Mock data

    context = {
        # Saved searches metrics
        'saved_searches': total_saved_searches,
        'active_searches': active_searches,
        'search_alerts': search_alerts,
        'recent_searches': recent_searches,

        # Favorite properties metrics
        'favorite_properties': total_favorites,
        'recent_favorites': recent_favorites,
        'avg_favorite_price': avg_favorite_price,

        # Inquiries metrics
        'inquiries_sent': total_inquiries,
        'pending_responses': pending_responses,
        'response_rate': response_rate,
        'recent_inquiries': recent_inquiries,

        # Property viewing metrics
        'properties_viewed': total_properties_viewed,
        'monthly_views': monthly_views,
        'weekly_views': weekly_views,
        'daily_views': daily_views,

        # Property preferences
        'property_preferences': property_preferences,

        # Recent activity
        'recent_favorites_list': recent_favorites_list,
        'recent_inquiries_list': recent_inquiries_list,

        # Legacy context variables for template compatibility
        'favorites_count': total_favorites,
        'inquiries_count': total_inquiries,
        'saved_searches_count': total_saved_searches,
    }
    return render(request, 'dashboards/buyer.html', context)


def api_featured_listings(request):
    """API endpoint for featured listings (HTMX)"""
    featured_listings = Land.objects.filter(
        status='approved',
        is_approved=True
    ).order_by('-created_at')[:6]

    context = {
        'featured_listings': featured_listings,
    }
    return render(request, 'components/featured_listings.html', context)


@login_required
def admin_api_recent_activity(request):
    """API endpoint for recent activity feed (HTMX)"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    # Get recent activities from different models
    recent_users = User.objects.order_by('-date_joined')[:3]
    recent_listings = Land.objects.order_by('-created_at')[:3]
    recent_inquiries = Inquiry.objects.select_related('buyer', 'land').order_by('-created_at')[:3]

    context = {
        'recent_users': recent_users,
        'recent_listings': recent_listings,
        'recent_inquiries': recent_inquiries,
    }
    return render(request, 'components/admin_activity_feed.html', context)


@login_required
def admin_api_approve_listing(request, listing_id):
    """API endpoint to approve a listing (HTMX)"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        try:
            listing = Land.objects.get(id=listing_id)
            listing.status = 'approved'
            listing.is_approved = True
            listing.save()

            return render(request, 'components/admin_listing_approved.html', {
                'listing': listing,
                'message': 'Listing approved successfully'
            })
        except Land.DoesNotExist:
            return JsonResponse({'error': 'Listing not found'}, status=404)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def admin_api_reject_listing(request, listing_id):
    """API endpoint to reject a listing (HTMX)"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        try:
            listing = Land.objects.get(id=listing_id)
            listing.status = 'rejected'
            listing.is_approved = False
            listing.admin_notes = 'Rejected by admin'
            listing.save()

            return render(request, 'components/admin_listing_rejected.html', {
                'listing': listing,
                'message': 'Listing rejected'
            })
        except Land.DoesNotExist:
            return JsonResponse({'error': 'Listing not found'}, status=404)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ============================================================================
# SELLER LISTING MANAGEMENT VIEWS
# ============================================================================

@login_required
def seller_my_listings(request):
    """View for sellers to see all their listings with search and filter"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'seller':
        return redirect('landing')

    # Get user's listings
    listings = Land.objects.filter(owner=request.user).order_by('-created_at')

    # Handle search and filtering
    form = ListingSearchForm(request.GET)
    if form.is_valid():
        search_query = form.cleaned_data.get('search')
        status_filter = form.cleaned_data.get('status')
        property_type_filter = form.cleaned_data.get('property_type')

        if search_query:
            listings = listings.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(location__icontains=search_query)
            )

        if status_filter:
            listings = listings.filter(status=status_filter)

        if property_type_filter:
            listings = listings.filter(property_type=property_type_filter)

    # Pagination
    paginator = Paginator(listings, 12)  # Show 12 listings per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'listings': page_obj,
        'form': form,
        'total_listings': listings.count(),
    }
    return render(request, 'seller/my_listings.html', context)


@login_required
def seller_create_listing(request):
    """View for sellers to create new listings"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'seller':
        return redirect('landing')

    if request.method == 'POST':
        form = LandListingForm(request.POST)
        image_formset = LandImageFormSet(request.POST, request.FILES)

        if form.is_valid() and image_formset.is_valid():
            with transaction.atomic():
                # Save the listing
                listing = form.save(commit=False)
                listing.owner = request.user
                listing.status = 'draft'  # Start as draft
                listing.save()

                # Save images
                image_formset.instance = listing
                images = image_formset.save()

                # Ensure only one primary image
                primary_images = [img for img in images if img.is_primary]
                if len(primary_images) > 1:
                    # Keep only the first primary image
                    for img in primary_images[1:]:
                        img.is_primary = False
                        img.save()
                elif len(primary_images) == 0 and images:
                    # Set first image as primary if none selected
                    images[0].is_primary = True
                    images[0].save()

                messages.success(request, 'Listing created successfully! You can now submit it for approval.')
                return redirect('seller_edit_listing', listing_id=listing.id)
    else:
        form = LandListingForm()
        image_formset = LandImageFormSet()

    context = {
        'form': form,
        'image_formset': image_formset,
        'action': 'Create',
    }
    return render(request, 'seller/create_edit_listing.html', context)


@login_required
def seller_edit_listing(request, listing_id):
    """View for sellers to edit their listings"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'seller':
        return redirect('landing')

    listing = get_object_or_404(Land, id=listing_id, owner=request.user)

    if request.method == 'POST':
        form = LandListingForm(request.POST, instance=listing)
        image_formset = LandImageFormSet(request.POST, request.FILES, instance=listing)

        if form.is_valid() and image_formset.is_valid():
            with transaction.atomic():
                # Check if significant changes were made
                original_listing = Land.objects.get(id=listing_id)
                significant_changes = (
                    form.cleaned_data['price'] != original_listing.price or
                    form.cleaned_data['size_acres'] != original_listing.size_acres or
                    form.cleaned_data['property_type'] != original_listing.property_type
                )

                # Save the listing
                listing = form.save(commit=False)

                # If significant changes and listing was approved, require re-approval
                if significant_changes and original_listing.status == 'approved':
                    listing.status = 'pending'
                    listing.is_approved = False
                    messages.info(request, 'Your listing has been updated and will require admin re-approval due to significant changes.')

                listing.save()

                # Save images
                images = image_formset.save()

                # Ensure only one primary image
                all_images = listing.images.all()
                primary_images = [img for img in all_images if img.is_primary]
                if len(primary_images) > 1:
                    # Keep only the first primary image
                    for img in primary_images[1:]:
                        img.is_primary = False
                        img.save()
                elif len(primary_images) == 0 and all_images:
                    # Set first image as primary if none selected
                    first_image = all_images.first()
                    first_image.is_primary = True
                    first_image.save()

                messages.success(request, 'Listing updated successfully!')
                return redirect('seller_my_listings')
    else:
        form = LandListingForm(instance=listing)
        image_formset = LandImageFormSet(instance=listing)

    context = {
        'form': form,
        'image_formset': image_formset,
        'listing': listing,
        'action': 'Edit',
    }
    return render(request, 'seller/create_edit_listing.html', context)


@login_required
def seller_delete_listing(request, listing_id):
    """View for sellers to delete their listings"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'seller':
        return redirect('landing')

    listing = get_object_or_404(Land, id=listing_id, owner=request.user)

    if request.method == 'POST':
        listing_title = listing.title
        listing.delete()
        messages.success(request, f'Listing "{listing_title}" has been deleted successfully.')
        return redirect('seller_my_listings')

    context = {
        'listing': listing,
    }
    return render(request, 'seller/delete_listing.html', context)


@login_required
def seller_submit_for_approval(request, listing_id):
    """View for sellers to submit listings for admin approval"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'seller':
        return redirect('landing')

    listing = get_object_or_404(Land, id=listing_id, owner=request.user)

    if request.method == 'POST':
        if listing.status == 'draft':
            listing.status = 'pending'
            listing.save()
            messages.success(request, f'Listing "{listing.title}" has been submitted for approval.')
        else:
            messages.warning(request, 'This listing has already been submitted.')

        return redirect('seller_my_listings')

    return redirect('seller_edit_listing', listing_id=listing_id)


# ============================================================================
# SELLER INQUIRY MANAGEMENT VIEWS
# ============================================================================

@login_required
def seller_inquiries(request):
    """View for sellers to see all inquiries about their listings"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'seller':
        return redirect('landing')

    # Get inquiries for user's listings
    inquiries = Inquiry.objects.filter(
        land__owner=request.user
    ).select_related('buyer', 'land').order_by('-created_at')

    # Filter by status if requested
    status_filter = request.GET.get('status')
    if status_filter == 'unread':
        inquiries = inquiries.filter(is_read=False)
    elif status_filter == 'responded':
        inquiries = inquiries.exclude(seller_response='')
    elif status_filter == 'pending':
        inquiries = inquiries.filter(seller_response='')

    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        inquiries = inquiries.filter(
            Q(subject__icontains=search_query) |
            Q(message__icontains=search_query) |
            Q(buyer__username__icontains=search_query) |
            Q(land__title__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(inquiries, 20)  # Show 20 inquiries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    total_inquiries = inquiries.count()
    unread_count = inquiries.filter(is_read=False).count()
    pending_responses = inquiries.filter(seller_response='').count()
    responded_count = total_inquiries - pending_responses

    context = {
        'inquiries': page_obj,
        'total_inquiries': total_inquiries,
        'unread_count': unread_count,
        'pending_responses': pending_responses,
        'responded_count': responded_count,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'seller/inquiries.html', context)


@login_required
def seller_inquiry_detail(request, inquiry_id):
    """View for sellers to see inquiry details and respond"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'seller':
        return redirect('landing')

    inquiry = get_object_or_404(
        Inquiry.objects.select_related('buyer', 'land'),
        id=inquiry_id,
        land__owner=request.user
    )

    # Mark as read
    if not inquiry.is_read:
        inquiry.is_read = True
        inquiry.save()

    if request.method == 'POST':
        form = InquiryResponseForm(request.POST, instance=inquiry)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.response_date = timezone.now()
            inquiry.save()
            messages.success(request, 'Your response has been sent successfully!')
            return redirect('seller_inquiries')
    else:
        form = InquiryResponseForm(instance=inquiry)

    context = {
        'inquiry': inquiry,
        'form': form,
    }
    return render(request, 'seller/inquiry_detail.html', context)


@login_required
def seller_mark_inquiry_read(request, inquiry_id):
    """HTMX endpoint to mark inquiry as read"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'seller':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        try:
            inquiry = Inquiry.objects.get(id=inquiry_id, land__owner=request.user)
            inquiry.is_read = True
            inquiry.save()

            return render(request, 'components/inquiry_read_status.html', {
                'inquiry': inquiry,
                'message': 'Marked as read'
            })
        except Inquiry.DoesNotExist:
            return JsonResponse({'error': 'Inquiry not found'}, status=404)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ============================================================================
# SELLER PROFILE MANAGEMENT VIEWS
# ============================================================================

@login_required
def seller_profile(request):
    """View for sellers to manage their profile"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'seller':
        return redirect('landing')

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('seller_profile')
    else:
        form = UserProfileForm(instance=request.user.profile, user=request.user)

    # Get seller statistics for profile display
    total_listings = request.user.land_listings.count()
    active_listings = request.user.land_listings.filter(status='approved').count()
    total_inquiries = Inquiry.objects.filter(land__owner=request.user).count()

    context = {
        'form': form,
        'total_listings': total_listings,
        'active_listings': active_listings,
        'total_inquiries': total_inquiries,
    }
    return render(request, 'seller/profile.html', context)


# ============================================================================
# SELLER API ENDPOINTS (HTMX)
# ============================================================================

@login_required
def seller_api_listing_status(request, listing_id):
    """HTMX endpoint to update listing status"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'seller':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        try:
            listing = Land.objects.get(id=listing_id, owner=request.user)
            action = request.POST.get('action')

            if action == 'submit_for_approval' and listing.status == 'draft':
                listing.status = 'pending'
                listing.save()
                message = 'Listing submitted for approval'
            elif action == 'mark_as_sold' and listing.status == 'approved':
                listing.status = 'sold'
                listing.save()
                message = 'Listing marked as sold'
            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)

            return render(request, 'components/listing_status_updated.html', {
                'listing': listing,
                'message': message
            })
        except Land.DoesNotExist:
            return JsonResponse({'error': 'Listing not found'}, status=404)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def seller_api_dashboard_stats(request):
    """HTMX endpoint for refreshing dashboard statistics"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'seller':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    # Calculate fresh statistics
    user_listings = Land.objects.filter(owner=request.user)
    total_listings = user_listings.count()
    active_listings = user_listings.filter(status='approved').count()
    draft_listings = user_listings.filter(status='draft').count()
    pending_listings = user_listings.filter(status='pending').count()

    # Get inquiries
    total_inquiries = Inquiry.objects.filter(land__owner=request.user).count()
    unread_inquiries = Inquiry.objects.filter(land__owner=request.user, is_read=False).count()

    context = {
        'total_listings': total_listings,
        'active_listings': active_listings,
        'draft_listings': draft_listings,
        'pending_listings': pending_listings,
        'total_inquiries': total_inquiries,
        'unread_inquiries': unread_inquiries,
    }
    return render(request, 'components/seller_dashboard_stats.html', context)


# ============================================================================
# BUYER PROPERTY BROWSING VIEWS
# ============================================================================

@login_required
def buyer_browse_listings(request):
    """View for buyers to browse and search available properties"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return redirect('landing')

    # Get all approved listings
    listings = Land.objects.filter(
        status='approved',
        is_approved=True
    ).select_related('owner').prefetch_related('images').order_by('-created_at')

    # Handle search and filtering
    form = PropertySearchForm(request.GET)
    if form.is_valid():
        search_query = form.cleaned_data.get('search')
        location = form.cleaned_data.get('location')
        property_type = form.cleaned_data.get('property_type')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        min_size = form.cleaned_data.get('min_size')
        max_size = form.cleaned_data.get('max_size')
        sort_by = form.cleaned_data.get('sort_by')

        # Apply filters
        if search_query:
            listings = listings.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(location__icontains=search_query)
            )

        if location:
            listings = listings.filter(location__icontains=location)

        if property_type:
            listings = listings.filter(property_type=property_type)

        if min_price:
            listings = listings.filter(price__gte=min_price)

        if max_price:
            listings = listings.filter(price__lte=max_price)

        if min_size:
            listings = listings.filter(size_acres__gte=min_size)

        if max_size:
            listings = listings.filter(size_acres__lte=max_size)

        # Apply sorting
        if sort_by == 'price_asc':
            listings = listings.order_by('price')
        elif sort_by == 'price_desc':
            listings = listings.order_by('-price')
        elif sort_by == 'size_asc':
            listings = listings.order_by('size_acres')
        elif sort_by == 'size_desc':
            listings = listings.order_by('-size_acres')
        elif sort_by == 'newest':
            listings = listings.order_by('-created_at')
        elif sort_by == 'oldest':
            listings = listings.order_by('created_at')

    # Get user's favorites for heart icons
    user_favorites = set()
    if request.user.is_authenticated:
        user_favorites = set(
            request.user.favorites.values_list('land_id', flat=True)
        )

    # Pagination
    paginator = Paginator(listings, 12)  # Show 12 listings per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics for display
    total_results = listings.count()

    context = {
        'listings': page_obj,
        'form': form,
        'total_results': total_results,
        'user_favorites': user_favorites,
        'search_performed': bool(request.GET),
    }

    # Return HTMX partial if requested
    if request.headers.get('HX-Request'):
        return render(request, 'components/property_search_results.html', context)

    return render(request, 'buyer/browse_listings.html', context)


@login_required
def buyer_property_detail(request, property_id):
    """View for buyers to see detailed property information"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return redirect('landing')

    property_obj = get_object_or_404(
        Land.objects.select_related('owner').prefetch_related('images'),
        id=property_id,
        status='approved',
        is_approved=True
    )

    # Check if user has favorited this property
    is_favorited = request.user.favorites.filter(land=property_obj).exists()

    # Get related properties (same type, similar price range)
    price_range_min = property_obj.price * Decimal('0.8')  # 20% below
    price_range_max = property_obj.price * Decimal('1.2')  # 20% above

    related_properties = Land.objects.filter(
        status='approved',
        is_approved=True,
        property_type=property_obj.property_type,
        price__gte=price_range_min,
        price__lte=price_range_max
    ).exclude(id=property_obj.id).select_related('owner').prefetch_related('images')[:4]

    # Handle inquiry form submission
    inquiry_form = None
    if request.method == 'POST' and 'submit_inquiry' in request.POST:
        inquiry_form = BuyerInquiryForm(request.POST)
        if inquiry_form.is_valid():
            inquiry = inquiry_form.save(commit=False)
            inquiry.buyer = request.user
            inquiry.land = property_obj
            inquiry.save()
            messages.success(request, 'Your inquiry has been sent to the seller!')
            return redirect('buyer_property_detail', property_id=property_obj.id)
    else:
        inquiry_form = BuyerInquiryForm()

    context = {
        'property': property_obj,
        'is_favorited': is_favorited,
        'related_properties': related_properties,
        'inquiry_form': inquiry_form,
    }
    return render(request, 'buyer/property_detail.html', context)


# ============================================================================
# BUYER FAVORITES MANAGEMENT VIEWS
# ============================================================================

@login_required
def buyer_favorites(request):
    """View for buyers to see their favorite properties"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return redirect('landing')

    # Get user's favorites
    favorites = request.user.favorites.select_related('land__owner').prefetch_related('land__images').order_by('-created_at')

    # Filter by property type if requested
    property_type_filter = request.GET.get('property_type')
    if property_type_filter:
        favorites = favorites.filter(land__property_type=property_type_filter)

    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        favorites = favorites.filter(
            Q(land__title__icontains=search_query) |
            Q(land__description__icontains=search_query) |
            Q(land__location__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(favorites, 12)  # Show 12 favorites per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    total_favorites = favorites.count()
    if total_favorites > 0:
        avg_price = favorites.aggregate(
            avg_price=models.Avg('land__price')
        )['avg_price'] or 0

        # Property type breakdown
        property_type_stats = favorites.values('land__property_type').annotate(
            count=Count('land__property_type')
        ).order_by('-count')
    else:
        avg_price = 0
        property_type_stats = []

    context = {
        'favorites': page_obj,
        'total_favorites': total_favorites,
        'avg_price': avg_price,
        'property_type_stats': property_type_stats,
        'property_type_filter': property_type_filter,
        'search_query': search_query,
    }
    return render(request, 'buyer/favorites.html', context)


@login_required
def buyer_toggle_favorite(request, property_id):
    """HTMX endpoint to toggle favorite status of a property"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        try:
            property_obj = Land.objects.get(
                id=property_id,
                status='approved',
                is_approved=True
            )

            favorite, created = Favorite.objects.get_or_create(
                user=request.user,
                land=property_obj
            )

            if not created:
                # Remove from favorites
                favorite.delete()
                is_favorited = False
                message = 'Removed from favorites'
            else:
                # Added to favorites
                is_favorited = True
                message = 'Added to favorites'

            return render(request, 'components/favorite_button.html', {
                'property': property_obj,
                'is_favorited': is_favorited,
                'message': message
            })

        except Land.DoesNotExist:
            return JsonResponse({'error': 'Property not found'}, status=404)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def buyer_remove_favorite(request, favorite_id):
    """View to remove a property from favorites"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return redirect('landing')

    favorite = get_object_or_404(Favorite, id=favorite_id, user=request.user)

    if request.method == 'POST':
        property_title = favorite.land.title
        favorite.delete()
        messages.success(request, f'"{property_title}" has been removed from your favorites.')
        return redirect('buyer_favorites')

    context = {
        'favorite': favorite,
    }
    return render(request, 'buyer/remove_favorite.html', context)


# ============================================================================
# BUYER SAVED SEARCHES VIEWS
# ============================================================================

@login_required
def buyer_saved_searches(request):
    """View for buyers to manage their saved searches"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return redirect('landing')

    # Get user's saved searches
    saved_searches = request.user.saved_searches.order_by('-created_at')

    # Filter by active status if requested
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        saved_searches = saved_searches.filter(is_active=True)
    elif status_filter == 'inactive':
        saved_searches = saved_searches.filter(is_active=False)

    # Add matching properties count for each search
    for search in saved_searches:
        search.matching_count = search.get_matching_properties_count()

    # Pagination
    paginator = Paginator(saved_searches, 10)  # Show 10 searches per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    total_searches = saved_searches.count()
    active_searches = saved_searches.filter(is_active=True).count()
    searches_with_alerts = saved_searches.filter(email_alerts=True).count()

    context = {
        'saved_searches': page_obj,
        'total_searches': total_searches,
        'active_searches': active_searches,
        'searches_with_alerts': searches_with_alerts,
        'status_filter': status_filter,
    }
    return render(request, 'buyer/saved_searches.html', context)


@login_required
def buyer_create_saved_search(request):
    """View for buyers to create a new saved search"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return redirect('landing')

    if request.method == 'POST':
        form = SavedSearchForm(request.POST)
        if form.is_valid():
            saved_search = form.save(commit=False)
            saved_search.user = request.user
            saved_search.save()
            messages.success(request, f'Saved search "{saved_search.name}" has been created!')
            return redirect('buyer_saved_searches')
    else:
        # Pre-populate form with current search parameters if coming from browse page
        initial_data = {}
        if request.GET:
            initial_data = {
                'search_query': request.GET.get('search', ''),
                'location_filter': request.GET.get('location', ''),
                'property_type_filter': request.GET.get('property_type', ''),
                'min_price': request.GET.get('min_price', ''),
                'max_price': request.GET.get('max_price', ''),
                'min_size': request.GET.get('min_size', ''),
                'max_size': request.GET.get('max_size', ''),
            }
        form = SavedSearchForm(initial=initial_data)

    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'buyer/create_edit_saved_search.html', context)


@login_required
def buyer_edit_saved_search(request, search_id):
    """View for buyers to edit their saved searches"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return redirect('landing')

    saved_search = get_object_or_404(SavedSearch, id=search_id, user=request.user)

    if request.method == 'POST':
        form = SavedSearchForm(request.POST, instance=saved_search)
        if form.is_valid():
            form.save()
            messages.success(request, f'Saved search "{saved_search.name}" has been updated!')
            return redirect('buyer_saved_searches')
    else:
        form = SavedSearchForm(instance=saved_search)

    context = {
        'form': form,
        'saved_search': saved_search,
        'action': 'Edit',
    }
    return render(request, 'buyer/create_edit_saved_search.html', context)


@login_required
def buyer_delete_saved_search(request, search_id):
    """View for buyers to delete their saved searches"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return redirect('landing')

    saved_search = get_object_or_404(SavedSearch, id=search_id, user=request.user)

    if request.method == 'POST':
        search_name = saved_search.name
        saved_search.delete()
        messages.success(request, f'Saved search "{search_name}" has been deleted.')
        return redirect('buyer_saved_searches')

    context = {
        'saved_search': saved_search,
    }
    return render(request, 'buyer/delete_saved_search.html', context)


@login_required
def buyer_toggle_search_status(request, search_id):
    """HTMX endpoint to toggle saved search active status"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        try:
            saved_search = SavedSearch.objects.get(id=search_id, user=request.user)
            saved_search.is_active = not saved_search.is_active
            saved_search.save()

            status_text = 'Active' if saved_search.is_active else 'Inactive'
            message = f'Search "{saved_search.name}" is now {status_text.lower()}'

            return render(request, 'components/search_status_updated.html', {
                'saved_search': saved_search,
                'message': message
            })

        except SavedSearch.DoesNotExist:
            return JsonResponse({'error': 'Saved search not found'}, status=404)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ============================================================================
# BUYER INQUIRY SYSTEM VIEWS
# ============================================================================

@login_required
def buyer_inquiries(request):
    """View for buyers to see their inquiry history"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return redirect('landing')

    # Get user's inquiries
    inquiries = request.user.inquiries_sent.select_related('land__owner').order_by('-created_at')

    # Filter by response status if requested
    status_filter = request.GET.get('status')
    if status_filter == 'pending':
        inquiries = inquiries.filter(seller_response='')
    elif status_filter == 'responded':
        inquiries = inquiries.exclude(seller_response='')

    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        inquiries = inquiries.filter(
            Q(subject__icontains=search_query) |
            Q(message__icontains=search_query) |
            Q(land__title__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(inquiries, 20)  # Show 20 inquiries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    total_inquiries = inquiries.count()
    pending_responses = inquiries.filter(seller_response='').count()
    responded_inquiries = inquiries.exclude(seller_response='').count()
    response_rate = round((responded_inquiries / total_inquiries * 100) if total_inquiries > 0 else 0, 1)

    context = {
        'inquiries': page_obj,
        'total_inquiries': total_inquiries,
        'pending_responses': pending_responses,
        'responded_inquiries': responded_inquiries,
        'response_rate': response_rate,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'buyer/inquiries.html', context)


@login_required
def buyer_inquiry_detail(request, inquiry_id):
    """View for buyers to see inquiry details and seller responses"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return redirect('landing')

    inquiry = get_object_or_404(
        Inquiry.objects.select_related('land__owner'),
        id=inquiry_id,
        buyer=request.user
    )

    context = {
        'inquiry': inquiry,
    }
    return render(request, 'buyer/inquiry_detail.html', context)


@login_required
def buyer_send_inquiry(request, property_id):
    """View for buyers to send inquiries about specific properties"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return redirect('landing')

    property_obj = get_object_or_404(
        Land.objects.select_related('owner'),
        id=property_id,
        status='approved',
        is_approved=True
    )

    # Check if user has already sent an inquiry for this property recently
    recent_inquiry = request.user.inquiries_sent.filter(
        land=property_obj,
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).first()

    if recent_inquiry:
        messages.warning(request, 'You have already sent an inquiry about this property in the last 24 hours.')
        return redirect('buyer_property_detail', property_id=property_obj.id)

    if request.method == 'POST':
        form = BuyerInquiryForm(request.POST)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.buyer = request.user
            inquiry.land = property_obj
            inquiry.save()
            messages.success(request, 'Your inquiry has been sent to the seller!')
            return redirect('buyer_inquiries')
    else:
        # Pre-populate subject with property title
        initial_data = {
            'subject': f'Inquiry about {property_obj.title}'
        }
        form = BuyerInquiryForm(initial=initial_data)

    context = {
        'form': form,
        'property': property_obj,
    }
    return render(request, 'buyer/send_inquiry.html', context)


# ============================================================================
# BUYER PROFILE MANAGEMENT VIEWS
# ============================================================================

@login_required
def buyer_profile(request):
    """View for buyers to manage their profile"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return redirect('landing')

    if request.method == 'POST':
        form = BuyerProfileForm(request.POST, request.FILES, instance=request.user.profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('buyer_profile')
    else:
        form = BuyerProfileForm(instance=request.user.profile, user=request.user)

    # Get buyer statistics for profile display
    total_favorites = request.user.favorites.count()
    total_saved_searches = request.user.saved_searches.count()
    total_inquiries = request.user.inquiries_sent.count()

    context = {
        'form': form,
        'total_favorites': total_favorites,
        'total_saved_searches': total_saved_searches,
        'total_inquiries': total_inquiries,
    }
    return render(request, 'buyer/profile.html', context)


# ============================================================================
# BUYER API ENDPOINTS (HTMX)
# ============================================================================

@login_required
def buyer_api_dashboard_stats(request):
    """HTMX endpoint for refreshing buyer dashboard statistics"""
    # Role-based access control
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'buyer':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    # Calculate fresh statistics
    total_favorites = request.user.favorites.count()
    total_saved_searches = request.user.saved_searches.count()
    active_searches = request.user.saved_searches.filter(is_active=True).count()
    searches_with_alerts = request.user.saved_searches.filter(email_alerts=True).count()

    # Get inquiries
    total_inquiries = request.user.inquiries_sent.count()
    pending_responses = request.user.inquiries_sent.filter(seller_response='').count()
    responded_inquiries = request.user.inquiries_sent.exclude(seller_response='').count()
    response_rate = round((responded_inquiries / total_inquiries * 100) if total_inquiries > 0 else 0, 1)

    # Calculate average favorite price
    favorite_prices = [fav.land.price for fav in request.user.favorites.all() if fav.land.price]
    avg_favorite_price = sum(favorite_prices) / len(favorite_prices) if favorite_prices else 0

    context = {
        'total_favorites': total_favorites,
        'total_saved_searches': total_saved_searches,
        'active_searches': active_searches,
        'searches_with_alerts': searches_with_alerts,
        'total_inquiries': total_inquiries,
        'pending_responses': pending_responses,
        'responded_inquiries': responded_inquiries,
        'response_rate': response_rate,
        'avg_favorite_price': avg_favorite_price,
    }
    return render(request, 'components/buyer_dashboard_stats.html', context)