
# This file needs to be imported from __init__.py

from django_mojeid.attribute_handlers import register_handler
@register_handler('full_name_handler')
def print_fullname_to_console(full_name):
    print '>>>', full_name, '<<<'
