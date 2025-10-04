from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Land, LandImage, Inquiry, Favorite, Notification


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__role')
    
    def get_role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, 'profile') else 'No Profile'
    get_role.short_description = 'Role'


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register UserProfile separately for direct access
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone')
    readonly_fields = ('created_at', 'updated_at')


class LandImageInline(admin.TabularInline):
    model = LandImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'order')


@admin.register(Land)
class LandAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'location', 'price', 'size_acres', 'property_type', 'status', 'is_approved', 'created_at')
    list_filter = ('property_type', 'status', 'is_approved', 'created_at')
    search_fields = ('title', 'location', 'owner__username', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [LandImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'title', 'description')
        }),
        ('Property Details', {
            'fields': ('price', 'size_acres', 'location', 'address', 'property_type')
        }),
        ('Status & Approval', {
            'fields': ('status', 'is_approved', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LandImage)
class LandImageAdmin(admin.ModelAdmin):
    list_display = ('land', 'alt_text', 'is_primary', 'order', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('land__title', 'alt_text')
    readonly_fields = ('created_at',)


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('subject', 'buyer', 'land', 'is_read', 'created_at', 'response_date')
    list_filter = ('is_read', 'created_at', 'response_date')
    search_fields = ('subject', 'buyer__username', 'land__title', 'message')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Inquiry Details', {
            'fields': ('buyer', 'land', 'subject', 'message', 'is_read')
        }),
        ('Response', {
            'fields': ('seller_response', 'response_date')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'land', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'land__title')
    readonly_fields = ('created_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'sender', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__username', 'sender__username')
    readonly_fields = ('created_at', 'read_at')
    list_editable = ('is_read',)

    fieldsets = (
        ('Notification Details', {
            'fields': ('recipient', 'sender', 'notification_type', 'title', 'message')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Related Object', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipient', 'sender', 'content_type')
