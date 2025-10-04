from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Public pages
    path('', views.landing, name='landing'),

    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('register/', views.register, name='register'),

    # Dashboards
    path('dashboard/', views.dashboard, name='dashboard'),

    # API endpoints for HTMX
    path('api/featured-listings/', views.api_featured_listings, name='api_featured_listings'),

    # Admin management (using /manage/ to avoid conflict with Django admin)
    path('manage/users/', views.admin_user_management, name='admin_user_management'),
    path('manage/listings/', views.admin_listing_management, name='admin_listing_management'),
    path('manage/listings/<int:listing_id>/', views.admin_listing_detail, name='admin_listing_detail'),
    path('manage/analytics/', views.admin_analytics, name='admin_analytics'),
    path('manage/settings/', views.admin_settings, name='admin_settings'),
    path('manage/profile/', views.admin_profile, name='admin_profile'),

    # Admin API endpoints
    path('manage/api/recent-activity/', views.admin_api_recent_activity, name='admin_api_recent_activity'),
    path('manage/api/approve-listing/<int:listing_id>/', views.admin_api_approve_listing, name='admin_api_approve_listing'),
    path('manage/api/reject-listing/<int:listing_id>/', views.admin_api_reject_listing, name='admin_api_reject_listing'),
    path('manage/api/dashboard-stats/', views.admin_api_dashboard_stats, name='admin_api_dashboard_stats'),

    # Seller listing management
    path('seller/listings/', views.seller_my_listings, name='seller_my_listings'),
    path('seller/listings/create/', views.seller_create_listing, name='seller_create_listing'),
    path('seller/listings/<int:listing_id>/edit/', views.seller_edit_listing, name='seller_edit_listing'),
    path('seller/listings/<int:listing_id>/delete/', views.seller_delete_listing, name='seller_delete_listing'),
    path('seller/listings/<int:listing_id>/submit/', views.seller_submit_for_approval, name='seller_submit_for_approval'),

    # Seller inquiry management
    path('seller/inquiries/', views.seller_inquiries, name='seller_inquiries'),
    path('seller/inquiries/<int:inquiry_id>/', views.seller_inquiry_detail, name='seller_inquiry_detail'),

    # Seller profile management
    path('seller/profile/', views.seller_profile, name='seller_profile'),

    # Seller API endpoints
    path('seller/api/listing-status/<int:listing_id>/', views.seller_api_listing_status, name='seller_api_listing_status'),
    path('seller/api/dashboard-stats/', views.seller_api_dashboard_stats, name='seller_api_dashboard_stats'),
    path('seller/api/mark-inquiry-read/<int:inquiry_id>/', views.seller_mark_inquiry_read, name='seller_mark_inquiry_read'),

    # Buyer property browsing
    path('buyer/browse/', views.buyer_browse_listings, name='buyer_browse_listings'),
    path('buyer/property/<int:property_id>/', views.buyer_property_detail, name='buyer_property_detail'),

    # Buyer favorites management
    path('buyer/favorites/', views.buyer_favorites, name='buyer_favorites'),
    path('buyer/favorites/remove/<int:favorite_id>/', views.buyer_remove_favorite, name='buyer_remove_favorite'),

    # Buyer saved searches
    path('buyer/saved-searches/', views.buyer_saved_searches, name='buyer_saved_searches'),
    path('buyer/saved-searches/create/', views.buyer_create_saved_search, name='buyer_create_saved_search'),
    path('buyer/saved-searches/<int:search_id>/edit/', views.buyer_edit_saved_search, name='buyer_edit_saved_search'),
    path('buyer/saved-searches/<int:search_id>/delete/', views.buyer_delete_saved_search, name='buyer_delete_saved_search'),

    # Buyer inquiry management
    path('buyer/inquiries/', views.buyer_inquiries, name='buyer_inquiries'),
    path('buyer/inquiries/<int:inquiry_id>/', views.buyer_inquiry_detail, name='buyer_inquiry_detail'),
    path('buyer/inquiries/send/<int:property_id>/', views.buyer_send_inquiry, name='buyer_send_inquiry'),

    # Buyer profile management
    path('buyer/profile/', views.buyer_profile, name='buyer_profile'),

    # Buyer API endpoints
    path('buyer/api/toggle-favorite/<int:property_id>/', views.buyer_toggle_favorite, name='buyer_toggle_favorite'),
    path('buyer/api/toggle-search-status/<int:search_id>/', views.buyer_toggle_search_status, name='buyer_toggle_search_status'),
    path('buyer/api/dashboard-stats/', views.buyer_api_dashboard_stats, name='buyer_api_dashboard_stats'),

    # Notification management
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/dropdown/', views.notifications_dropdown, name='notifications_dropdown'),
    path('notifications/<int:notification_id>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/<int:notification_id>/unread/', views.notification_mark_unread, name='notification_mark_unread'),
    path('notifications/<int:notification_id>/delete/', views.notification_delete, name='notification_delete'),
    path('notifications/mark-all-read/', views.notifications_mark_all_read, name='notifications_mark_all_read'),

    # Test page for modal functionality
    path('test-modal/', views.test_modal, name='test_modal'),
]