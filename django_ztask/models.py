import uuid
import datetime
import time
import sys
import traceback
import pickle

from django.db.models import *

from django_ztask.conf import settings, logger

class Status(object):
    """Enum-style class of possible task statuses."""
    QUEUED = u'Q'
    RUNNING = u'R'
    COMPLETED = u'C'
    FAILED = u'F'

# pretty forms for the admin interface
STATUS_CHOICES = (
    (Status.QUEUED, u'Queued'),
    (Status.RUNNING, u'Running'),
    (Status.COMPLETED, u'Completed'),
    (Status.FAILED, u'Failed'),
)

_func_cache = {} # could be a classwide "static" member (may have to override __new__)
class Task(Model):
    uuid = CharField(max_length=36, primary_key=True)
    
    function_name = CharField(max_length=255)
    args = TextField()
    kwargs = TextField()
    
    error = TextField(blank=True, null=True)
    
    queued = DateTimeField(blank=True, null=True)
    started = DateTimeField(blank=True, null=True)
    finished = DateTimeField(blank=True, null=True)
    
    status = CharField(max_length=1, choices=STATUS_CHOICES, 
        default=Status.QUEUED)
    
    def save(self, *args, **kwargs):
        if not self.uuid:
            self.queued = datetime.datetime.utcnow()
            self.uuid = str(uuid.uuid4())
        super(Task, self).save(*args, **kwargs)
    
    class Meta:
        db_table = 'django_ztask_task'
    
    @classmethod
    def run_task(cls, task_id):
        try:
            task = cls.objects.get(pk=task_id)
        except Exception, e:
            logger.info('Could not get task with id %s:\n%s' % (task_id, e))
            return
        task.run()
    
    def mark_running(self):
        self.status = Status.RUNNING
        self.started = datetime.datetime.utcnow()
        
        self.save()
    
    def mark_complete(self, success=True, delete=False, error_msg=''):
        """Mark the task as finished (success/failure)
        
        The error message is only used if success is False.
        
        """
        if delete:
            self.delete()
            return
        
        self.status = Status.COMPLETED if success else Status.FAILED
        if not success:
            self.error = error_msg
        self.finished = datetime.datetime.utcnow()
        
        self.save()
    
    def get_args(self):
        """
        TODO: need to a descriptor or whatever its called that 
         handles pickling the args/kwargs object when the value is
         assigned to and unpickling when it is read such that it is 
         transparent to the user of the Task.  for now just using this getter
        
        """
        return pickle.loads(str(self.args))
    
    def get_kwargs(self):
        """TODO: ditto with get_args()"""
        return pickle.loads(str(self.kwargs))
    
    def run(self):
        
        function_name = self.function_name
        args = self.get_args()
        kwargs = self.get_kwargs()
        
        self.mark_running()
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
            self.mark_complete(success=False, error_msg=str(e))
            logger.error('Error calling %s. Details:\n%s' % (function_name, e))
        else:
            self.mark_complete(success=True)
            logger.info('Called %s successfully' % function_name)

