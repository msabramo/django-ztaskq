Notes about this fork
=====================

Django ZTaskQ is a 0MQ-based [http://www.zeromq.org/] asynchronous task queue that is based upon a fork of the 
delightfully straight-forward django-ztask by Jason Allum and Dave Martorana (read more 
about how django-ztask from [http://www.zeromq.org/story:3]).

Django ZTaskQ adds an asynchronous task queue that farms out work equitably to one
or more worker processes.  Because the changed necessary were quite backwards incompatible,
Django ZTaskQ is now a separate project from Django ZTask.

Installing
==========

Download and install 0MQ version 2.1.3 or better from [http://www.zeromq.org](http://www.zeromq.org)

Install pyzmq and django-ztaskq using PIP:

    pip install pyzmq
    pip install -e git+git@github.com:awesomo/django-ztaskq.git#egg=django_ztaskq

Add `django_ztaskq` to your `INSTALLED_APPS` setting in `settings.py`

```python
    INSTALLED_APPS = (
        ...,
        'django_ztaskq',
    )
```

Then run `syncdb`

    python manage.py syncdb
    

Running the server
==================

Start the django-ztaskq server using the manage.py command:

    python manage.py ztaskd

Start one or more worker processes by using the manage.py command:

    python manage.py workerd


Command-line arguments
----------------------

The `ztaskd` command takes a series of command-line arguments:

- `--noreload`
  
  By default, `ztaskd` will use the built-in Django reloader 
  to reload the server whenever a change is made to a python file. Passing
  in `--noreload` will prevent it from listening for changed files.
  (Good to use in production.)

- `-l` or `--loglevel`
  
  Choose from the standard `CRITICAL`, `ERROR`, `WARNING`, 
  `INFO`, `DEBUG`, or `NOTSET`. If this argument isn't passed 
  in, `INFO` is used by default.

- `-f` or `--logfile`
  
  The file to log messages to. By default, all messages are logged
  to `stdout`



Settings
--------

There are several settings that you can put in your `settings.py` file in 
your Django project. These are the settings and their defaults

    ZTASKD_URL = 'tcp://127.0.0.1:5555'

By default, `ztaskd` will run over TCP, listening on 127.0.0.1 port 5555. 

    ZTASK_WORKER_URL = getattr(settings, 'ZTASK_WORKER_URL', 'tcp://127.0.0.1:5556')

By default, all `workerd` instances will listen on 127.0.0.1 port 5556.

Running in production
---------------------

A recommended way to run in production would be to put something similar to 
the following in to your `rc.local` file:

    #!/bin/bash -e
    pushd /var/www/path/to/site
    sudo -u www-data python manage.py ztaskd --noreload -f /var/log/ztaskd.log &
    popd
    
    pushd /var/www/path/to/site
    sudo -u www-data python manage.py workerd --noreload -f /var/log/workerd0.log &
    popd
    
    pushd /var/www/path/to/site
    sudo -u www-data python manage.py workerd --noreload -f /var/log/workerd1.log &
    popd

The commands above will start the ztask queue in addition to 2 worker processes.

Making functions in to tasks
============================

Decorators and function extensions make tasks able to run. 
Unlike some solutions, tasks can be in any file anywhere. 
When the file is imported, `ztaskd` will register the task for running.

**Important note: all functions and their arguments must be able to be pickled.**

([Read more about pickling here](http://docs.python.org/tutorial/inputoutput.html#the-pickle-module))

The @ztask Decorator
-------------------

    from django_ztaskq.decorators import ztask

The `@ztask()` decorator will turn any normal function in to a 
`django_ztaskq` task if called using one of the function extensions.

Function extensions
-------------------

Any function can be called in one of three ways:

- `func(*args, *kwargs)`

  Calling a function normally will bypass the decorator and call the function directly

- `func.async(*args, **kwargs)`

  Calling a function with `.async` will cause the function task to be called asynchronously 
  on the ztaskd server. 


Example
-------

    from django_ztaskq.decorators import ztask
    
    @ztask()
    def print_this(what_to_print):
        print what_to_print
        
    if __name__ == '__main__':
        
        # Call the function directly
        print_this('Hello world!')
        
        # Call the function asynchronously
        print_this.async('This will print to the ztaskd log')
        
        
