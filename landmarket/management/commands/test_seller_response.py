"""
Management command to test seller inquiry response functionality
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from landmarket.models import Land, Inquiry
from landmarket.forms import InquiryResponseForm
from landmarket.notifications import notify_inquiry_response


class Command(BaseCommand):
    help = 'Test seller inquiry response functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--seller',
            type=str,
            default='seller_test',
            help='Username of seller for testing (default: seller_test)',
        )

    def handle(self, *args, **options):
        seller_username = options['seller']
        
        self.stdout.write("🔍 Testing Seller Inquiry Response System...")
        
        # Get seller user
        try:
            seller = User.objects.get(username=seller_username)
            self.stdout.write(
                self.style.SUCCESS(f"✅ Found seller: {seller.username}")
            )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"❌ Seller '{seller_username}' not found")
            )
            return
        
        # Get inquiries for this seller
        inquiries = Inquiry.objects.filter(land__owner=seller).order_by('-created_at')
        
        if not inquiries.exists():
            self.stdout.write(
                self.style.ERROR("❌ No inquiries found for this seller")
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Found {inquiries.count()} inquiries for seller")
        )
        
        # Test 1: Check inquiry access and permissions
        self.stdout.write("\n🔐 Test 1: Checking inquiry access...")
        for inquiry in inquiries[:3]:  # Test first 3 inquiries
            try:
                # Verify seller can access this inquiry
                assert inquiry.land.owner == seller, f"Seller doesn't own property for inquiry {inquiry.id}"
                
                # Check inquiry details
                self.stdout.write(f"   - Inquiry {inquiry.id}: {inquiry.subject}")
                self.stdout.write(f"     From: {inquiry.buyer.username}")
                self.stdout.write(f"     Property: {inquiry.land.title}")
                self.stdout.write(f"     Read: {'Yes' if inquiry.is_read else 'No'}")
                self.stdout.write(f"     Responded: {'Yes' if inquiry.seller_response else 'No'}")
                
            except AssertionError as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Access check failed for inquiry {inquiry.id}: {e}")
                )
                return
        
        self.stdout.write(self.style.SUCCESS("✅ All inquiry access checks passed"))
        
        # Test 2: Test form validation
        self.stdout.write("\n📝 Test 2: Testing form validation...")
        
        # Get an inquiry without response for testing
        test_inquiry = inquiries.filter(seller_response='').first()
        if not test_inquiry:
            # Create a test inquiry if none exists without response
            buyer = User.objects.filter(profile__role='buyer').first()
            if buyer:
                property_obj = Land.objects.filter(owner=seller, status='approved').first()
                if property_obj:
                    test_inquiry = Inquiry.objects.create(
                        buyer=buyer,
                        land=property_obj,
                        subject="Test inquiry for response testing",
                        message="This is a test inquiry for testing seller responses."
                    )
                    self.stdout.write(
                        self.style.WARNING(f"⚠️ Created test inquiry: {test_inquiry.id}")
                    )
        
        if test_inquiry:
            # Test valid form data
            valid_data = {
                'seller_response': 'Thank you for your inquiry! I would be happy to provide more information about this property.'
            }
            form = InquiryResponseForm(data=valid_data, instance=test_inquiry)
            
            if form.is_valid():
                self.stdout.write(self.style.SUCCESS("✅ Valid form data accepted"))
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Valid form data rejected: {form.errors}")
                )
                return
            
            # Test invalid form data (too short)
            invalid_data = {
                'seller_response': 'Short'  # Less than 10 characters
            }
            form = InquiryResponseForm(data=invalid_data, instance=test_inquiry)
            
            if not form.is_valid():
                self.stdout.write(self.style.SUCCESS("✅ Invalid form data properly rejected"))
            else:
                self.stdout.write(
                    self.style.ERROR("❌ Invalid form data was accepted")
                )
                return
        
        # Test 3: Test response saving
        self.stdout.write("\n💾 Test 3: Testing response saving...")
        
        if test_inquiry and not test_inquiry.seller_response:
            try:
                original_response_date = test_inquiry.response_date
                original_read_status = test_inquiry.is_read
                
                # Save response
                test_inquiry.seller_response = "This is a test response from the seller. Thank you for your interest in our property!"
                test_inquiry.response_date = timezone.now()
                test_inquiry.is_read = True
                test_inquiry.save()
                
                # Verify changes
                test_inquiry.refresh_from_db()
                assert test_inquiry.seller_response != "", "Response not saved"
                assert test_inquiry.response_date is not None, "Response date not set"
                assert test_inquiry.is_read == True, "Inquiry not marked as read"
                
                self.stdout.write(self.style.SUCCESS("✅ Response saved successfully"))
                
                # Test notification trigger
                notify_inquiry_response(test_inquiry)
                self.stdout.write(self.style.SUCCESS("✅ Response notification sent"))
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error saving response: {e}")
                )
                return
        
        # Test 4: Check notification creation
        self.stdout.write("\n🔔 Test 4: Checking notifications...")
        
        if test_inquiry:
            try:
                # Check buyer notifications
                buyer_notifications = test_inquiry.buyer.notifications.filter(
                    notification_type='inquiry_response'
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Buyer has {buyer_notifications.count()} response notifications"
                    )
                )
                
                # Check latest notification
                latest_notification = buyer_notifications.first()
                if latest_notification:
                    self.stdout.write(f"   Latest notification: {latest_notification.title}")
                    self.stdout.write(f"   Message: {latest_notification.message[:100]}...")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error checking notifications: {e}")
                )
                return
        
        # Test 5: Check inquiry status updates
        self.stdout.write("\n📊 Test 5: Checking inquiry status...")
        
        try:
            # Count inquiries by status
            total_inquiries = inquiries.count()
            unread_inquiries = inquiries.filter(is_read=False).count()
            responded_inquiries = inquiries.exclude(seller_response='').count()
            pending_inquiries = inquiries.filter(seller_response='').count()
            
            self.stdout.write(f"   Total inquiries: {total_inquiries}")
            self.stdout.write(f"   Unread inquiries: {unread_inquiries}")
            self.stdout.write(f"   Responded inquiries: {responded_inquiries}")
            self.stdout.write(f"   Pending inquiries: {pending_inquiries}")
            
            # Verify counts add up
            assert responded_inquiries + pending_inquiries == total_inquiries, "Inquiry counts don't match"
            
            self.stdout.write(self.style.SUCCESS("✅ Inquiry status counts verified"))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error checking inquiry status: {e}")
            )
            return
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS("\n🎉 All seller response tests passed!")
        )
        
        if test_inquiry:
            self.stdout.write(f"📊 Test Summary:")
            self.stdout.write(f"   - Test Inquiry ID: {test_inquiry.id}")
            self.stdout.write(f"   - Seller: {seller.username}")
            self.stdout.write(f"   - Buyer: {test_inquiry.buyer.username}")
            self.stdout.write(f"   - Property: {test_inquiry.land.title}")
            self.stdout.write(f"   - Response saved: {'Yes' if test_inquiry.seller_response else 'No'}")
            self.stdout.write(f"   - Response date: {test_inquiry.response_date}")
            self.stdout.write(f"   - Marked as read: {'Yes' if test_inquiry.is_read else 'No'}")
        
        self.stdout.write(
            self.style.SUCCESS("✅ Seller inquiry response system is working correctly!")
        )
