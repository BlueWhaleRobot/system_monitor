#!/usr/bin/env python3
# encoding=utf-8
# The MIT License (MIT)
#
# Copyright (c) 2018 Bluewhale Robot
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Author: Randoms, Xie fusheng
#

import os
import subprocess
import threading
import time

import psutil
import rospy

from .config import ROS_PACKAGE_PATH


class ScheduleService(threading.Thread):
    def __init__(self, galileo_status, galileo_status_lock):
        super(ScheduleService, self).__init__()
        self._stop = threading.Event()
        self._stop.set()
        self.p_slam = None
        self.ps_process_slam = None
        self.p_navigation = None
        self.ps_process_navigation = None
        self.galileo_status = galileo_status
        self.galileo_status_lock = galileo_status_lock
        self.fake_flag = rospy.get_param("~fake", False)
        self.navigation_cmd = "roslaunch lagrange_navigation navigation.launch"
        self.slam_cmd = "roslaunch lagrange_navigation slam.launch"
        if self.fake_flag:
            self.slam_cmd = "roslaunch lagrange_navigation slam_fake.launch"


    def stop(self):
        self._stop.set()
        self.stop_slam()
        self.stop_navigation()
        self.__init__(self.galileo_status, self.galileo_status_lock)

    def stop_slam(self):
        if self.p_slam != None:
            try:
                self.ps_process_slam = psutil.Process(pid=self.p_slam.pid)
                for child in self.ps_process_slam.children(recursive=True):
                    child.kill()
                self.ps_process_slam.kill()
            except Exception:
                pass
        os.system("pkill -f 'roslaunch lagrange_navigation slam.launch'")
        os.system("pkill -f 'roslaunch lagrange_navigation slam_fake.launch'")
    
    def stop_navigation(self):
        if self.p_navigation != None:
            try:
                self.ps_process_navigation = psutil.Process(pid=self.p_navigation.pid)
                for child in self.ps_process_navigation.children(recursive=True):
                    child.kill()
                self.ps_process_navigation.kill()
            except Exception:
                pass
        os.system("pkill -f 'roslaunch lagrange_navigation navigation.launch'")
        self.p_navigation = None

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        self._stop.clear()
        new_env = os.environ.copy()
        new_env['ROS_PACKAGE_PATH'] = ROS_PACKAGE_PATH
        if self.p_navigation == None and not self.stopped():
            self.p_navigation = subprocess.Popen(self.navigation_cmd, shell=True, env=new_env)
            self.ps_process_navigation = psutil.Process(pid=self.p_navigation.pid)
        while not self.stopped() and not rospy.is_shutdown():
            if self.p_slam == None and not self.stopped():
                self.p_slam = subprocess.Popen(self.slam_cmd, shell=True, env=new_env)
                self.ps_process_slam = psutil.Process(pid=self.p_slam.pid)
            else:
                if not self.ps_process_slam.is_running():
                    break
            time.sleep(0.1)
        self.stop()

    def reload(self):
        if self.stopped():
            return
        # restart lagrange_navigation navigation.launch
        self.stop_navigation()
        new_env = os.environ.copy()
        new_env['ROS_PACKAGE_PATH'] = ROS_PACKAGE_PATH
        self.p_navigation = subprocess.Popen(self.navigation_cmd, shell=True, env=new_env)
        self.ps_process_navigation = psutil.Process(pid=self.p_navigation.pid)