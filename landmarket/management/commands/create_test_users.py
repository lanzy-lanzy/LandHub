from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from landmarket.models import UserProfile, Land
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Create test users with different roles for testing dashboards'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing test users before creating new ones',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Deleting existing test users...')
            User.objects.filter(username__in=['admin_test', 'seller_test', 'buyer_test']).delete()

        # Create Admin User
        admin_user, created = User.objects.get_or_create(
            username='admin_test',
            defaults={
                'email': 'admin@landhub.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('admin123')
        admin_user.save()

        admin_profile, created = UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                'role': 'admin',
                'phone': '+1-555-0101',
                'bio': 'System administrator for LandHub platform.',
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created admin user: admin_test / admin123')
            )
        else:
            self.stdout.write(f'Admin user already exists: admin_test / admin123')

        # Create Seller User
        seller_user, created = User.objects.get_or_create(
            username='seller_test',
            defaults={
                'email': 'seller@landhub.com',
                'first_name': 'John',
                'last_name': 'Seller',
            }
        )
        seller_user.set_password('seller123')
        seller_user.save()

        seller_profile, created = UserProfile.objects.get_or_create(
            user=seller_user,
            defaults={
                'role': 'seller',
                'phone': '+1-555-0102',
                'bio': 'Experienced land seller with 10+ years in real estate.',
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created seller user: seller_test / seller123')
            )
        else:
            self.stdout.write(f'Seller user already exists: seller_test / seller123')

        # Create Buyer User
        buyer_user, created = User.objects.get_or_create(
            username='buyer_test',
            defaults={
                'email': 'buyer@landhub.com',
                'first_name': 'Jane',
                'last_name': 'Buyer',
            }
        )
        buyer_user.set_password('buyer123')
        buyer_user.save()

        buyer_profile, created = UserProfile.objects.get_or_create(
            user=buyer_user,
            defaults={
                'role': 'buyer',
                'phone': '+1-555-0103',
                'bio': 'Looking for agricultural and recreational land investments.',
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created buyer user: buyer_test / buyer123')
            )
        else:
            self.stdout.write(f'Buyer user already exists: buyer_test / buyer123')

        # Create sample listings for the seller
        self.create_sample_listings(seller_user)

        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🎉 TEST USERS CREATED SUCCESSFULLY!'))
        self.stdout.write('='*60)
        self.stdout.write('\n📋 LOGIN CREDENTIALS:')
        self.stdout.write(f'   🔧 Admin:  username=admin_test  | password=admin123')
        self.stdout.write(f'   🏪 Seller: username=seller_test | password=seller123')
        self.stdout.write(f'   🛒 Buyer:  username=buyer_test  | password=buyer123')
        self.stdout.write('\n🌐 LOGIN URL: http://127.0.0.1:8000/login/')
        self.stdout.write('='*60)

    def create_sample_listings(self, seller_user):
        """Create sample land listings for the seller"""
        sample_listings = [
            {
                'title': '50-Acre Agricultural Farm',
                'description': 'Prime agricultural land with fertile soil, perfect for farming operations. Includes water rights and existing irrigation system.',
                'price': Decimal('125000.00'),
                'size_acres': Decimal('50.0'),
                'property_type': 'agricultural',
                'location': 'Texas, USA',
                'address': '1234 Farm Road, Austin, TX 78701',
                'status': 'approved',
            },
            {
                'title': 'Mountain View Ranch',
                'description': 'Beautiful recreational property with stunning mountain views. Perfect for hunting, camping, or building a weekend retreat.',
                'price': Decimal('89000.00'),
                'size_acres': Decimal('25.0'),
                'property_type': 'recreational',
                'location': 'Colorado, USA',
                'address': '5678 Mountain Trail, Denver, CO 80201',
                'status': 'draft',
            },
            {
                'title': 'Residential Development Land',
                'description': 'Prime residential development opportunity in growing suburban area. Zoned for single-family homes.',
                'price': Decimal('200000.00'),
                'size_acres': Decimal('15.0'),
                'property_type': 'residential',
                'location': 'California, USA',
                'address': '9012 Development Ave, Los Angeles, CA 90210',
                'status': 'approved',
            },
            {
                'title': 'Commercial Corner Lot',
                'description': 'High-traffic commercial corner lot in downtown area. Perfect for retail or office development.',
                'price': Decimal('350000.00'),
                'size_acres': Decimal('2.5'),
                'property_type': 'commercial',
                'location': 'Florida, USA',
                'address': '3456 Main Street, Miami, FL 33101',
                'status': 'pending',
            },
            {
                'title': 'Organic Farm Opportunity',
                'description': 'Certified organic farmland with established crop rotation. Includes barn and equipment storage.',
                'price': Decimal('180000.00'),
                'size_acres': Decimal('75.0'),
                'property_type': 'agricultural',
                'location': 'Oregon, USA',
                'address': '7890 Organic Way, Portland, OR 97201',
                'status': 'approved',
            },
        ]

        for listing_data in sample_listings:
            listing, created = Land.objects.get_or_create(
                owner=seller_user,
                title=listing_data['title'],
                defaults=listing_data
            )
            if created:
                self.stdout.write(f'   📄 Created listing: {listing_data["title"]}')
