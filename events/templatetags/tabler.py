from django import template
from django.forms.widgets import CheckboxInput, Select, SelectMultiple

register = template.Library()


@register.filter
def is_checkbox(field):
    return isinstance(field.field.widget, CheckboxInput)


@register.filter
def tabler(field):
    """Render a form field with Tabler's input classes."""
    widget = field.field.widget
    if isinstance(widget, CheckboxInput):
        css = "form-check-input"
    elif isinstance(widget, (Select, SelectMultiple)):
        css = "form-select"
    else:
        css = "form-control"
    classes = [widget.attrs.get("class", ""), css]
    if field.errors:
        classes.append("is-invalid")
    return field.as_widget(attrs={"class": " ".join(c for c in classes if c)})
