from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.files.images import get_image_dimensions
from decimal import Decimal
import os
from .models import Land, LandImage, Inquiry, UserProfile, SavedSearch, Favorite


class LandListingForm(forms.ModelForm):
    """Form for creating and editing land listings"""
    
    class Meta:
        model = Land
        fields = [
            'title', 'description', 'price', 'size_acres', 
            'location', 'address', 'property_type'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': 'Enter a descriptive title for your property'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'rows': 6,
                'placeholder': 'Describe your property in detail, including features, amenities, and unique selling points'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'size_acres': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': 'City, State, Country'
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'rows': 3,
                'placeholder': 'Full address or detailed location description'
            }),
            'property_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors'
            })
        }
        labels = {
            'title': 'Property Title',
            'description': 'Property Description',
            'price': 'Price ($)',
            'size_acres': 'Size (Acres)',
            'location': 'Location',
            'address': 'Address',
            'property_type': 'Property Type'
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise ValidationError('Price must be greater than zero.')
        if price is not None and price > Decimal('999999999.99'):
            raise ValidationError('Price cannot exceed $999,999,999.99.')
        return price

    def clean_size_acres(self):
        size_acres = self.cleaned_data.get('size_acres')
        if size_acres is not None and size_acres <= 0:
            raise ValidationError('Size must be greater than zero acres.')
        if size_acres is not None and size_acres > Decimal('99999.99'):
            raise ValidationError('Size cannot exceed 99,999.99 acres.')
        return size_acres

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title and len(title.strip()) < 5:
            raise ValidationError('Title must be at least 5 characters long.')
        return title.strip() if title else title

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description.strip()) < 20:
            raise ValidationError('Description must be at least 20 characters long.')
        return description.strip() if description else description


class LandImageForm(forms.ModelForm):
    """Form for uploading land images"""
    
    class Meta:
        model = LandImage
        fields = ['image', 'alt_text', 'is_primary']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'accept': 'image/*'
            }),
            'alt_text': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': 'Describe this image for accessibility'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500 focus:ring-2'
            })
        }
        labels = {
            'image': 'Image File',
            'alt_text': 'Image Description',
            'is_primary': 'Set as Primary Image'
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (max 10MB)
            if image.size > 10 * 1024 * 1024:
                raise ValidationError('Image file size cannot exceed 10MB.')

            # Check file type by extension and content type
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']

            # Get file extension
            file_extension = os.path.splitext(image.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise ValidationError('Only JPEG, PNG, and WebP images are allowed.')

            # Check content type if available
            if hasattr(image, 'content_type') and image.content_type not in allowed_types:
                raise ValidationError('Invalid image format. Only JPEG, PNG, and WebP images are allowed.')

            # Check image dimensions
            try:
                width, height = get_image_dimensions(image)
                if width and height:
                    # Minimum dimensions check
                    if width < 300 or height < 200:
                        raise ValidationError('Image must be at least 300x200 pixels.')

                    # Maximum dimensions check (prevent extremely large images)
                    if width > 5000 or height > 5000:
                        raise ValidationError('Image dimensions cannot exceed 5000x5000 pixels.')
            except Exception:
                raise ValidationError('Invalid image file. Please upload a valid image.')

        return image


# Create formset for multiple image uploads
LandImageFormSet = forms.inlineformset_factory(
    Land, 
    LandImage, 
    form=LandImageForm,
    extra=3,  # Show 3 empty forms by default
    max_num=10,  # Maximum 10 images per listing
    can_delete=True,
    validate_max=True
)


class InquiryResponseForm(forms.ModelForm):
    """Form for sellers to respond to buyer inquiries"""
    
    class Meta:
        model = Inquiry
        fields = ['seller_response']
        widgets = {
            'seller_response': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'rows': 6,
                'placeholder': 'Type your response to the buyer here...'
            })
        }
        labels = {
            'seller_response': 'Your Response'
        }

    def clean_seller_response(self):
        response = self.cleaned_data.get('seller_response')
        if response and len(response.strip()) < 10:
            raise ValidationError('Response must be at least 10 characters long.')
        return response.strip() if response else response


