from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('seller', 'Seller'),
        ('buyer', 'Buyer'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='buyer')
    phone = models.CharField(max_length=15, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


class Land(models.Model):
    PROPERTY_TYPES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('agricultural', 'Agricultural'),
        ('recreational', 'Recreational'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('sold', 'Sold'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='land_listings')
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    size_acres = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=200)
    address = models.TextField()
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_approved = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.location}"
    
    class Meta:
        verbose_name = "Land Listing"
        verbose_name_plural = "Land Listings"
        ordering = ['-created_at']


class LandImage(models.Model):
    land = models.ForeignKey(Land, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='listings/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for {self.land.title} - {'Primary' if self.is_primary else 'Secondary'}"
    
    class Meta:
        verbose_name = "Land Image"
        verbose_name_plural = "Land Images"
        ordering = ['order', '-created_at']


class Inquiry(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inquiries_sent')
    land = models.ForeignKey(Land, on_delete=models.CASCADE, related_name='inquiries')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    seller_response = models.TextField(blank=True)
    response_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Inquiry from {self.buyer.username} about {self.land.title}"
    
    class Meta:
        verbose_name = "Inquiry"
        verbose_name_plural = "Inquiries"
        ordering = ['-created_at']


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    land = models.ForeignKey(Land, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} favorited {self.land.title}"

    class Meta:
        verbose_name = "Favorite"
        verbose_name_plural = "Favorites"
        unique_together = ('user', 'land')
        ordering = ['-created_at']


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('inquiry_new', 'New Inquiry'),
        ('inquiry_response', 'Inquiry Response'),
        ('listing_approved', 'Listing Approved'),
        ('listing_rejected', 'Listing Rejected'),
        ('listing_pending', 'Listing Pending Approval'),
        ('property_favorited', 'Property Favorited'),
        ('system_welcome', 'Welcome Message'),
        ('system_update', 'System Update'),
        ('admin_message', 'Admin Message'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Generic foreign key to link to any model (Land, Inquiry, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    # Additional metadata as JSON (stored as text for SQLite compatibility)
    metadata = models.TextField(default='{}', blank=True)

    def get_metadata(self):
        """Get metadata as dict"""
        import json
        try:
            return json.loads(self.metadata) if self.metadata else {}
        except json.JSONDecodeError:
            return {}

    def set_metadata(self, data):
        """Set metadata from dict"""
        import json
        self.metadata = json.dumps(data) if data else '{}'

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_as_unread(self):
        """Mark notification as unread"""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])

    def get_action_url(self):
        """Get the URL for the action related to this notification"""
        if self.notification_type in ['inquiry_new', 'inquiry_response'] and self.related_object:
            if hasattr(self.related_object, 'id'):
                if self.recipient.profile.role == 'seller':
                    return f'/seller/inquiries/{self.related_object.id}/'
                else:
                    return f'/buyer/inquiries/{self.related_object.id}/'
        elif self.notification_type in ['listing_approved', 'listing_rejected', 'listing_pending'] and self.related_object:
            if hasattr(self.related_object, 'id'):
                return f'/seller/listings/{self.related_object.id}/edit/'
        elif self.notification_type == 'property_favorited' and self.related_object:
            if hasattr(self.related_object, 'land'):
                return f'/buyer/property/{self.related_object.land.id}/'
        return '/notifications/'

    def __str__(self):
        return f"{self.title} - {self.recipient.username}"

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'created_at']),
            models.Index(fields=['notification_type']),
        ]


class SavedSearch(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_searches')
    name = models.CharField(max_length=100, help_text="Name for this saved search")
    search_query = models.CharField(max_length=200, blank=True, help_text="Search keywords")
    location_filter = models.CharField(max_length=200, blank=True, help_text="Location filter")
    property_type_filter = models.CharField(max_length=20, choices=Land.PROPERTY_TYPES, blank=True, help_text="Property type filter")
    min_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Minimum price")
    max_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Maximum price")
    min_size = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Minimum size in acres")
    max_size = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Maximum size in acres")
    email_alerts = models.BooleanField(default=True, help_text="Send email alerts for new matching properties")
    is_active = models.BooleanField(default=True, help_text="Whether this search is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_alert_sent = models.DateTimeField(null=True, blank=True, help_text="When the last alert was sent")

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    def get_search_url(self):
        """Generate URL for this saved search"""
        from django.urls import reverse
        from urllib.parse import urlencode

        params = {}
        if self.search_query:
            params['search'] = self.search_query
        if self.location_filter:
            params['location'] = self.location_filter
        if self.property_type_filter:
            params['property_type'] = self.property_type_filter
        if self.min_price:
            params['min_price'] = str(self.min_price)
        if self.max_price:
            params['max_price'] = str(self.max_price)
        if self.min_size:
            params['min_size'] = str(self.min_size)
        if self.max_size:
            params['max_size'] = str(self.max_size)

        base_url = reverse('buyer_browse_listings')
        if params:
            return f"{base_url}?{urlencode(params)}"
        return base_url

    def get_matching_properties_count(self):
        """Get count of properties matching this search"""
        from django.db.models import Q

        queryset = Land.objects.filter(status='approved', is_approved=True)

        if self.search_query:
            queryset = queryset.filter(
                Q(title__icontains=self.search_query) |
                Q(description__icontains=self.search_query) |
                Q(location__icontains=self.search_query)
            )

        if self.location_filter:
            queryset = queryset.filter(location__icontains=self.location_filter)

        if self.property_type_filter:
            queryset = queryset.filter(property_type=self.property_type_filter)

        if self.min_price:
            queryset = queryset.filter(price__gte=self.min_price)

        if self.max_price:
            queryset = queryset.filter(price__lte=self.max_price)

        if self.min_size:
            queryset = queryset.filter(size_acres__gte=self.min_size)

        if self.max_size:
            queryset = queryset.filter(size_acres__lte=self.max_size)

        return queryset.count()

    class Meta:
        verbose_name = "Saved Search"
        verbose_name_plural = "Saved Searches"
        ordering = ['-created_at']
