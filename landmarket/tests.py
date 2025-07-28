from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from landmarket.models import UserProfile, Land, Inquiry, Favorite, SavedSearch, LandImage
from landmarket.forms import LandListingForm, UserProfileForm


class SellerFunctionalityTests(TestCase):
    """Test cases for seller functionality"""

    def setUp(self):
        """Set up test data"""
        # Create a seller user
        self.seller_user = User.objects.create_user(
            username='testseller',
            email='seller@test.com',
            password='testpass123'
        )
        self.seller_user.profile.role = 'seller'
        self.seller_user.profile.save()

        # Create a buyer user
        self.buyer_user = User.objects.create_user(
            username='testbuyer',
            email='buyer@test.com',
            password='testpass123'
        )
        self.buyer_user.profile.role = 'buyer'
        self.buyer_user.profile.save()

        # Create test listing
        self.test_listing = Land.objects.create(
            owner=self.seller_user,
            title='Test Property',
            description='A beautiful test property for sale',
            price=Decimal('100000.00'),
            size_acres=Decimal('10.5'),
            location='Test City, Test State',
            address='123 Test Street, Test City, Test State',
            property_type='residential',
            status='draft'
        )

        self.client = Client()

    def test_seller_dashboard_access(self):
        """Test that sellers can access their dashboard"""
        self.client.login(username='testseller', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seller Dashboard')

    def test_seller_my_listings_view(self):
        """Test seller can view their listings"""
        self.client.login(username='testseller', password='testpass123')
        response = self.client.get(reverse('seller_my_listings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Property')

    def test_seller_create_listing_get(self):
        """Test seller can access create listing form"""
        self.client.login(username='testseller', password='testpass123')
        response = self.client.get(reverse('seller_create_listing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Listing')

    def test_seller_create_listing_post(self):
        """Test seller can create a new listing"""
        self.client.login(username='testseller', password='testpass123')

        listing_data = {
            'title': 'New Test Property',
            'description': 'Another beautiful property for testing',
            'price': '150000.00',
            'size_acres': '20.0',
            'location': 'New Test City, Test State',
            'address': '456 New Test Street, New Test City, Test State',
            'property_type': 'agricultural',
            # Formset management form data
            'landimage_set-TOTAL_FORMS': '0',
            'landimage_set-INITIAL_FORMS': '0',
            'landimage_set-MIN_NUM_FORMS': '0',
            'landimage_set-MAX_NUM_FORMS': '10',
        }

        response = self.client.post(reverse('seller_create_listing'), data=listing_data)

        # Debug: Print response content if not redirecting
        if response.status_code != 302:
            print("Response status:", response.status_code)
            print("Response content:", response.content.decode()[:500])

        # Should redirect to edit page after successful creation
        self.assertEqual(response.status_code, 302)

        # Check that listing was created
        new_listing = Land.objects.filter(title='New Test Property').first()
        self.assertIsNotNone(new_listing)
        self.assertEqual(new_listing.owner, self.seller_user)
        self.assertEqual(new_listing.status, 'draft')

    def test_seller_edit_listing(self):
        """Test seller can edit their listing"""
        self.client.login(username='testseller', password='testpass123')

        edit_data = {
            'title': 'Updated Test Property',
            'description': self.test_listing.description,
            'price': '120000.00',
            'size_acres': str(self.test_listing.size_acres),
            'location': self.test_listing.location,
            'address': self.test_listing.address,
            'property_type': self.test_listing.property_type,
            # Formset management form data
            'landimage_set-TOTAL_FORMS': '0',
            'landimage_set-INITIAL_FORMS': '0',
            'landimage_set-MIN_NUM_FORMS': '0',
            'landimage_set-MAX_NUM_FORMS': '10',
        }

        response = self.client.post(
            reverse('seller_edit_listing', args=[self.test_listing.id]),
            data=edit_data
        )

        # Should redirect after successful edit
        self.assertEqual(response.status_code, 302)

        # Check that listing was updated
        updated_listing = Land.objects.get(id=self.test_listing.id)
        self.assertEqual(updated_listing.title, 'Updated Test Property')
        self.assertEqual(updated_listing.price, Decimal('120000.00'))

    def test_seller_inquiries_view(self):
        """Test seller can view inquiries about their listings"""
        # Create an inquiry
        inquiry = Inquiry.objects.create(
            buyer=self.buyer_user,
            land=self.test_listing,
            subject='Interested in your property',
            message='I would like to know more about this property.'
        )

        self.client.login(username='testseller', password='testpass123')
        response = self.client.get(reverse('seller_inquiries'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Interested in your property')

    def test_seller_profile_view(self):
        """Test seller can view and update their profile"""
        self.client.login(username='testseller', password='testpass123')
        response = self.client.get(reverse('seller_profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Profile')

    def test_non_seller_access_denied(self):
        """Test that non-sellers cannot access seller views"""
        self.client.login(username='testbuyer', password='testpass123')

        # Test various seller views
        seller_urls = [
            'seller_my_listings',
            'seller_create_listing',
            'seller_inquiries',
            'seller_profile',
        ]

        for url_name in seller_urls:
            response = self.client.get(reverse(url_name))
            # Should redirect to landing page
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, reverse('landing'))

    def test_listing_form_validation(self):
        """Test listing form validation"""
        # Test valid form
        valid_data = {
            'title': 'Valid Property Title',
            'description': 'This is a valid description with enough characters to pass validation.',
            'price': '100000.00',
            'size_acres': '10.5',
            'location': 'Valid City, Valid State',
            'address': '123 Valid Street, Valid City, Valid State',
            'property_type': 'residential',
        }

        form = LandListingForm(data=valid_data)
        self.assertTrue(form.is_valid())

        # Test invalid form - title too short
        invalid_data = valid_data.copy()
        invalid_data['title'] = 'Bad'

        form = LandListingForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)


class SellerReportsViewTests(TestCase):
    """Test cases for the seller_reports view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test users
        self.seller_user = User.objects.create_user(
            username='testseller',
            email='seller@test.com',
            password='testpass123'
        )

        self.buyer_user = User.objects.create_user(
            username='testbuyer',
            email='buyer@test.com',
            password='testpass123'
        )

        self.admin_user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123'
        )

        # Update user profiles (they are automatically created by signals)
        self.seller_profile = self.seller_user.profile
        self.seller_profile.role = 'seller'
        self.seller_profile.phone = '123-456-7890'
        self.seller_profile.save()

        self.buyer_profile = self.buyer_user.profile
        self.buyer_profile.role = 'buyer'
        self.buyer_profile.phone = '098-765-4321'
        self.buyer_profile.save()

        self.admin_profile = self.admin_user.profile
        self.admin_profile.role = 'admin'
        self.admin_profile.phone = '555-555-5555'
        self.admin_profile.save()

        # Create test listings for the seller
        self.listing1 = Land.objects.create(
            title='Test Property 1',
            description='A beautiful piece of land',
            price=Decimal('50000.00'),
            size_acres=Decimal('5.0'),
            location='Test Location 1',
            property_type='residential',
            status='approved',
            is_approved=True,
            owner=self.seller_user
        )

        self.listing2 = Land.objects.create(
            title='Test Property 2',
            description='Another great property',
            price=Decimal('75000.00'),
            size_acres=Decimal('10.0'),
            location='Test Location 2',
            property_type='commercial',
            status='approved',
            is_approved=True,
            owner=self.seller_user
        )

        self.listing3 = Land.objects.create(
            title='Test Property 3',
            description='Pending property',
            price=Decimal('30000.00'),
            size_acres=Decimal('3.0'),
            location='Test Location 3',
            property_type='agricultural',
            status='pending',
            is_approved=False,
            owner=self.seller_user
        )

        # Create test inquiries
        self.inquiry1 = Inquiry.objects.create(
            buyer=self.buyer_user,
            land=self.listing1,
            message='Interested in this property',
            is_read=True,
            seller_response='Thank you for your interest'
        )

        self.inquiry2 = Inquiry.objects.create(
            buyer=self.buyer_user,
            land=self.listing2,
            message='Can you provide more details?',
            is_read=False,
            seller_response=''
        )

        self.inquiry3 = Inquiry.objects.create(
            buyer=self.buyer_user,
            land=self.listing1,
            message='What is the zoning?',
            is_read=True,
            seller_response='Residential zoning'
        )

        # Create test favorites
        self.favorite1 = Favorite.objects.create(
            user=self.buyer_user,
            land=self.listing1
        )

        # Create competitor listings for market analysis
        self.competitor_user = User.objects.create_user(
            username='competitor',
            email='competitor@test.com',
            password='testpass123'
        )

        self.competitor_profile = self.competitor_user.profile
        self.competitor_profile.role = 'seller'
        self.competitor_profile.phone = '111-222-3333'
        self.competitor_profile.save()

        self.competitor_listing = Land.objects.create(
            title='Competitor Property',
            description='Competitor land',
            price=Decimal('55000.00'),
            size_acres=Decimal('5.5'),
            location='Competitor Location',
            property_type='residential',
            status='approved',
            is_approved=True,
            owner=self.competitor_user
        )

    def test_seller_reports_view_requires_login(self):
        """Test that seller_reports view requires authentication"""
        url = reverse('seller_reports')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('/login/', response.url)

    def test_seller_reports_view_requires_seller_role(self):
        """Test that seller_reports view requires seller role"""
        # Test with buyer user
        self.client.login(username='testbuyer', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect due to access denied

        # Test with admin user
        self.client.login(username='testadmin', password='testpass123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect due to access denied

    def test_seller_reports_view_success_for_seller(self):
        """Test that seller_reports view works for seller users"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Comprehensive Reports')
        self.assertContains(response, 'Performance Analytics')
        self.assertContains(response, 'Market Insights')
        self.assertContains(response, 'Resources & Tips')
        self.assertContains(response, 'Support & Help')

    def test_seller_reports_context_data(self):
        """Test that seller_reports view provides correct context data"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)

        # Check that all required context variables are present
        context = response.context

        # Performance Analytics context
        self.assertIn('total_listings', context)
        self.assertIn('active_listings', context)
        self.assertIn('pending_listings', context)
        self.assertIn('draft_listings', context)
        self.assertIn('total_value', context)
        self.assertIn('avg_price', context)
        self.assertIn('total_inquiries', context)
        self.assertIn('unread_inquiries', context)
        self.assertIn('responded_inquiries', context)
        self.assertIn('response_rate', context)
        self.assertIn('inquiries_per_listing', context)
        self.assertIn('recent_inquiries', context)
        self.assertIn('recent_listings', context)
        self.assertIn('top_listings', context)
        self.assertIn('property_type_performance', context)
        self.assertIn('monthly_inquiries', context)
        self.assertIn('favorites_count', context)

        # Market Insights context
        self.assertIn('total_market_listings', context)
        self.assertIn('seller_market_share', context)
        self.assertIn('market_avg_price', context)
        self.assertIn('seller_avg_price', context)
        self.assertIn('price_comparison', context)
        self.assertIn('seller_property_types', context)
        self.assertIn('market_property_types', context)
        self.assertIn('competitive_analysis', context)
        self.assertIn('recent_market_listings', context)
        self.assertIn('recommendations', context)

    def test_seller_reports_performance_calculations(self):
        """Test that performance metrics are calculated correctly"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)
        context = response.context

        # Test basic listing counts
        self.assertEqual(context['total_listings'], 3)  # 3 listings total
        self.assertEqual(context['active_listings'], 2)  # 2 approved listings
        self.assertEqual(context['pending_listings'], 1)  # 1 pending listing
        self.assertEqual(context['draft_listings'], 0)  # 0 draft listings

        # Test financial calculations
        expected_total_value = Decimal('125000.00')  # 50000 + 75000 (only approved)
        self.assertEqual(context['total_value'], expected_total_value)

        expected_avg_price = Decimal('62500.00')  # (50000 + 75000) / 2
        self.assertEqual(context['avg_price'], expected_avg_price)

        # Test inquiry statistics
        self.assertEqual(context['total_inquiries'], 3)  # 3 inquiries total
        self.assertEqual(context['unread_inquiries'], 1)  # 1 unread inquiry
        self.assertEqual(context['responded_inquiries'], 2)  # 2 with responses

        # Test response rate calculation
        expected_response_rate = (2 / 3) * 100  # 66.67%
        self.assertAlmostEqual(context['response_rate'], expected_response_rate, places=1)

        # Test inquiries per listing
        expected_inquiries_per_listing = 3 / 3  # 1.0
        self.assertEqual(context['inquiries_per_listing'], expected_inquiries_per_listing)

        # Test favorites count
        self.assertEqual(context['favorites_count'], 1)  # 1 favorite

    def test_seller_reports_market_calculations(self):
        """Test that market insights are calculated correctly"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)
        context = response.context

        # Test market share calculation
        # Total market listings: 3 (2 seller + 1 competitor)
        # Seller listings: 2 approved
        expected_market_share = (2 / 3) * 100  # 66.67%
        self.assertAlmostEqual(context['seller_market_share'], expected_market_share, places=1)

        # Test market average price
        # Market listings: 50000, 75000, 55000
        expected_market_avg = Decimal('60000')  # (50000 + 75000 + 55000) / 3
        self.assertAlmostEqual(float(context['market_avg_price']), float(expected_market_avg), places=2)

        # Test seller average price
        expected_seller_avg = Decimal('62500')  # (50000 + 75000) / 2
        self.assertEqual(context['seller_avg_price'], expected_seller_avg)

        # Test price comparison
        price_diff = Decimal('4.17')  # ((62500 - 60000) / 60000) * 100
        self.assertAlmostEqual(float(context['price_comparison']), float(price_diff), places=1)

    def test_seller_reports_property_type_performance(self):
        """Test property type performance analysis"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)
        context = response.context

        property_types = list(context['property_type_performance'])

        # Should have data for residential, commercial, and agricultural
        property_type_names = [pt['property_type'] for pt in property_types]
        self.assertIn('residential', property_type_names)
        self.assertIn('commercial', property_type_names)
        self.assertIn('agricultural', property_type_names)

        # Find residential property type data
        residential_data = next(pt for pt in property_types if pt['property_type'] == 'residential')

        # Test setup creates:
        # - listing1: residential, approved (seller) with 2 inquiries
        # - listing2: commercial, approved (seller) with 1 inquiry
        # - listing3: agricultural, pending (seller) with 0 inquiries
        self.assertEqual(residential_data['count'], 1)  # 1 residential listing
        self.assertEqual(residential_data['inquiry_count'], 2)  # 2 inquiries for residential

    def test_seller_reports_monthly_trends(self):
        """Test monthly inquiry trends calculation"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)
        context = response.context

        monthly_inquiries = context['monthly_inquiries']

        # Should have 6 months of data
        self.assertEqual(len(monthly_inquiries), 6)

        # Each month should have 'month' and 'count' keys
        for month_data in monthly_inquiries:
            self.assertIn('month', month_data)
            self.assertIn('count', month_data)
            self.assertIsInstance(month_data['count'], int)

    def test_seller_reports_top_listings(self):
        """Test top performing listings calculation"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)
        context = response.context

        top_listings = list(context['top_listings'])

        # Should be ordered by inquiry count (descending)
        if len(top_listings) > 1:
            for i in range(len(top_listings) - 1):
                self.assertGreaterEqual(
                    top_listings[i].inquiry_count,
                    top_listings[i + 1].inquiry_count
                )

    def test_seller_reports_competitive_analysis(self):
        """Test competitive analysis calculation"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)
        context = response.context

        competitive_analysis = context['competitive_analysis']

        # Should have analysis data
        self.assertIsInstance(competitive_analysis, list)

        # Each analysis should have required fields
        for analysis in competitive_analysis:
            self.assertIn('listing', analysis)
            self.assertIn('competitor_count', analysis)
            self.assertIn('avg_competitor_price', analysis)
            self.assertIn('price_position', analysis)
            self.assertIn('price_difference', analysis)

            # Price position should be one of the expected values
            self.assertIn(analysis['price_position'], ['below_market', 'above_market', 'competitive'])


class SellerReportsURLTests(TestCase):
    """Test cases for seller reports URL patterns"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test seller user
        self.seller_user = User.objects.create_user(
            username='testseller',
            email='seller@test.com',
            password='testpass123'
        )

        self.seller_profile = self.seller_user.profile
        self.seller_profile.role = 'seller'
        self.seller_profile.phone = '123-456-7890'
        self.seller_profile.save()

    def test_seller_reports_url_resolves(self):
        """Test that seller reports URL resolves correctly"""
        url = reverse('seller_reports')
        self.assertEqual(url, '/seller/reports/')

    def test_old_seller_urls_return_404(self):
        """Test that old removed URLs return 404"""
        self.client.login(username='testseller', password='testpass123')

        # These URLs should no longer exist
        old_urls = [
            '/seller/performance/',
            '/seller/market-insights/',
            '/seller/resources/',
            '/seller/support/'
        ]

        for url in old_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404, f"URL {url} should return 404")

    def test_seller_reports_url_accessible(self):
        """Test that seller reports URL is accessible to sellers"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class SellerReportsTemplateTests(TestCase):
    """Test cases for seller reports template rendering"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test seller user
        self.seller_user = User.objects.create_user(
            username='testseller',
            email='seller@test.com',
            password='testpass123'
        )

        self.seller_profile = self.seller_user.profile
        self.seller_profile.role = 'seller'
        self.seller_profile.phone = '123-456-7890'
        self.seller_profile.save()

        # Create test buyer
        self.buyer_user = User.objects.create_user(
            username='testbuyer',
            email='buyer@test.com',
            password='testpass123'
        )

        self.buyer_profile = self.buyer_user.profile
        self.buyer_profile.role = 'buyer'
        self.buyer_profile.save()

        # Create test listing
        self.listing = Land.objects.create(
            title='Test Property',
            description='A test property',
            price=Decimal('50000.00'),
            size_acres=Decimal('5.0'),
            location='Test Location',
            property_type='residential',
            status='approved',
            is_approved=True,
            owner=self.seller_user
        )

        # Create test inquiry so listing appears in top performing listings
        self.inquiry = Inquiry.objects.create(
            buyer=self.buyer_user,
            land=self.listing,
            message='Test inquiry',
            is_read=False,
            seller_response=''
        )

    def test_seller_reports_template_used(self):
        """Test that correct template is used"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'dashboards/seller_reports.html')
        self.assertTemplateUsed(response, 'dashboards/base_dashboard.html')

    def test_seller_reports_template_content(self):
        """Test that template contains expected content"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)

        # Check for tab navigation
        self.assertContains(response, 'Performance Analytics')
        self.assertContains(response, 'Market Insights')
        self.assertContains(response, 'Resources & Tips')
        self.assertContains(response, 'Support & Help')

        # Check for performance metrics
        self.assertContains(response, 'Portfolio Value')
        self.assertContains(response, 'Average Price')
        self.assertContains(response, 'Response Rate')
        self.assertContains(response, 'Avg. Inquiries')

        # Check for market insights
        self.assertContains(response, 'Market Share')
        self.assertContains(response, 'vs Market Avg')
        self.assertContains(response, 'Total Market')

        # Check for resources content
        self.assertContains(response, 'Success Tips')
        self.assertContains(response, 'Listing Optimization')
        self.assertContains(response, 'Marketing & Promotion')

        # Check for support content
        self.assertContains(response, 'Email Support')
        self.assertContains(response, 'Phone Support')
        self.assertContains(response, 'Live Chat')
        self.assertContains(response, 'Frequently Asked Questions')

    def test_seller_reports_template_data_display(self):
        """Test that template displays data correctly"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)

        # Check that listing data is displayed
        self.assertContains(response, '$50000')  # Price should be formatted (floatformat:0 doesn't add commas)
        self.assertContains(response, 'Test Property')  # Listing title

        # Check that counts are displayed
        self.assertContains(response, '1')  # Should show 1 listing

    def test_seller_reports_template_javascript(self):
        """Test that template includes necessary JavaScript"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)

        # Check for Alpine.js data attributes
        self.assertContains(response, 'x-data')
        self.assertContains(response, 'activeTab')
        self.assertContains(response, '@click')

    def test_seller_reports_template_responsive_design(self):
        """Test that template includes responsive design classes"""
        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)

        # Check for responsive grid classes
        self.assertContains(response, 'grid-cols-1')
        self.assertContains(response, 'md:grid-cols-2')
        self.assertContains(response, 'lg:grid-cols-4')


class SellerReportsIntegrationTests(TestCase):
    """Integration tests for seller reports functionality"""

    def setUp(self):
        """Set up comprehensive test data"""
        self.client = Client()

        # Create test users
        self.seller_user = User.objects.create_user(
            username='testseller',
            email='seller@test.com',
            password='testpass123'
        )

        self.buyer_user = User.objects.create_user(
            username='testbuyer',
            email='buyer@test.com',
            password='testpass123'
        )

        # Update user profiles (they are automatically created by signals)
        self.seller_profile = self.seller_user.profile
        self.seller_profile.role = 'seller'
        self.seller_profile.phone = '123-456-7890'
        self.seller_profile.save()

        self.buyer_profile = self.buyer_user.profile
        self.buyer_profile.role = 'buyer'
        self.buyer_profile.phone = '098-765-4321'
        self.buyer_profile.save()

        # Create multiple listings with different statuses
        self.approved_listing = Land.objects.create(
            title='Approved Property',
            description='An approved property',
            price=Decimal('100000.00'),
            size_acres=Decimal('10.0'),
            location='Approved Location',
            property_type='residential',
            status='approved',
            is_approved=True,
            owner=self.seller_user
        )

        self.pending_listing = Land.objects.create(
            title='Pending Property',
            description='A pending property',
            price=Decimal('75000.00'),
            size_acres=Decimal('7.5'),
            location='Pending Location',
            property_type='commercial',
            status='pending',
            is_approved=False,
            owner=self.seller_user
        )

        # Create inquiries with different timestamps
        self.recent_inquiry = Inquiry.objects.create(
            buyer=self.buyer_user,
            land=self.approved_listing,
            message='Recent inquiry',
            is_read=False,
            seller_response='',
            created_at=timezone.now() - timedelta(days=5)
        )

        self.old_inquiry = Inquiry.objects.create(
            buyer=self.buyer_user,
            land=self.approved_listing,
            message='Old inquiry',
            is_read=True,
            seller_response='Thank you',
            created_at=timezone.now() - timedelta(days=45)
        )

        # Create favorites
        self.favorite = Favorite.objects.create(
            user=self.buyer_user,
            land=self.approved_listing
        )

    def test_complete_seller_reports_flow(self):
        """Test complete flow from login to viewing reports"""
        # Test login
        login_successful = self.client.login(username='testseller', password='testpass123')
        self.assertTrue(login_successful)

        # Test accessing reports
        url = reverse('seller_reports')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Test that all data is present and correct
        context = response.context

        # Verify performance data
        self.assertEqual(context['total_listings'], 2)
        self.assertEqual(context['active_listings'], 1)
        self.assertEqual(context['pending_listings'], 1)
        self.assertEqual(context['total_inquiries'], 2)
        self.assertEqual(context['unread_inquiries'], 1)

        # Verify market data
        self.assertGreater(context['total_market_listings'], 0)
        self.assertIsNotNone(context['seller_market_share'])

        # Verify template rendering
        self.assertContains(response, 'Comprehensive Reports')
        self.assertContains(response, '$100000')  # Approved listing price (floatformat:0 doesn't add commas)
        self.assertContains(response, 'Approved Property')  # Listing title

    def test_seller_reports_with_no_data(self):
        """Test seller reports when seller has no listings"""
        # Create seller with no listings
        empty_seller = User.objects.create_user(
            username='emptyseller',
            email='empty@test.com',
            password='testpass123'
        )

        empty_seller_profile = empty_seller.profile
        empty_seller_profile.role = 'seller'
        empty_seller_profile.phone = '000-000-0000'
        empty_seller_profile.save()

        self.client.login(username='emptyseller', password='testpass123')
        url = reverse('seller_reports')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Check that zero values are handled correctly
        context = response.context
        self.assertEqual(context['total_listings'], 0)
        self.assertEqual(context['active_listings'], 0)
        self.assertEqual(context['total_inquiries'], 0)
        self.assertEqual(context['total_value'], 0)

    def test_seller_reports_performance_under_load(self):
        """Test seller reports performance with larger dataset"""
        # Create many listings and inquiries
        for i in range(50):
            listing = Land.objects.create(
                title=f'Property {i}',
                description=f'Description {i}',
                price=Decimal(f'{10000 + i * 1000}.00'),
                size_acres=Decimal(f'{i + 1}.0'),
                location=f'Location {i}',
                property_type='residential',
                status='approved',
                is_approved=True,
                owner=self.seller_user
            )

            # Create inquiries for some listings
            if i % 3 == 0:
                Inquiry.objects.create(
                    buyer=self.buyer_user,
                    land=listing,
                    message=f'Inquiry for property {i}',
                    is_read=i % 2 == 0,
                    seller_response='Response' if i % 4 == 0 else ''
                )

        self.client.login(username='testseller', password='testpass123')
        url = reverse('seller_reports')

        # Measure response time
        import time
        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()

        self.assertEqual(response.status_code, 200)

        # Response should be reasonably fast (less than 5 seconds)
        response_time = end_time - start_time
        self.assertLess(response_time, 5.0, f"Response took {response_time:.2f} seconds")

        # Verify data is still correct
        context = response.context
        self.assertEqual(context['total_listings'], 52)  # 50 + 2 from setUp
        self.assertEqual(context['active_listings'], 51)  # 50 + 1 from setUp
