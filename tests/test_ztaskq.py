from os import chdir, environ, execl, fdopen, fork, getpid, kill, killpg, setpgid, setsid, system, wait
from signal import SIGTERM
from subprocess import Popen, PIPE
from sys import executable, exit
from time import sleep
from unittest import TestCase
from urllib2 import urlopen
from pty import openpty

import sys
sys.path.append(".")

from django_ztaskq.decorators import ztask


class ZTaskQTestCase(TestCase):

    verbose = False

    def setUp(self):
        self.is_child = False

        fork_result = fork()

        if fork_result == 0:
            self.is_child = True
            self.spawn_children()
        else:
            self.child_pid = fork_result

    def spawn_children(self):
        setpgid(0, 0)
        chdir("example")
        environ["DJANGO_SETTINGS_MODULE"] = "settings"
        system("%s manage.py syncdb --noinput > /dev/null" % executable)

        self.ztaskd = Popen([executable, "manage.py", "ztaskd"], stdout=PIPE, stderr=PIPE)

        master, slave = openpty()
        self.workerd = Popen([executable, "manage.py", "workerd"], stdout=slave, stderr=slave)
        self.workerd_stdout = fdopen(master)

        self.runserver = Popen([executable, "manage.py", "runserver"], stdout=PIPE, stderr=PIPE)

    def test_hit_page_that_spawns_a_ztask(self):
        if not self.is_child:
            wait()
            return

        sleep(1)
        urlopen("http://localhost:8000/launch_ztask/")
        sleep(1)

        while True:
            line = self.workerd_stdout.readline()
            if self.verbose:
                print("    " + line.rstrip())

            if 'This is a message logged from a ztaskq workerd process' in line:
                break

    def tearDown(self):
        if self.is_child:
            killpg(0, SIGTERM)

