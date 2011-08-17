import datetime, time

from django_ztask.conf import settings, logger

from django_ztask.models import Task

def _run_next_task():
    try:
        task = _get_next_task()
    except ValueError: # no tasks to compute
        pass
    else:
        _execute_task(task.pk)

def _get_next_task():
    tasks = Task.objects.filter(retry_count__gt=0).order_by('created')
    try:
        return tasks[0]
    except IndexError: # zero tasks
        raise RuntimeError('No callbacks available currently.')
    
    # this whole function needs to be replaced because the database is being used as the queue
    #  but there could be issues with multiple workers grabbing work simultaneously.
    # use a zmq queue instead of the database for the work pipeline

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
        _mark_failed_task(task_id, e)
        logger.error('Error calling %s. Details:\n%s' % (function_name, e))
    else:
        _finalize_complete_task(task_id)
        logger.info('Called %s successfully' % function_name)
    

def _finalize_complete_task(task_id):
    Task.objects.get(pk=task_id).delete() # TODO just mark it complete instead of deleting?

def _mark_failed_task(task_id, last_exception):
    task = Task.objects.get(pk=task_id)
    
    if task.retry_count > 0:
        task.retry_count = task.retry_count - 1
        task.next_attempt = time.time() + settings.ZTASKD_RETRY_AFTER
        
    task.failed = datetime.datetime.utcnow()
    task.last_exception = str(last_exception)
    task.save()
