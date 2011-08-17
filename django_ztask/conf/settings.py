from django.conf import settings

ZTASKD_URL = getattr(settings, 'ZTASKD_URL', 'tcp://127.0.0.1:5555')
ZTASKD_RETRY_COUNT = getattr(settings, 'ZTASKD_RETRY_COUNT', 5)
ZTASKD_RETRY_AFTER = getattr(settings, 'ZTASKD_RETRY_AFTER', 5)

ZTASKD_ON_LOAD = getattr(settings, 'ZTASKD_ON_LOAD', ())
ZTASKD_LOG_LEVEL = getattr(settings, 'ZTASKD_LOG_LEVEL', 'info')
ZTASKD_LOG_PATH = getattr(settings, 'ZTASKD_LOG_PATH', None)
