This is a sample Django app that illustrates how to use [django_ztaskq](https://github.com/awesomo/django-ztaskq).

Install django_ztaskq and then do::

    python manage.py syncdb
    python manage.py ztaskd
    python manage.py workerd

And visit:

- http://localhost:8000/launch_ztask/
