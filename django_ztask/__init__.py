"""Django ZTaskQueue based on a fork of Django ZTask."""
import os

VERSION = (0, 1, 4)

__version__ = ".".join(map(str, VERSION[0:3])) + "".join(VERSION[3:])
__author__ = "Drew Bryant (ZTask: Jason Allum and Dave Martorana)"
__contact__ = "drew.h.bryant@gmail.com"
__homepage__ = "https://github.com/awesomo/django-ztask"
__docformat__ = "markdown"
__license__ = "BSD (3 clause)"

# try to import dependencies
# repo: https://github.com/awesomo/django-picklefield
import picklefield
