"""
Management command to test the inquiry system functionality
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from landmarket.models import Land, Inquiry
from landmarket.notifications import notify_new_inquiry, notify_inquiry_response


class Command(BaseCommand):
    help = 'Test the inquiry system functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--buyer',
            type=str,
            default='buyer_test',
            help='Username of buyer for testing (default: buyer_test)',
        )
        parser.add_argument(
            '--seller',
            type=str,
            default='seller_test',
            help='Username of seller for testing (default: seller_test)',
        )

    def handle(self, *args, **options):
        buyer_username = options['buyer']
        seller_username = options['seller']
        
        self.stdout.write("🔍 Testing Inquiry System...")
        
        # Get test users
        try:
            buyer = User.objects.get(username=buyer_username)
            seller = User.objects.get(username=seller_username)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Found test users: {buyer.username} (buyer), {seller.username} (seller)"
                )
            )
        except User.DoesNotExist as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Test users not found: {e}")
            )
            return
        
        # Get or create a test property
        try:
            property_obj = Land.objects.filter(
                owner=seller,
                status='approved',
                is_approved=True
            ).first()
            
            if not property_obj:
                # Create a test property if none exists
                property_obj = Land.objects.create(
                    title="Test Property for Inquiry",
                    description="A test property for testing the inquiry system",
                    price=50000.00,
                    size_acres=5.0,
                    location="Test Location",
                    address="123 Test Street",
                    property_type="residential",
                    status="approved",
                    is_approved=True,
                    owner=seller
                )
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Created new test property: {property_obj.title}")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Found test property: {property_obj.title}")
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error with property: {e}")
            )
            return
        
        # Test 1: Create a new inquiry
        self.stdout.write("\n📝 Test 1: Creating new inquiry...")
        try:
            # Check if inquiry already exists
            existing_inquiry = Inquiry.objects.filter(
                buyer=buyer,
                land=property_obj,
                subject="Test inquiry about your property"
            ).first()
            
            if existing_inquiry:
                inquiry = existing_inquiry
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Using existing inquiry: {inquiry.id}")
                )
            else:
                inquiry = Inquiry.objects.create(
                    buyer=buyer,
                    land=property_obj,
                    subject="Test inquiry about your property",
                    message="Hi, I'm interested in this property. Can you provide more details about the soil quality and water access?"
                )
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Created inquiry: {inquiry.id}")
                )
            
            # Test notification trigger
            notify_new_inquiry(inquiry)
            self.stdout.write(self.style.SUCCESS("✅ Notification sent to seller"))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error creating inquiry: {e}")
            )
            return
        
        # Test 2: Seller responds to inquiry
        self.stdout.write("\n💬 Test 2: Seller responding to inquiry...")
        try:
            if not inquiry.seller_response:
                inquiry.seller_response = "Thank you for your interest! The property has excellent soil quality with clay loam composition, perfect for agriculture. There's a well on the property and access to irrigation. Would you like to schedule a visit?"
                inquiry.response_date = timezone.now()
                inquiry.is_read = True
                inquiry.save()
                self.stdout.write(self.style.SUCCESS("✅ Seller response saved"))
            else:
                self.stdout.write(
                    self.style.WARNING("⚠️ Inquiry already has a response")
                )
            
            # Test notification trigger
            notify_inquiry_response(inquiry)
            self.stdout.write(self.style.SUCCESS("✅ Notification sent to buyer"))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error saving seller response: {e}")
            )
            return
        
        # Test 3: Verify inquiry data integrity
        self.stdout.write("\n🔍 Test 3: Verifying data integrity...")
        try:
            # Refresh from database
            inquiry.refresh_from_db()
            
            # Check all fields
            assert inquiry.buyer == buyer, "Buyer mismatch"
            assert inquiry.land == property_obj, "Property mismatch"
            assert inquiry.subject == "Test inquiry about your property", "Subject mismatch"
            assert inquiry.seller_response != "", "Response is empty"
            assert inquiry.response_date is not None, "Response date is None"
            assert inquiry.is_read == True, "Inquiry not marked as read"
            
            self.stdout.write(self.style.SUCCESS("✅ All inquiry fields verified"))
            
        except AssertionError as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Data integrity check failed: {e}")
            )
            return
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error verifying data: {e}")
            )
            return
        
        # Test 4: Check relationships
        self.stdout.write("\n🔗 Test 4: Checking model relationships...")
        try:
            # Check buyer's inquiries
            buyer_inquiries = buyer.inquiries_sent.all()
            assert inquiry in buyer_inquiries, "Inquiry not in buyer's inquiries"
            self.stdout.write(
                self.style.SUCCESS(f"✅ Buyer has {buyer_inquiries.count()} inquiries")
            )
            
            # Check property's inquiries
            property_inquiries = property_obj.inquiries.all()
            assert inquiry in property_inquiries, "Inquiry not in property's inquiries"
            self.stdout.write(
                self.style.SUCCESS(f"✅ Property has {property_inquiries.count()} inquiries")
            )
            
            # Check seller's inquiries (through property)
            seller_inquiries = Inquiry.objects.filter(land__owner=seller)
            assert inquiry in seller_inquiries, "Inquiry not accessible to seller"
            self.stdout.write(
                self.style.SUCCESS(f"✅ Seller can access {seller_inquiries.count()} inquiries")
            )
            
        except AssertionError as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Relationship check failed: {e}")
            )
            return
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error checking relationships: {e}")
            )
            return
        
        # Test 5: Check notifications
        self.stdout.write("\n🔔 Test 5: Checking notifications...")
        try:
            # Check seller notifications
            seller_notifications = seller.notifications.filter(
                notification_type='inquiry_new'
            )
            self.stdout.write(
                self.style.SUCCESS(f"✅ Seller has {seller_notifications.count()} inquiry notifications")
            )
            
            # Check buyer notifications
            buyer_notifications = buyer.notifications.filter(
                notification_type='inquiry_response'
            )
            self.stdout.write(
                self.style.SUCCESS(f"✅ Buyer has {buyer_notifications.count()} response notifications")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error checking notifications: {e}")
            )
            return
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS("\n🎉 All tests passed! Inquiry system is working correctly.")
        )
        self.stdout.write(f"📊 Test Summary:")
        self.stdout.write(f"   - Inquiry ID: {inquiry.id}")
        self.stdout.write(f"   - Buyer: {buyer.username}")
        self.stdout.write(f"   - Seller: {seller.username}")
        self.stdout.write(f"   - Property: {property_obj.title}")
        self.stdout.write(f"   - Created: {inquiry.created_at}")
        self.stdout.write(f"   - Responded: {inquiry.response_date}")
        self.stdout.write(f"   - Seller notifications: {seller_notifications.count()}")
        self.stdout.write(f"   - Buyer notifications: {buyer_notifications.count()}")
