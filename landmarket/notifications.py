"""
Notification utility functions for creating and managing notifications.
"""

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from .models import Notification, Land, Inquiry


def create_notification(recipient, notification_type, title, message, sender=None, related_object=None, metadata=None):
    """
    Create a new notification.
    
    Args:
        recipient: User who will receive the notification
        notification_type: Type of notification (from Notification.NOTIFICATION_TYPES)
        title: Short title for the notification
        message: Detailed message
        sender: User who triggered the notification (optional)
        related_object: Related model instance (Land, Inquiry, etc.) (optional)
        metadata: Additional data as dict (optional)
    
    Returns:
        Notification instance
    """
    notification_data = {
        'recipient': recipient,
        'sender': sender,
        'notification_type': notification_type,
        'title': title,
        'message': message,
    }

    # Add related object if provided
    if related_object:
        notification_data['content_type'] = ContentType.objects.get_for_model(related_object)
        notification_data['object_id'] = related_object.id

    notification = Notification.objects.create(**notification_data)

    # Set metadata if provided
    if metadata:
        notification.set_metadata(metadata)
        notification.save()

    return notification


def notify_new_inquiry(inquiry):
    """Create notification when a new inquiry is submitted"""
    seller = inquiry.land.owner
    buyer = inquiry.buyer
    
    title = f"New inquiry about {inquiry.land.title}"
    message = f"{buyer.get_full_name() or buyer.username} sent an inquiry about your property '{inquiry.land.title}'. Subject: {inquiry.subject}"
    
    return create_notification(
        recipient=seller,
        sender=buyer,
        notification_type='inquiry_new',
        title=title,
        message=message,
        related_object=inquiry,
        metadata={
            'property_id': inquiry.land.id,
            'property_title': inquiry.land.title,
            'inquiry_subject': inquiry.subject
        }
    )


def notify_inquiry_response(inquiry):
    """Create notification when seller responds to an inquiry"""
    buyer = inquiry.buyer
    seller = inquiry.land.owner
    
    title = f"Response to your inquiry about {inquiry.land.title}"
    message = f"{seller.get_full_name() or seller.username} responded to your inquiry about '{inquiry.land.title}'."
    
    return create_notification(
        recipient=buyer,
        sender=seller,
        notification_type='inquiry_response',
        title=title,
        message=message,
        related_object=inquiry,
        metadata={
            'property_id': inquiry.land.id,
            'property_title': inquiry.land.title,
            'inquiry_subject': inquiry.subject
        }
    )


def notify_listing_approved(listing):
    """Create notification when a listing is approved"""
    seller = listing.owner
    
    title = f"Listing approved: {listing.title}"
    message = f"Your property listing '{listing.title}' has been approved and is now live on the platform."
    
    return create_notification(
        recipient=seller,
        notification_type='listing_approved',
        title=title,
        message=message,
        related_object=listing,
        metadata={
            'property_id': listing.id,
            'property_title': listing.title,
            'property_type': listing.property_type
        }
    )


def notify_listing_rejected(listing, admin_notes=""):
    """Create notification when a listing is rejected"""
    seller = listing.owner
    
    title = f"Listing rejected: {listing.title}"
    message = f"Your property listing '{listing.title}' has been rejected."
    if admin_notes:
        message += f" Reason: {admin_notes}"
    
    return create_notification(
        recipient=seller,
        notification_type='listing_rejected',
        title=title,
        message=message,
        related_object=listing,
        metadata={
            'property_id': listing.id,
            'property_title': listing.title,
            'admin_notes': admin_notes
        }
    )


def notify_listing_pending_approval(listing):
    """Create notification for admins when a listing needs approval"""
    # Get all admin users
    admin_users = User.objects.filter(profile__role='admin')
    
    title = f"New listing pending approval: {listing.title}"
    message = f"A new property listing '{listing.title}' by {listing.owner.get_full_name() or listing.owner.username} is pending approval."
    
    notifications = []
    for admin in admin_users:
        notification = create_notification(
            recipient=admin,
            sender=listing.owner,
            notification_type='listing_pending',
            title=title,
            message=message,
            related_object=listing,
            metadata={
                'property_id': listing.id,
                'property_title': listing.title,
                'seller_name': listing.owner.get_full_name() or listing.owner.username
            }
        )
        notifications.append(notification)
    
    return notifications


def notify_property_favorited(favorite):
    """Create notification when someone favorites a property (optional)"""
    seller = favorite.land.owner
    buyer = favorite.user
    
    # Only notify if seller wants these notifications (you can add a preference later)
    title = f"Someone favorited your property: {favorite.land.title}"
    message = f"{buyer.get_full_name() or buyer.username} added your property '{favorite.land.title}' to their favorites."
    
    return create_notification(
        recipient=seller,
        sender=buyer,
        notification_type='property_favorited',
        title=title,
        message=message,
        related_object=favorite.land,
        metadata={
            'property_id': favorite.land.id,
            'property_title': favorite.land.title,
            'buyer_name': buyer.get_full_name() or buyer.username
        }
    )


def notify_welcome_message(user):
    """Create welcome notification for new users"""
    role_messages = {
        'buyer': "Welcome to LandHub! Start exploring amazing land properties and find your perfect piece of land.",
        'seller': "Welcome to LandHub! You can now list your properties and connect with potential buyers.",
        'admin': "Welcome to LandHub Admin! You have access to manage listings and oversee the platform."
    }
    
    role = getattr(user.profile, 'role', 'buyer')
    message = role_messages.get(role, role_messages['buyer'])
    
    return create_notification(
        recipient=user,
        notification_type='system_welcome',
        title="Welcome to LandHub!",
        message=message,
        metadata={
            'user_role': role,
            'welcome_date': user.date_joined.isoformat()
        }
    )


def notify_system_update(message, users=None):
    """Create system update notifications for users"""
    if users is None:
        users = User.objects.filter(is_active=True)
    
    title = "System Update"
    
    notifications = []
    for user in users:
        notification = create_notification(
            recipient=user,
            notification_type='system_update',
            title=title,
            message=message,
            metadata={
                'update_type': 'system',
                'broadcast': True
            }
        )
        notifications.append(notification)
    
    return notifications
