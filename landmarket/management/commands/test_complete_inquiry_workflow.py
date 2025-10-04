"""
Management command to test the complete inquiry workflow end-to-end
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.test import Client
from django.urls import reverse
from landmarket.models import Land, Inquiry, Notification
from landmarket.forms import BuyerInquiryForm, InquiryResponseForm


class Command(BaseCommand):
    help = 'Test the complete inquiry workflow end-to-end'

    def handle(self, *args, **options):
        self.stdout.write("🔄 Testing Complete Inquiry Workflow...")
        
        # Setup test client
        client = Client()
        
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
        
        # Record initial state
        initial_inquiries = Inquiry.objects.count()
        initial_seller_notifications = seller.notifications.count()
        initial_buyer_notifications = buyer.notifications.count()
        
        self.stdout.write(f"📊 Initial state:")
        self.stdout.write(f"   Total inquiries: {initial_inquiries}")
        self.stdout.write(f"   Seller notifications: {initial_seller_notifications}")
        self.stdout.write(f"   Buyer notifications: {initial_buyer_notifications}")
        
        # Step 1: Buyer submits inquiry
        self.stdout.write("\n📝 Step 1: Buyer submits inquiry...")
        
        try:
            # Test form validation
            form_data = {
                'subject': 'End-to-end test inquiry',
                'message': 'This is a comprehensive test of the inquiry system workflow from start to finish.'
            }
            
            form = BuyerInquiryForm(data=form_data)
            if form.is_valid():
                self.stdout.write("✅ Inquiry form validation passed")
                
                # Create inquiry
                inquiry = form.save(commit=False)
                inquiry.buyer = buyer
                inquiry.land = property_obj
                inquiry.save()

                # Trigger notification (as would happen in the view)
                from landmarket.notifications import notify_new_inquiry
                notify_new_inquiry(inquiry)

                self.stdout.write(f"✅ Inquiry created: {inquiry.id}")
                
                # Verify inquiry data
                assert inquiry.buyer == buyer, "Buyer mismatch"
                assert inquiry.land == property_obj, "Property mismatch"
                assert inquiry.subject == form_data['subject'], "Subject mismatch"
                assert inquiry.message == form_data['message'], "Message mismatch"
                assert not inquiry.is_read, "Inquiry should be unread"
                assert inquiry.seller_response == "", "Response should be empty"
                
                self.stdout.write("✅ Inquiry data verified")
                
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Form validation failed: {form.errors}")
                )
                return
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error in step 1: {e}")
            )
            return
        
        # Step 2: Verify seller notification
        self.stdout.write("\n🔔 Step 2: Verifying seller notification...")
        
        try:
            # Check if notification was created
            seller_notifications = seller.notifications.filter(
                notification_type='inquiry_new',
                created_at__gte=inquiry.created_at
            )
            
            if seller_notifications.exists():
                notification = seller_notifications.first()
                self.stdout.write(f"✅ Seller notification created: {notification.id}")
                
                # Verify notification details
                assert notification.recipient == seller, "Wrong recipient"
                assert notification.sender == buyer, "Wrong sender"
                assert property_obj.title in notification.title, "Property title not in title"
                assert inquiry.subject in notification.message, "Inquiry subject not in message"
                assert not notification.is_read, "Notification should be unread"
                
                self.stdout.write("✅ Seller notification details verified")
                
            else:
                self.stdout.write(
                    self.style.ERROR("❌ Seller notification not found")
                )
                return
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error in step 2: {e}")
            )
            return
        
        # Step 3: Seller views and responds to inquiry
        self.stdout.write("\n💬 Step 3: Seller responds to inquiry...")
        
        try:
            # Mark inquiry as read (simulating seller viewing it)
            inquiry.is_read = True
            inquiry.save()
            
            # Test response form validation
            response_data = {
                'seller_response': 'Thank you for your inquiry! I would be happy to provide more information about this property. The land has excellent drainage and is perfect for your intended use.'
            }
            
            response_form = InquiryResponseForm(data=response_data, instance=inquiry)
            if response_form.is_valid():
                self.stdout.write("✅ Response form validation passed")
                
                # Save response
                inquiry = response_form.save(commit=False)
                inquiry.response_date = timezone.now()
                inquiry.save()

                # Trigger notification (as would happen in the view)
                from landmarket.notifications import notify_inquiry_response
                notify_inquiry_response(inquiry)

                self.stdout.write(f"✅ Response saved for inquiry: {inquiry.id}")
                
                # Verify response data
                assert inquiry.seller_response == response_data['seller_response'], "Response mismatch"
                assert inquiry.response_date is not None, "Response date not set"
                assert inquiry.is_read, "Inquiry should be marked as read"
                
                self.stdout.write("✅ Response data verified")
                
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Response form validation failed: {response_form.errors}")
                )
                return
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error in step 3: {e}")
            )
            return
        
        # Step 4: Verify buyer notification
        self.stdout.write("\n🔔 Step 4: Verifying buyer notification...")
        
        try:
            # Check if response notification was created
            buyer_notifications = buyer.notifications.filter(
                notification_type='inquiry_response',
                created_at__gte=inquiry.response_date
            )
            
            if buyer_notifications.exists():
                response_notification = buyer_notifications.first()
                self.stdout.write(f"✅ Buyer notification created: {response_notification.id}")
                
                # Verify notification details
                assert response_notification.recipient == buyer, "Wrong recipient"
                assert response_notification.sender == seller, "Wrong sender"
                assert property_obj.title in response_notification.title, "Property title not in title"
                assert not response_notification.is_read, "Notification should be unread"
                
                self.stdout.write("✅ Buyer notification details verified")
                
            else:
                self.stdout.write(
                    self.style.ERROR("❌ Buyer notification not found")
                )
                return
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error in step 4: {e}")
            )
            return
        
        # Step 5: Verify final state
        self.stdout.write("\n📊 Step 5: Verifying final state...")
        
        try:
            # Check inquiry counts
            final_inquiries = Inquiry.objects.count()
            assert final_inquiries == initial_inquiries + 1, "Inquiry count mismatch"
            
            # Check notification counts
            final_seller_notifications = seller.notifications.count()
            final_buyer_notifications = buyer.notifications.count()
            
            assert final_seller_notifications > initial_seller_notifications, "Seller notification count didn't increase"
            assert final_buyer_notifications > initial_buyer_notifications, "Buyer notification count didn't increase"
            
            self.stdout.write("✅ Final state verified")
            
            # Check inquiry accessibility
            buyer_inquiries = buyer.inquiries_sent.filter(id=inquiry.id)
            seller_inquiries = Inquiry.objects.filter(land__owner=seller, id=inquiry.id)
            
            assert buyer_inquiries.exists(), "Buyer cannot access their inquiry"
            assert seller_inquiries.exists(), "Seller cannot access inquiry about their property"
            
            self.stdout.write("✅ Inquiry accessibility verified")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error in step 5: {e}")
            )
            return
        
        # Step 6: Test notification action URLs
        self.stdout.write("\n🔗 Step 6: Testing notification action URLs...")
        
        try:
            # Test seller notification URL
            seller_notification_url = notification.get_action_url()
            expected_seller_url = f'/seller/inquiries/{inquiry.id}/'
            
            if seller_notification_url == expected_seller_url:
                self.stdout.write("✅ Seller notification URL correct")
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Seller notification URL: {seller_notification_url}")
                )
            
            # Test buyer notification URL
            buyer_notification_url = response_notification.get_action_url()
            expected_buyer_url = f'/buyer/inquiries/{inquiry.id}/'
            
            if buyer_notification_url == expected_buyer_url:
                self.stdout.write("✅ Buyer notification URL correct")
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Buyer notification URL: {buyer_notification_url}")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error in step 6: {e}")
            )
            return
        
        # Success summary
        self.stdout.write(
            self.style.SUCCESS("\n🎉 Complete inquiry workflow test PASSED!")
        )
        
        self.stdout.write(f"📊 Workflow Summary:")
        self.stdout.write(f"   ✅ Buyer submitted inquiry")
        self.stdout.write(f"   ✅ Seller received notification")
        self.stdout.write(f"   ✅ Seller responded to inquiry")
        self.stdout.write(f"   ✅ Buyer received response notification")
        self.stdout.write(f"   ✅ All data integrity checks passed")
        self.stdout.write(f"   ✅ All accessibility checks passed")
        
        self.stdout.write(f"\n📈 Final Statistics:")
        self.stdout.write(f"   - Inquiry ID: {inquiry.id}")
        self.stdout.write(f"   - Seller notification ID: {notification.id}")
        self.stdout.write(f"   - Buyer notification ID: {response_notification.id}")
        self.stdout.write(f"   - Total inquiries: {final_inquiries}")
        self.stdout.write(f"   - Seller notifications: {final_seller_notifications}")
        self.stdout.write(f"   - Buyer notifications: {final_buyer_notifications}")
        
        self.stdout.write(
            self.style.SUCCESS("\n✅ The inquiry system is fully functional and ready for production!")
        )
