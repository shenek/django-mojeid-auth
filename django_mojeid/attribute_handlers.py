from django.utils.translation import ugettext_lazy as _

_handlers = {}


class HandlerNotFound(Exception):
    pass


def register_handler(handler_name):

    def function_wrapper(f):

        def wrapped_function(*args, **kwargs):
            return f(*args, **kwargs)

        # This import is required to match the correct import
        from django_mojeid.attribute_handlers import _handlers

        # Store function into dict under handler name
        _handlers[handler_name] = wrapped_function

        return wrapped_function

    return function_wrapper


def call_handler(handler_name, *args, **kwargs):
    try:
        _handlers[handler_name](*args, **kwargs)
    except KeyError:
        raise HandlerNotFound(_('Handler with name %s was not found.') % handler_name)