class UserProfileForm(forms.ModelForm):
    """Form for updating seller profile information"""
    
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
            'placeholder': 'Last Name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
            'placeholder': 'Email Address'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = ['phone', 'bio', 'avatar']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': '+1 (555) 123-4567'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'rows': 4,
                'placeholder': 'Tell buyers about yourself and your experience with land sales...'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'accept': 'image/*'
            })
        }
        labels = {
            'phone': 'Phone Number',
            'bio': 'About You',
            'avatar': 'Profile Picture'
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Check file size (max 5MB)
            if avatar.size > 5 * 1024 * 1024:
                raise ValidationError('Avatar file size cannot exceed 5MB.')

            # Check file type by extension and content type
            allowed_extensions = ['.jpg', '.jpeg', '.png']
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png']

            # Get file extension
            file_extension = os.path.splitext(avatar.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise ValidationError('Only JPEG and PNG images are allowed for avatars.')

            # Check content type if available
            if hasattr(avatar, 'content_type') and avatar.content_type not in allowed_types:
                raise ValidationError('Invalid image format. Only JPEG and PNG images are allowed for avatars.')

            # Check image dimensions
            try:
                width, height = get_image_dimensions(avatar)
                if width and height:
                    # Minimum dimensions check for avatar
                    if width < 100 or height < 100:
                        raise ValidationError('Avatar image must be at least 100x100 pixels.')

                    # Maximum dimensions check
                    if width > 2000 or height > 2000:
                        raise ValidationError('Avatar image dimensions cannot exceed 2000x2000 pixels.')
            except Exception:
                raise ValidationError('Invalid image file. Please upload a valid image.')

        return avatar

    def save(self, commit=True):
        profile = super().save(commit=False)
        
        if commit:
            # Update User model fields
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.save()
            
            # Save profile
            profile.save()
        
        return profile


class ListingSearchForm(forms.Form):
    """Form for searching and filtering seller's own listings"""

    SEARCH_CHOICES = [
        ('', 'All Listings'),
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('sold', 'Sold'),
    ]

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
            'placeholder': 'Search your listings...'
        })
    )

    status = forms.ChoiceField(
        choices=SEARCH_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors'
        })
    )

    property_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Land.PROPERTY_TYPES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors'
        })
    )


# ============================================================================
# BUYER FORMS
# ============================================================================

