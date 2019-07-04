#!/usr/bin/env python2
# IBM_PROLOG_BEGIN_TAG
# This is an automatically generated prolog.
#
# $Source: op-test-framework/testcases/NMI.py $
#
# OpenPOWER Automated Test Project
#
# Contributors Listed Below - COPYRIGHT 2017
# [+] International Business Machines Corp.
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.
#
# IBM_PROLOG_END_TAG

'''
NMI
---

Let's try to test various types of ways of triggering an NMI.
'''

import time
import subprocess
import commands
import re
import sys
import pexpect

from common.OpTestConstants import OpTestConstants as BMC_CONST
from common.OpTestError import OpTestError

import unittest
import OpTestConfiguration
from common.OpTestSystem import OpSystemState
from common.OpTestSSH import ConsoleState as SSHConnectionState
from common.Exceptions import KernelOOPS, KernelCrashUnknown, KernelKdump
from common.Exceptions import CommandFailed

class PdbgNMI(unittest.TestCase):
    def setUp(self):
        conf = OpTestConfiguration.conf
        self.host = conf.host()
        self.ipmi = conf.ipmi()
        self.bmc = conf.bmc()
        self.system = conf.system()
        self.bmc_type = conf.args.bmc_type
        self.c = self.system.console

    def runTest(self):
        self.system.goto_state(OpSystemState.OS)

        pdbg = "/tmp/pdbg "
        try:
            self.bmc.run_command(pdbg + "-V")
        except CommandFailed as cf:
            try:
                pdbg = "pdbg "
                self.bmc.run_command(pdbg + "-V")
            except CommandFailed as cf:
                self.skipTest("pdbg seems non-functional on BMC")

        self.bmc.run_command(pdbg + "-a threadstatus")

        c = self.system.console
        pty = self.system.console.get_console()

        c.run_command("echo 1 > /sys/kernel/debug/powerpc/xmon")

        for i in range(0, 100):
            try:
                while True:
                    self.bmc.run_command(pdbg + "-p0 -c03 -t0-7 stop")
                    getnia = self.bmc.run_command(pdbg + "-p0 -c03 -t0  getnia")
                    nia = getnia[0]
                    if "0x00000000300" not in nia:
                        self.bmc.run_command(pdbg + "-p0 -c03 -t1-7 start")
                        break
                    print "nia {} was in OPAL, retrying".format(nia)
                    self.bmc.run_command(pdbg + "-p0 -c03 -t0-7 start")
            except CommandFailed as cf:
                if "Thread in incorrect state" in cf.output:
                    continue
                self.bmc.run_command(pdbg + "-a threadstatus")
                self.assertTrue(False, str(cf))

            self.bmc.run_command(pdbg + "-p0 -c3 -t0 sreset")

            rc = pty.expect(["mon>",
                             pexpect.TIMEOUT, pexpect.EOF],
                            timeout=100)
            if rc in [1, 2]:
                self.system.set_state(OpSystemState.Unknown)

            pty.sendline("x")
            time.sleep(0.2)
            pty.sendline("")
            pty.expect(['#'])
            c.run_command("echo Hello World")

            print "SRESET into XMON round {} complete!".format(i)



