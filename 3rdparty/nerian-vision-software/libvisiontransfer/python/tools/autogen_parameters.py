#!/usr/bin/env python3

###############################################################################/
# Copyright (c) 2022 Nerian Vision GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
###############################################################################/

#
# This helper script auto-generates adapters for all current
#  Nerian stereo device parameters directly from the C++ header file.
#

import pathlib
import sys
import os

class Generator(object):
    def __init__(self):

        ##### Code for the .pxd file (appended to by autogenerator) #####
        self.pxdcode = \
'''
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!  CAUTION                                                        !!
# !!                                                                 !!
# !!  This file is autogenerated from the libvisiontransfer headers  !!
# !!  using autogen_parameters.py - manual changes are not permanent !!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

cdef extern from "visiontransfer/deviceparameters.h" namespace "visiontransfer":
    cdef cppclass DeviceParameters:
        DeviceParameters(const DeviceInfo &) except +
        DeviceParameters(const char* address, const char* service) except +
        ParameterSet getParameterSet() except +
        bool hasParameter(const string& uid) except +
        Parameter getParameter(const string& uid) except +
        void setParameter(const string& uid, string value) except +'''.split('\n')

        ##### Code for the .pyx file (docstring appended to by autogenerator) #####
        self.pyxcode = \
'''# distutils: language=c++
# cython: language_level=3

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!  CAUTION                                                        !!
# !!                                                                 !!
# !!  This file is autogenerated from the libvisiontransfer headers  !!
# !!  using autogen_parameters.py - manual changes are not permanent !!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

from libcpp.string cimport string
from libcpp.vector cimport vector
from libcpp cimport bool
from cython cimport view

cdef class DeviceParameters:
'''.split('\n')

        ##### Second block of code for .pyx (after docstring), appended to by autogen #####
        self.pyxcode2 = \
