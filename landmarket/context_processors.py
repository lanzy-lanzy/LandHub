"""
Context processors for the LandHub application.
Provides global template variables for notifications and other shared data.
"""

from django.db.models import Q
from .models import Notification


def notifications(request):
    """
    Add notification data to all template contexts.
    
    Provides:
    - unread_notifications_count: Number of unread notifications for the user
    - recent_notifications: Last 5 notifications for dropdown display
    - has_unread_notifications: Boolean indicating if user has unread notifications
    """
    if not request.user.is_authenticated:
        return {
            'unread_notifications_count': 0,
            'recent_notifications': [],
            'has_unread_notifications': False,
        }
    
    # Get unread notifications count
    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    # Get recent notifications for dropdown (last 5)
    recent_notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('sender', 'content_type').order_by('-created_at')[:5]
    
    return {
        'unread_notifications_count': unread_count,
        'recent_notifications': recent_notifications,
        'has_unread_notifications': unread_count > 0,
    }


def user_stats(request):
    """
    Add user-specific statistics to template contexts.
    This can be extended to include other global stats.
    """
    if not request.user.is_authenticated:
        return {}
    
    # This can be extended with other user stats
    # For now, we'll keep it simple and focused on notifications
    return {}
