from django.utils.decorators import available_attrs
from functools import wraps

import logging
import types


def task():
    from .conf import settings
    try:
        from zmq import PUSH
    except:
        from zmq import DOWNSTREAM as PUSH
    
    def wrapper(func):
        function_name = '%s.%s' % (func.__module__, func.__name__)
        
        logger = logging.getLogger('ztaskd')
        logger.info('Registered task: %s' % function_name)
        
        from .context import shared_context as context
        socket = context.socket(PUSH)
        socket.connect(settings.ZTASKD_URL)
        
        @wraps(func)
        def _async(*args, **kwargs):
            # pop the key and ignore it
            after = kwargs.pop('__ztask_after', 0)
            
            try:
                socket.send_pyobj((function_name, args, kwargs))
            except Exception, e:
                logger.error('Failed to submit task to ztaskd: '
                    '%s(args=%r, kwargs=%r)' % (function_name, args, kwargs))
        
        setattr(func, 'async', _async)
        return func
    
    return wrapper
