from django import template
from django.forms import widgets
from decimal import Decimal, InvalidOperation

register = template.Library()

@register.filter
def add_class(field, css_class):
    """
    Add CSS class to form field widget.
    Usage: {{ form.field|add_class:"my-class" }}
    """
    if hasattr(field, 'as_widget'):
        # Get existing classes
        existing_classes = field.field.widget.attrs.get('class', '')
        
        # Combine existing and new classes
        if existing_classes:
            new_classes = f"{existing_classes} {css_class}"
        else:
            new_classes = css_class
            
        # Update widget attributes
        field.field.widget.attrs.update({'class': new_classes})
        
        return field
    return field

@register.filter
def add_label_class(field, css_class):
    """
    Renders the field's label tag and adds a CSS class.
    This is useful for styling labels differently from the fields.
    Usage: {{ form.field|add_label_class:"my-label-class" }}
    """
    if hasattr(field, 'label_tag'):
        # Render the label tag with the given class attribute
        return field.label_tag(attrs={'class': css_class})
    # Fallback for fields without a label_tag method
    return ''

@register.filter
def add_attr(field, attr_value):
    """
    Add attribute to form field widget.
    Usage: {{ form.field|add_attr:"placeholder:Enter value" }}
    """
    if hasattr(field, 'as_widget'):
        try:
            attr_name, attr_val = attr_value.split(':', 1)
            field.field.widget.attrs.update({attr_name: attr_val})
        except ValueError:
            pass
        return field
    return field

@register.filter
def field_type(field):
    """
    Get the field widget type.
    Usage: {% if form.field|field_type == 'textarea' %}
    """
    if hasattr(field, 'field'):
        widget = field.field.widget
        if isinstance(widget, widgets.Textarea):
            return 'textarea'
        elif isinstance(widget, widgets.Select):
            return 'select'
        elif isinstance(widget, widgets.CheckboxInput):
            return 'checkbox'
        elif isinstance(widget, widgets.RadioSelect):
            return 'radio'
        elif isinstance(widget, widgets.FileInput):
            return 'file'
        elif isinstance(widget, widgets.PasswordInput):
            return 'password'
        elif isinstance(widget, widgets.EmailInput):
            return 'email'
        elif isinstance(widget, widgets.NumberInput):
            return 'number'
        elif isinstance(widget, widgets.DateInput):
            return 'date'
        elif isinstance(widget, widgets.TimeInput):
            return 'time'
        elif isinstance(widget, widgets.DateTimeInput):
            return 'datetime'
        else:
            return 'text'
    return 'text'


@register.filter
def div(value, divisor):
    """
    Divide value by divisor.
    Usage: {{ price|div:size_acres }}
    """
    try:
        # Convert to Decimal for precise calculation
        value = Decimal(str(value))
        divisor = Decimal(str(divisor))

        # Avoid division by zero
        if divisor == 0:
            return 0

        return value / divisor
    except (ValueError, InvalidOperation, TypeError):
        return 0
