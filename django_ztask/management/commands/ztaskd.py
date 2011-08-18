import sys
import traceback
import pickle
import datetime, time
from threading import Thread
from optparse import make_option

import zmq
from zmq.core.device import device
try:
    from zmq import PUSH
except:
    from zmq import DOWNSTREAM as PUSH
try:
    from zmq import PULL
except:
    from zmq import UPSTREAM as PULL

from django.core.management.base import BaseCommand
from django.utils import autoreload

from django_ztask.models import Task
from django_ztask.conf import settings, logger
from django_ztask.context import shared_context as context

class DeviceType(object):
    QUEUE, FORWARDER, STREAMER = range(3)

def _async_queue():
    """Handles the blocking messaging for the worker queue."""
    logger.info('Async queue thread is running.')
    queue_socket = context.socket(PULL)
    queue_socket.connect(settings.ZTASK_INTERNAL_QUEUE_URL)
    
    worker_socket = context.socket(PUSH)
    worker_socket.bind(settings.ZTASK_WORKER_URL)
    
    d = device(DeviceType.STREAMER, 
        queue_socket, worker_socket)

def _serve():
    """Handles immediate logging of tasks in the Django model."""
    logger.info('Server thread is running.')
    
    server_socket = context.socket(PULL)
    server_socket.bind(settings.ZTASKD_URL)
    
    queue_socket = context.socket(PUSH)
    queue_socket.bind(settings.ZTASK_INTERNAL_QUEUE_URL)
    
    while True:
        _recv_and_enqueue(server_socket, queue_socket)


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
        
        # TODO: how should these threads be killed when reloaded
        queue_thread = Thread(target=_async_queue)
        queue_thread.start()
        
        serve_thread = Thread(target=_serve)
        serve_thread.start()
    

def _recv_and_enqueue(server_socket, worker_socket):
    try:
        
        function_name, args, kwargs = server_socket.recv_pyobj()
        
        if function_name == 'ztask_log':
            logger.warn('%s: %s' % (args[0], args[1]))
            return
        
        task = Task.objects.create(
            function_name=function_name, 
            args=pickle.dumps(args), 
            kwargs=pickle.dumps(kwargs), 
        )
        logger.info('Listed task in django database (%r)' % task.pk)
        # TODO: need to make the send below async so that work can be 
        #   recorded in the queue even if workers aren't present to recv
        worker_socket.send_pyobj((str(task.pk),))
        logger.info('Passed task to worker queue (%r)' % task.pk)
        
        
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

