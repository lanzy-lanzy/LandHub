"""
Management command to create test notifications for development.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from landmarket.notifications import (
    notify_welcome_message, 
    notify_system_update,
    create_notification
)


class Command(BaseCommand):
    help = 'Create test notifications for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username to create notifications for (default: all users)',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of test notifications to create per user (default: 5)',
        )

    def handle(self, *args, **options):
        username = options.get('user')
        count = options.get('count', 5)
        
        if username:
            try:
                users = [User.objects.get(username=username)]
                self.stdout.write(f"Creating notifications for user: {username}")
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"User '{username}' does not exist")
                )
                return
        else:
            users = User.objects.filter(is_active=True)
            self.stdout.write(f"Creating notifications for {users.count()} users")
        
        if not users:
            self.stdout.write(self.style.WARNING("No users found"))
            return
        
        # Sample notification data
        sample_notifications = [
            {
                'notification_type': 'inquiry_new',
                'title': 'New inquiry about your property',
                'message': 'John Doe sent an inquiry about your 5-acre residential property in Austin, TX.',
            },
            {
                'notification_type': 'inquiry_response',
                'title': 'Response to your inquiry',
                'message': 'The seller responded to your inquiry about the commercial property in Dallas.',
            },
            {
                'notification_type': 'listing_approved',
                'title': 'Your listing has been approved',
                'message': 'Your property listing "Beautiful 10-acre ranch" has been approved and is now live.',
            },
            {
                'notification_type': 'listing_rejected',
                'title': 'Listing requires updates',
                'message': 'Your listing needs additional information before it can be approved.',
            },
            {
                'notification_type': 'property_favorited',
                'title': 'Someone favorited your property',
                'message': 'A buyer added your agricultural land to their favorites list.',
            },
            {
                'notification_type': 'system_welcome',
                'title': 'Welcome to LandHub!',
                'message': 'Thank you for joining LandHub. Start exploring amazing land opportunities today.',
            },
            {
                'notification_type': 'system_update',
                'title': 'New features available',
                'message': 'We\'ve added new search filters and improved the property browsing experience.',
            },
        ]
        
        total_created = 0
        
        for user in users:
            self.stdout.write(f"Creating notifications for {user.username}...")
            
            # Create welcome notification if user doesn't have one
            existing_welcome = user.notifications.filter(notification_type='system_welcome').exists()
            if not existing_welcome:
                notify_welcome_message(user)
                total_created += 1
            
            # Create sample notifications
            for i in range(min(count, len(sample_notifications))):
                notification_data = sample_notifications[i]
                
                # Skip if user already has this type of notification
                if user.notifications.filter(
                    notification_type=notification_data['notification_type'],
                    title=notification_data['title']
                ).exists():
                    continue
                
                create_notification(
                    recipient=user,
                    notification_type=notification_data['notification_type'],
                    title=notification_data['title'],
                    message=notification_data['message'],
                    metadata={
                        'test_notification': True,
                        'created_by_command': True
                    }
                )
                total_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {total_created} test notifications"
            )
        )
        
        # Show summary
        self.stdout.write("\nNotification summary:")
        for user in users:
            unread_count = user.notifications.filter(is_read=False).count()
            total_count = user.notifications.count()
            self.stdout.write(
                f"  {user.username}: {unread_count} unread, {total_count} total"
            )
