from django.core.management.base import BaseCommand
from django.utils import autoreload

from django_ztask.models import Task

from django_ztask.conf import settings, logger
from django_ztask.context import shared_context as context

import zmq
try:
    from zmq import PUSH
except:
    from zmq import DOWNSTREAM as PUSH
try:
    from zmq import PULL
except:
    from zmq import UPSTREAM as PULL

from optparse import make_option
import sys
import traceback

import pickle
import datetime, time

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noreload', 
            action='store_false', dest='use_reloader', default=True, 
            help='Tells Django to NOT use the auto-reloader.'),
        make_option('--replayfailed', 
            action='store_true', dest='replay_failed', default=False, 
            help='Replays all failed calls in the db'),
    )
    args = ''
    help = 'Start the ztaskd server'
    
    def handle(self, *args, **options):
        use_reloader = options.get('use_reloader', True)
        
        if use_reloader:
            autoreload.main(lambda: self._handle(use_reloader))
        else:
            self._handle(use_reloader)
    
    def _handle(self, use_reloader):
        logger.info("%sServer starting on %s." % ('Development ' if use_reloader else '', settings.ZTASKD_URL))
        _on_load()
        
        server_socket = context.socket(PULL)
        server_socket.bind(settings.ZTASKD_URL)
        
        worker_socket = context.socket(PUSH)
        worker_socket.bind(settings.ZTASK_WORKER_URL)
        
        while True:
            _recv_and_enqueue(server_socket, worker_socket)
        
    

def _recv_and_enqueue(server_socket, worker_socket):
    try:
        
        function_name, args, kwargs = server_socket.recv_pyobj()
        retry_wait_time = 5000 # 5 seconds
        
        if function_name == 'ztask_log':
            logger.warn('%s: %s' % (args[0], args[1]))
            return
        
        task = Task.objects.create(
            function_name=function_name, 
            
            args=pickle.dumps(args), 
            kwargs=pickle.dumps(kwargs), 
            
            retry_count=settings.ZTASKD_RETRY_COUNT,
            next_attempt=time.time() + retry_wait_time
        )
        logger.info('Listed task in django database (%s)' % function_name)
        worker_socket.send_pyobj((task.pk,))
        logger.info('Passed task to worker queue (%s)' % function_name)
        
    except Exception, e:
        logger.error('Error setting up function. Details:\n%s' % e)
        traceback.print_exc(e)
    

def _on_load():
    """Execute any startup function callbacks associated with ztaskd."""
    
    for callable_name in settings.ZTASKD_ON_LOAD:
        logger.info("ON_LOAD calling %s" % callable_name)
        
        parts = callable_name.split('.')
        module_name = '.'.join(parts[:-1])
        member_name = parts[-1]
        
        if not module_name in sys.modules:
            __import__(module_name)
        
        callable_fn = getattr(sys.modules[module_name], member_name)
        callable_fn()

