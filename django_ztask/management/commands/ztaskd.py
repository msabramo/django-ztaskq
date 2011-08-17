from django.core.management.base import BaseCommand
from django.utils import autoreload
#
from django_ztask.models import Task
#
from django_ztask.conf import settings, logger
from django_ztask.context import shared_context as context
#
import zmq
from zmq.eventloop import ioloop
try:
    from zmq import PULL
except:
    from zmq import UPSTREAM as PULL
#
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
        
        socket = context.socket(PULL)
        socket.bind(settings.ZTASKD_URL)
        
        while True:
            _recv_and_enqueue(socket)
        
    

def _recv_and_enqueue(socket):
    try:
        
        function_name, args, kwargs = socket.recv_pyobj()
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
        # TODO: extract this to worker processes
        # _execute_task(task.pk)
        
    except Exception, e:
        logger.error('Error setting up function. Details:\n%s' % e)
        traceback.print_exc(e)
    

def _get_next_task():
    tasks = Task.objects.filter(retry_count__gt=0).order_by('created')
    try:
        return tasks[0]
    except IndexError: # zero tasks
        raise RuntimeError('No callbacks available currently.')
    
    # this whole function needs to be replaced because the database is being used as the queue
    #  but there could be issues with multiple workers grabbing work simultaneously.
    # use a zmq queue instead of the database for the work pipeline

def _run_next_task():
    try:
        task = _get_next_task()
    except ValueError: # no tasks to compute
        pass
    else:
        _execute_task(task.pk)

_func_cache = {}
def _execute_task(task_id):
    
    try:
        task = Task.objects.get(pk=task_id)
    except Exception, e:
        logger.info('Could not get task with id %s:\n%s' % (task_id, e))
        return
    
    function_name = task.function_name
    args = pickle.loads(str(task.args))
    kwargs = pickle.loads(str(task.kwargs))
    
    logger.info('Executing task function (%s)' % function_name)
    
    try:
        function = _func_cache[function_name]
    except KeyError:
        parts = function_name.split('.')
        module_name = '.'.join(parts[:-1])
        member_name = parts[-1]
        if not module_name in sys.modules:
            __import__(module_name)
        function = getattr(sys.modules[module_name], member_name)
        _func_cache[function_name] = function
    
    try:
        function(*args, **kwargs)
    except Exception, e:
        _mark_failed_task(task, e)
        logger.error('Error calling %s. Details:\n%s' % (function_name, e))
    else:
        _finalize_complete_task(task)
        logger.info('Called %s successfully' % function_name)
    

def _finalize_complete_task(task):
    Task.objects.get(pk=task_id).delete() # TODO just mark it complete instead of deleting?

def _mark_failed_task(task, last_exception):
    task = Task.objects.get(pk=task_id)
    
    if task.retry_count > 0:
        task.retry_count = task.retry_count - 1
        task.next_attempt = time.time() + settings.ZTASKD_RETRY_AFTER
        
    task.failed = datetime.datetime.utcnow()
    task.last_exception = str(last_exception)
    task.save()

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