'''
    cdef cpp.DeviceParameters*  c_obj

    def __cinit__(self, device_info_or_address, service='7683'):
        if isinstance(device_info_or_address, DeviceInfo):
            self.c_obj = new cpp.DeviceParameters((<DeviceInfo> device_info_or_address).c_obj)
        else:
            self.c_obj = new cpp.DeviceParameters(
                    device_info_or_address.encode(),
                    service.encode()
                )

    def __init__(self, device_info_or_address, service='7683'):
        \'\'\'
Connects to parameter server of a Nerian stereo device, either by using a
discovered DeviceInfo (see DeviceEnumeration) or an address and optional port.
        \'\'\'
        pass

    def __dealloc__(self):
        del self.c_obj

    def get_parameter_set(self):
        \'\'\'
Returns a copy of the currently active ParameterSet (works like dict from
parameter UID to Parameter objects). Contents are not updated in this copy
if parameters are modified by the server. For setting parameters, please
use set_parameter() exclusively.
        \'\'\'
        ps = ParameterSet()
        ps.c_obj = self.c_obj.getParameterSet()
        return ps

    def has_parameter(self, uid):
        \'\'\'
        Tests whether a specific named parameter is available for this device.
        \'\'\'
        return self.c_obj.hasParameter(uid.encode('utf-8'))

    def get_parameter(self, uid):
        \'\'\'
Returns a Parameter object for the named device parameter. An
exception is raised for invalid or inaccessible parameter names.

The returned object is a detached copy of the internal parameter at invocation
time; it is not updated when the device sends a new value or metadata.
Likewise, any modifications must be requested using set_parameter() or the
various parameter-specific setters.
        \'\'\'
        return wrap_python_parameter(self.c_obj.getParameter(uid.encode('utf-8')))

    def set_parameter(self, uid, value):
        \'\'\'
Attempts to set a parameter on the device, given a parameter UID string
and a new value, which is typecast automatically. Raises an exception
if the operation failed.
        \'\'\'
        self.c_obj.setParameter(uid.encode('utf-8'), str(value).encode('utf-8'))

    def reboot(self):
        \'\'\'
Remotely triggers a reboot of the device
        \'\'\'
        self.c_obj.setParameter('reboot'.encode('utf-8'), '1'.encode('utf-8'))

    def trigger_now(self):
        \'\'\'
Emit a software trigger event to perform a single acquisition.
This only has effect when the External Trigger mode is set to Software.
        \'\'\'
        self.c_obj.setParameter('trigger_now'.encode('utf-8'), '1'.encode('utf-8'))

'''.split('\n')

    def add_pxd(self, ret, fnname, argstr):
        args = [p.strip().split() for p in argstr.split(',')]
        # remove default arguments in pxd (present in pyx)
        for a in args:
            if len(a)>1:
                a[1] = a[1].split('=')[0]
        self.pxdcode.append(' '*8 + ret + ' ' + fnname + ' ('+(', '.join((a[0]+' '+a[1]) for a in args if len(a)>1))+') except +')

    def add_pyx(self, ret, fnname, argstr, comment):
        # Generate function name reference also used by doc extractor
        args_just_names = [(a.split('=')[0].strip().split()[-1] if a.strip()!='' else '') for a in argstr.split(',')]
        currentname = 'visiontransfer::DeviceParameters::' + fnname + '(' + (', '.join(args_just_names)) + ')'
        fnname_snake = self.snake_case(fnname)
        args = [p.strip().split() for p in argstr.split(',')]
        # For non-trivial types (i.e. Classes / enums), rename with prefix 'cpp.' to refer to the Cython glue class
        for i in range(len(args)):
            if len(args[i])>0:
                if args[i][0] in ['int', 'float', 'double', 'bool', 'int&', 'float&', 'double&', 'bool&']:
                    pass
                else:
                    args[i][0] = "cpp." + str(args[i][0])
        # Code generation
        if fnname.startswith('set'):
            # for setter
            argstr = ', '.join(' '.join(a) for a in args if len(a)>0)
            self.pyxcode.append(' '*4 + 'def '+ fnname_snake + '(self' + (', ' if len(argstr) else '') + argstr + '):')
            self.pyxcode.append(' '*8 + '_SUBSTITUTE_DOCSTRING_FOR_("' + currentname + '")')
            self.pyxcode.append(' '*8 + 'self.c_obj.'+ fnname + '(' + ', '.join(a[1].split('=')[0] for a in args if len(a)>1) + ')')
            self.pyxcode.append(' '*0) # extra newline to visually separate blocks
            pass
        else:
            # for getter
            argstr = '' #', '.join(' '.join(a) for a in args if len(a)>0)
            newargstr_defaults = ', '.join(a[1] for a in args if len(a)>0)
            newargstr_nodefaults = ', '.join(a[1].split('=')[0] for a in args if len(a)>0)
            if all(' '.join(a).find('&')<0 for a in args): #len(args)==0 or len(args[0])==0:
                if ret in ['int', 'float', 'double', 'bool', 'int&', 'float&', 'double&', 'bool&']:
                    ret = ''
                    ret_post = ''
                else:
                    ret += '('
                    ret_post = ')'
                self.pyxcode.append(' '*4 + 'def '+ fnname_snake + '(self' + (', ' if len(newargstr_defaults) else '') + newargstr_defaults + '):')
                self.pyxcode.append(' '*8 + '_SUBSTITUTE_DOCSTRING_FOR_("' + currentname + '")')
                self.pyxcode.append(' '*8 + 'return '+ret+'self.c_obj.'+ fnname + '(' + newargstr_nodefaults + ')' + ret_post)
            else:
                self.pyxcode.append(' '*4 + 'def '+ fnname_snake + '(self' + (', ' if len(argstr) else '') + argstr + '):')
                self.pyxcode.append(' '*8 + '_SUBSTITUTE_DOCSTRING_FOR_("' + currentname + '")')
                for a in args:
                    rawtype = a[0].replace('&', '')
                    var = a[1] if a[1].find('=')>0 else (a[1]+' = 0')
                    self.pyxcode.append(' '*8 + 'cdef '+rawtype+' '+var)
                self.pyxcode.append(' '*8 + 'self.c_obj.'+ fnname + '(' + newargstr_nodefaults + ')')
                self.pyxcode.append(' '*8 + 'return '+newargstr_nodefaults)
            self.pyxcode.append(' '*0) # extra newline to visually separate blocks

    def snake_case(self, fnname):
        '''Convert mixed case to Python methods' snake case'''
        fnname_snake = ''
        for c in fnname:
            if c.isupper():
                fnname_snake += '_' + c.lower()
            else:
                fnname_snake += c
        # Some conventional exceptions :)
        fnname_snake = fnname_snake.replace('r_o_i', 'roi')
        return fnname_snake

    def generate(self, basedir):
        with open(basedir + '/visiontransfer/deviceparameters.h', 'r') as f:
            in_comment = False
            comment = ''
            level = 0
            for l in [ll.strip() for ll in f.readlines()]:
                if in_comment:
                    # Accumulate further lines for current docstring
                    end = l.find('*/')
                    thisline = (l if end<0 else l[:end]).lstrip('*').strip()
                    if thisline != '':
                        comment += '\n' + thisline
                    if end >= 0:
                        in_comment = False
                else:
                    start = l.find('/**')
                    if start >= 0:
                        # A docstring comment just started
                        in_comment = True
                        comment = l[start+3:]
                    else:
                        if level==1 and l.find(' DeviceParameters {') >= 0:
                            # insert class docstring
                            self.pyxcode.append(' '*4 + '_SUBSTITUTE_DOCSTRING_FOR_("visiontransfer::DeviceParameters")')
                            self.pyxcode.extend(self.pyxcode2)
                            self.pyxcode2 = []
                            comment = ''
                        elif level==2 and l.find('(') >= 0 and l.find('{') > 0 and (l.find('get') > 0 or l.find('set') > 0):
                            # This works because the parameter-specific getters/setters all are defined inline
                            #  while the generic ones (getNamed... etc.) are not (and thus do not have a curly brace!).
                            # Store return value, function name, argument list and docstring for all encountered accessors.
                            ret = l.split()[0]
                            fnname = l.split()[1].split('(')[0]
                            args = l.split('(')[1].split(')')[0]
                            self.add_pxd(ret, fnname, args)
                            self.add_pyx(ret, fnname, args, comment)
                            comment = ''
                        else:
                            pass
                level += l.count('{')
                level -= l.count('}')

if __name__=='__main__':
    basedir = os.getenv("LIBVISIONTRANSFER_SRCDIR", '../..')
    if os.path.isdir(basedir):
        g = Generator()
        g.generate(basedir)
        pathlib.Path("visiontransfer").mkdir(parents=True, exist_ok=True)
        with open('visiontransfer/visiontransfer_parameters_cpp_autogen.pxd', 'w') as f:
            f.write('\n'.join(g.pxdcode))
        with open('visiontransfer/visiontransfer_parameters_autogen.pyx.in', 'w') as f:
            f.write('\n'.join(g.pyxcode))
    else:
        print("Could not open library base dir, please set a correct LIBVISIONTRANSFER_SRCDIR")