class PropertySearchForm(forms.Form):
    """Form for buyers to search and filter available properties"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
            'placeholder': 'Search properties by title, description, or location...'
        }),
        label='Search Keywords'
    )

    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
            'placeholder': 'City, State, or Region'
        }),
        label='Location'
    )

    property_type = forms.ChoiceField(
        choices=[('', 'All Property Types')] + Land.PROPERTY_TYPES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors'
        }),
        label='Property Type'
    )

    min_price = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
            'placeholder': '0',
            'step': '1000',
            'min': '0'
        }),
        label='Min Price ($)'
    )

    max_price = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
            'placeholder': '1000000',
            'step': '1000',
            'min': '0'
        }),
        label='Max Price ($)'
    )

    min_size = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
            'placeholder': '0',
            'step': '0.1',
            'min': '0'
        }),
        label='Min Size (Acres)'
    )

    max_size = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
            'placeholder': '1000',
            'step': '0.1',
            'min': '0'
        }),
        label='Max Size (Acres)'
    )

    sort_by = forms.ChoiceField(
        choices=[
            ('', 'Relevance'),
            ('price_asc', 'Price: Low to High'),
            ('price_desc', 'Price: High to Low'),
            ('size_asc', 'Size: Small to Large'),
            ('size_desc', 'Size: Large to Small'),
            ('newest', 'Newest First'),
            ('oldest', 'Oldest First'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors'
        }),
        label='Sort By'
    )

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        min_size = cleaned_data.get('min_size')
        max_size = cleaned_data.get('max_size')

        # Validate price range
        if min_price and max_price and min_price > max_price:
            raise ValidationError('Minimum price cannot be greater than maximum price.')

        # Validate size range
        if min_size and max_size and min_size > max_size:
            raise ValidationError('Minimum size cannot be greater than maximum size.')

        return cleaned_data


class SavedSearchForm(forms.ModelForm):
    """Form for creating and editing saved searches"""

    class Meta:
        model = SavedSearch
        fields = [
            'name', 'search_query', 'location_filter', 'property_type_filter',
            'min_price', 'max_price', 'min_size', 'max_size', 'email_alerts'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': 'Give your search a memorable name'
            }),
            'search_query': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': 'Keywords to search for'
            }),
            'location_filter': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': 'City, State, or Region'
            }),
            'property_type_filter': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors'
            }),
            'min_price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': '0',
                'step': '1000',
                'min': '0'
            }),
            'max_price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': '1000000',
                'step': '1000',
                'min': '0'
            }),
            'min_size': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': '0',
                'step': '0.1',
                'min': '0'
            }),
            'max_size': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': '1000',
                'step': '0.1',
                'min': '0'
            }),
            'email_alerts': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500 focus:ring-2'
            })
        }
        labels = {
            'name': 'Search Name',
            'search_query': 'Keywords',
            'location_filter': 'Location',
            'property_type_filter': 'Property Type',
            'min_price': 'Minimum Price ($)',
            'max_price': 'Maximum Price ($)',
            'min_size': 'Minimum Size (Acres)',
            'max_size': 'Maximum Size (Acres)',
            'email_alerts': 'Send Email Alerts for New Matches'
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name and len(name.strip()) < 3:
            raise ValidationError('Search name must be at least 3 characters long.')
        return name.strip() if name else name

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        min_size = cleaned_data.get('min_size')
        max_size = cleaned_data.get('max_size')

        # Validate price range
        if min_price and max_price and min_price > max_price:
            raise ValidationError('Minimum price cannot be greater than maximum price.')

        # Validate size range
        if min_size and max_size and min_size > max_size:
            raise ValidationError('Minimum size cannot be greater than maximum size.')

        return cleaned_data


class BuyerInquiryForm(forms.ModelForm):
    """Form for buyers to send inquiries to sellers"""

    class Meta:
        model = Inquiry
        fields = ['subject', 'message']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': 'What would you like to know about this property?'
            }),
            'message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'rows': 6,
                'placeholder': 'Please provide details about your interest in this property, any specific questions, and how you would like to be contacted.'
            })
        }
        labels = {
            'subject': 'Subject',
            'message': 'Your Message'
        }

    def clean_subject(self):
        subject = self.cleaned_data.get('subject')
        if subject and len(subject.strip()) < 5:
            raise ValidationError('Subject must be at least 5 characters long.')
        return subject.strip() if subject else subject

    def clean_message(self):
        message = self.cleaned_data.get('message')
        if message and len(message.strip()) < 20:
            raise ValidationError('Message must be at least 20 characters long.')
        return message.strip() if message else message


class BuyerProfileForm(forms.ModelForm):
    """Form for updating buyer profile information"""

    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
            'placeholder': 'Last Name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
            'placeholder': 'Email Address'
        })
    )

    class Meta:
        model = UserProfile
        fields = ['phone', 'bio', 'avatar']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'placeholder': '+1 (555) 123-4567'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'rows': 4,
                'placeholder': 'Tell sellers about yourself and what type of land you are looking for...'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
                'accept': 'image/*'
            })
        }
        labels = {
            'phone': 'Phone Number',
            'bio': 'About You',
            'avatar': 'Profile Picture'
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Check file size (max 5MB)
            if avatar.size > 5 * 1024 * 1024:
                raise ValidationError('Avatar file size cannot exceed 5MB.')

            # Check file type by extension and content type
            allowed_extensions = ['.jpg', '.jpeg', '.png']
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png']

            # Get file extension
            file_extension = os.path.splitext(avatar.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise ValidationError('Only JPEG and PNG images are allowed for avatars.')

            # Check content type if available
            if hasattr(avatar, 'content_type') and avatar.content_type not in allowed_types:
                raise ValidationError('Invalid image format. Only JPEG and PNG images are allowed for avatars.')

            # Check image dimensions
            try:
                width, height = get_image_dimensions(avatar)
                if width and height:
                    # Minimum dimensions check for avatar
                    if width < 100 or height < 100:
                        raise ValidationError('Avatar image must be at least 100x100 pixels.')

                    # Maximum dimensions check
                    if width > 2000 or height > 2000:
                        raise ValidationError('Avatar image dimensions cannot exceed 2000x2000 pixels.')
            except Exception:
                raise ValidationError('Invalid image file. Please upload a valid image.')

        return avatar

    def save(self, commit=True):
        profile = super().save(commit=False)

        if commit:
            # Update User model fields
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.save()

            # Save profile
            profile.save()

        return profile
