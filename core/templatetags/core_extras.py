from django import template

from .. import markdown_lite

register = template.Library()


@register.filter
def mdlite(text):
    return markdown_lite.render(text or "")
