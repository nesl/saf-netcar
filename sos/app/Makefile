
PROJ = main_app

ROOTDIR = $(SOSROOT)


SRCS += accel_sampler.c
SRCS += loader.c
SRCS += rats.c linear.c
SRCS += SAF.c
SRCS += accel_sensor.c

INCDIR += -I$(ROOTDIR)/modules/sensordrivers/mts310/include/ -I../modules/

include $(ROOTDIR)/config/Makerules

vpath loader.c $(ROOTDIR)/extensions/loader
vpath rats.c $(ROOTDIR)/extensions/rats/
vpath linear.c $(ROOTDIR)/extensions/rats/
vpath accel_sampler.c ../modules/
ifeq ($(PROCESSOR), posix)
	vpath accel_sensor.c ../modules/
else
	vpath accel_sensor.c $(ROOTDIR)/modules/sensordrivers/mts310/accel/
	DEFS += -DMTS310SB
	SB = mts310
endif
vpath SAF.c ../modules/SAF/
