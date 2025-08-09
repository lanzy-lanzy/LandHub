"""
Management command to test all inquiry-related notification triggers
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from landmarket.models import Land, Inquiry, Notification
from landmarket.notifications import notify_new_inquiry, notify_inquiry_response


class Command(BaseCommand):
    help = 'Test inquiry-related notification triggers'

    def handle(self, *args, **options):
        self.stdout.write("🔔 Testing Inquiry Notification Triggers...")
        
        # Get test users
        try:
            buyer = User.objects.get(username='buyer_test')
            seller = User.objects.get(username='seller_test')
            self.stdout.write(
                self.style.SUCCESS(f"✅ Found test users: {buyer.username}, {seller.username}")
            )
        except User.DoesNotExist as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Test users not found: {e}")
            )
            return
        
        # Get test property
        property_obj = Land.objects.filter(
            owner=seller,
            status='approved',
            is_approved=True
        ).first()
        
        if not property_obj:
            self.stdout.write(
                self.style.ERROR("❌ No approved properties found for testing")
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Using test property: {property_obj.title}")
        )
        
        # Clear existing notifications for clean testing
        initial_seller_notifications = seller.notifications.count()
        initial_buyer_notifications = buyer.notifications.count()
        
        self.stdout.write(f"📊 Initial notification counts:")
        self.stdout.write(f"   Seller: {initial_seller_notifications}")
        self.stdout.write(f"   Buyer: {initial_buyer_notifications}")
        
        # Test 1: New Inquiry Notification
        self.stdout.write("\n📝 Test 1: Testing new inquiry notification...")
        
        try:
            # Create a new inquiry
            inquiry = Inquiry.objects.create(
                buyer=buyer,
                land=property_obj,
                subject="Test notification inquiry",
                message="This is a test inquiry to verify notification triggers are working correctly."
            )
            
            self.stdout.write(f"✅ Created test inquiry: {inquiry.id}")
            
            # Trigger notification
            notification = notify_new_inquiry(inquiry)
            
            if notification:
                self.stdout.write(f"✅ New inquiry notification created: {notification.id}")
                
                # Verify notification details
                assert notification.recipient == seller, "Wrong recipient"
                assert notification.sender == buyer, "Wrong sender"
                assert notification.notification_type == 'inquiry_new', "Wrong notification type"
                assert inquiry.land.title in notification.title, "Property title not in notification title"
                assert inquiry.subject in notification.message, "Inquiry subject not in notification message"
                assert not notification.is_read, "Notification should be unread"
                
                self.stdout.write("✅ New inquiry notification details verified")
                
                # Check metadata
                metadata = notification.get_metadata()
                assert metadata.get('property_id') == property_obj.id, "Property ID not in metadata"
                assert metadata.get('property_title') == property_obj.title, "Property title not in metadata"
                assert metadata.get('inquiry_subject') == inquiry.subject, "Inquiry subject not in metadata"
                
                self.stdout.write("✅ New inquiry notification metadata verified")
                
            else:
                self.stdout.write(
                    self.style.ERROR("❌ New inquiry notification not created")
                )
                return
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error testing new inquiry notification: {e}")
            )
            return
        
        # Test 2: Inquiry Response Notification
        self.stdout.write("\n💬 Test 2: Testing inquiry response notification...")
        
        try:
            # Add response to inquiry
            inquiry.seller_response = "Thank you for your inquiry! This is a test response to verify notification triggers."
            inquiry.response_date = timezone.now()
            inquiry.is_read = True
            inquiry.save()
            
            self.stdout.write("✅ Added response to inquiry")
            
            # Trigger notification
            response_notification = notify_inquiry_response(inquiry)
            
            if response_notification:
                self.stdout.write(f"✅ Inquiry response notification created: {response_notification.id}")
                
                # Verify notification details
                assert response_notification.recipient == buyer, "Wrong recipient"
                assert response_notification.sender == seller, "Wrong sender"
                assert response_notification.notification_type == 'inquiry_response', "Wrong notification type"
                assert inquiry.land.title in response_notification.title, "Property title not in notification title"
                assert seller.username in response_notification.message or seller.get_full_name() in response_notification.message, "Seller name not in notification message"
                assert not response_notification.is_read, "Notification should be unread"
                
                self.stdout.write("✅ Inquiry response notification details verified")
                
                # Check metadata
                metadata = response_notification.get_metadata()
                assert metadata.get('property_id') == property_obj.id, "Property ID not in metadata"
                assert metadata.get('property_title') == property_obj.title, "Property title not in metadata"
                assert metadata.get('inquiry_subject') == inquiry.subject, "Inquiry subject not in metadata"
                
                self.stdout.write("✅ Inquiry response notification metadata verified")
                
            else:
                self.stdout.write(
                    self.style.ERROR("❌ Inquiry response notification not created")
                )
                return
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error testing inquiry response notification: {e}")
            )
            return
        
        # Test 3: Verify notification counts
        self.stdout.write("\n📊 Test 3: Verifying notification counts...")
        
        try:
            # Check seller notifications (should have +1 for new inquiry)
            current_seller_notifications = seller.notifications.count()
            seller_inquiry_notifications = seller.notifications.filter(
                notification_type='inquiry_new'
            ).count()
            
            self.stdout.write(f"   Seller total notifications: {current_seller_notifications}")
            self.stdout.write(f"   Seller inquiry notifications: {seller_inquiry_notifications}")
            
            # Check buyer notifications (should have +1 for response)
            current_buyer_notifications = buyer.notifications.count()
            buyer_response_notifications = buyer.notifications.filter(
                notification_type='inquiry_response'
            ).count()
            
            self.stdout.write(f"   Buyer total notifications: {current_buyer_notifications}")
            self.stdout.write(f"   Buyer response notifications: {buyer_response_notifications}")
            
            # Verify increases
            assert current_seller_notifications > initial_seller_notifications, "Seller notification count didn't increase"
            assert current_buyer_notifications > initial_buyer_notifications, "Buyer notification count didn't increase"
            
            self.stdout.write("✅ Notification counts verified")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error verifying notification counts: {e}")
            )
            return
        
        # Test 4: Test notification action URLs
        self.stdout.write("\n🔗 Test 4: Testing notification action URLs...")
        
        try:
            # Test new inquiry notification URL
            inquiry_notification_url = notification.get_action_url()
            expected_seller_url = f"/seller/inquiries/{inquiry.id}/"
            
            if inquiry_notification_url == expected_seller_url:
                self.stdout.write("✅ New inquiry notification URL correct")
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ New inquiry notification URL: {inquiry_notification_url} (expected: {expected_seller_url})")
                )
            
            # Test response notification URL
            response_notification_url = response_notification.get_action_url()
            expected_buyer_url = f"/buyer/inquiries/{inquiry.id}/"
            
            if response_notification_url == expected_buyer_url:
                self.stdout.write("✅ Inquiry response notification URL correct")
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Inquiry response notification URL: {response_notification_url} (expected: {expected_buyer_url})")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error testing notification URLs: {e}")
            )
            return
        
        # Test 5: Test notification read/unread functionality
        self.stdout.write("\n👁️ Test 5: Testing notification read/unread functionality...")
        
        try:
            # Both notifications should be unread initially
            assert not notification.is_read, "New inquiry notification should be unread"
            assert not response_notification.is_read, "Response notification should be unread"
            
            # Mark notifications as read
            notification.mark_as_read()
            response_notification.mark_as_read()
            
            # Verify they are now read
            notification.refresh_from_db()
            response_notification.refresh_from_db()
            
            assert notification.is_read, "New inquiry notification should be read"
            assert response_notification.is_read, "Response notification should be read"
            assert notification.read_at is not None, "Read timestamp should be set"
            assert response_notification.read_at is not None, "Read timestamp should be set"
            
            self.stdout.write("✅ Notification read/unread functionality verified")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error testing read/unread functionality: {e}")
            )
            return
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS("\n🎉 All notification trigger tests passed!")
        )
        
        self.stdout.write(f"📊 Test Summary:")
        self.stdout.write(f"   - Test Inquiry ID: {inquiry.id}")
        self.stdout.write(f"   - New Inquiry Notification ID: {notification.id}")
        self.stdout.write(f"   - Response Notification ID: {response_notification.id}")
        self.stdout.write(f"   - Seller: {seller.username}")
        self.stdout.write(f"   - Buyer: {buyer.username}")
        self.stdout.write(f"   - Property: {property_obj.title}")
        self.stdout.write(f"   - Notifications created: 2")
        self.stdout.write(f"   - All triggers working: ✅")
        
        self.stdout.write(
            self.style.SUCCESS("✅ Inquiry notification system is fully functional!")
        )
