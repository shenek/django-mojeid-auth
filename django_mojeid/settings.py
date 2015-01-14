from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


# defaults

MOJEID_LOGIN_METHOD = "ANY"
MOJEID_ENDPOINT_URL = 'https://mojeid.fred.nic.cz/endpoint/'
MOJEID_REGISTRATION_URL = 'https://mojeid.fred.nic.cz/registration/endpoint/'


class Settings(object):
    def __getattr__(self, name):
        try:
            attr = getattr(settings, name)
        except AttributeError:
            try:
                attr = globals()[name]
            except KeyError:
                raise AttributeError("'Settings' object has no attribute '%s'"
                                     % name)
        
        # validate
        if name == 'MOJEID_LOGIN_METHOD' and attr not in ("ANY", "CERT", "OTP"):
            raise ImproperlyConfigured("Invalid MOJEID_LOGIN_METHOD '%s'"
                                        % attr)
        
        return attr

mojeid_settings = Settings()
