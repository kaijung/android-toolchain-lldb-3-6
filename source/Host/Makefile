##===- source/Host/Makefile --------------------------------*- Makefile -*-===##
# 
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
# 
##===----------------------------------------------------------------------===##

LLDB_LEVEL := ../..

include $(LLDB_LEVEL)/../../Makefile.config

DIRS := common

ifeq ($(HOST_OS),Darwin)
DIRS += posix
DIRS += macosx
endif

ifeq ($(HOST_OS),Linux)
DIRS += posix
DIRS += linux
endif

ifneq (,$(filter $(HOST_OS), FreeBSD GNU/kFreeBSD))
DIRS += posix
DIRS += freebsd
endif

ifeq ($(HOST_OS),MingW)
DIRS += windows
endif

include $(LLDB_LEVEL)/Makefile
