import logging
import logging.config
import logging.handlers
import corr
import time
import datetime
import sys
import os
import ConfigParser
from optparse import OptionParser

import AdcCalLoggingFileHandler
from ADCCalibrate import ADCCalibrate
from valon_katcp import ValonKATCP

# setup log file name:
current_time = datetime.datetime.now().strftime('%Y-%m%d-%H%M%S')
timestamp = "_%s"%(current_time)
AdcCalLoggingFileHandler.timestamp = timestamp

# load log config file
var = "YGOR_TELESCOPE"
confdir = '.' if not os.environ.has_key(var) else  os.path.join(os.environ[var], "etc/config")
conffile = "%s/%s" % (confdir, 'adc_cal_logging.conf')
if not os.path.isfile(conffile):
    print "Cannot find config file for logging: %s" % conffile
    sys.exit(0)

logging.config.fileConfig(conffile)
logger = logging.getLogger('adc5gLogging')
logger.info("Started")

def main():

    # TBF: we should read these from the $YGOR_TELESCOPE/etc/conf/vegas.conf file
    #roaches = ["vegasr2-2", "vegasr2-3"]
    #roaches = ["vegasr2-%d" % i for i in [4,5,6,7,8]]
    roaches = ["srbsr2-1"]
    for r in roaches:
         find_mmcms(r)
    #adc0s = [3, 9, None]
    #adc1s = [2, 2, 2]
    #adc0 = None
    #adc1 = None
    #print has_adc_difference(adc0, adc1, adc0s, adc1s)

def get_mmcm_info(fn, cp):
    "Reads the vegas.conf file and gathers info on modes"
    r = cp.read(fn)
    if len(r)==0:
        raise Exception("Could not read file: %s" % fn)

    sec = "MMCM"
    nentries = int(cp.get(sec, "num_entries"))
    logger.debug("Loading %d groups of entries in MMCM section." % nentries)
    info = []
    for i in range(nentries):
        opt = "mode[%d]" % i
        modes = cp.get(sec,opt)

        opt = "boff[%d]" % i
        bof = cp.get(sec,opt)

        opt = "freq[%d]" % i
        frq = cp.getfloat(sec,opt)

        opt = "adc0[%d]" % i
        try:
            adc0 = cp.getfloat(sec,opt)
        except ValueError:
            adc0 = None # there are Nones in here

        opt = "adc1[%d]" % i
        try:
            adc1 = cp.getfloat(sec,opt)
        except ValueError:
            adc1 = None

        info.append((modes, bof, frq, adc0, adc1))
        tmsg = "Modes: %s, Freq: %s, Bof: %s, Adc0: %s, Adc1: %s" % (modes, frq, bof, adc0, adc1)
        logger.debug(tmsg)
    return info    

def find_mmcms(roach_name):
    """
    For the given roach, determine all the MMCM optimal phase values
    for all the different combinations of bof file and frequency.
    """

    tmsg = 'Connecting to %s'%roach_name
    logger.info(tmsg)
    roach = corr.katcp_wrapper.FpgaClient(roach_name)
    time.sleep(1)
    if not roach.is_connected():
        raise Exception("Cannot connect to %s" % roach_name)

    # we'll need this to change the frequency
    valonSerial = "/dev/ttyS1" # this should never change
    v = ValonKATCP(roach, valonSerial) 

    # this is the object that will find the MMCM value
    cal = ADCCalibrate(dir = '.' #opts.dir 
                     , roach_name = roach_name
                     #, gpib_addr = gpibaddr
                     , roach = roach)
                     #, test = True)

    # read the config file and find the mmcm  through each mode
    fn = "%s-mmcm.conf" % roach_name
    logger.info("MMCM config file: %s" % fn)
    cp = ConfigParser.ConfigParser()

    info = get_mmcm_info(fn, cp)

    # mark this file as update
    cp.set("MMCM", "last_updated", datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"))

    #for mode, bof, frq, adc0, adc1 in info:
    for i in range(len(info)):
        modes, bof, frq, adc0, adc1 = info[i]
        # determine the MMCM optimal phase values for this combo
        # of bof file and frequency
        adc0s = []
        adc1s = []
        for trial in range(4):
            adc0, adc1 = find_this_mmcm(v, cal, roach, bof, frq)
            tmsg = "Found ADC mmcm's for trial %d: %s, %s" % (trial, adc0, adc1)
            logger.info(tmsg)
            if has_adc_difference(adc0, adc1, adc0s, adc1s):
                adc0s.append(adc0)
                adc1s.append(adc1)

        # write it to the conf file
        opt = "adc0[%d]" % i
        cp.set("MMCM", opt, value = ",".join([str(x) for x in adc0s]))
        opt = "adc1[%d]" % i
        cp.set("MMCM", opt, value = ",".join([str(x) for x in adc1s]))


    with open(fn, 'wb') as configfile:
        cp.write(configfile) 

def has_adc_difference(adc0, adc1, adc0s, adc1s):
    assert len(adc0s) == len(adc1s)
    if len(adc0s) == 0:
        return True
    has_diff = True    
    adcs = zip(adc0s, adc1s)    
    t = 4 # TBF?
    for i in range(len(adc0s)):
        #if ((abs(adc0s[i] - adc0) < tolerance) and (abs(adc1s[i] - adc1) < tolerance)): 
        if is_within_tolerance(adc0, adc0s[i], t) and is_within_tolerance(adc1, adc1s[i], t):
            has_diff = False
    return has_diff        

def is_within_tolerance(x, y, tolerance):
    # they are both None
    if x is None and y is None:
        return True
    # one of them is None and the other isn't    
    if x is None or y is None:
        return False
    # none of them are none
    return abs(x - y) < tolerance

def find_this_mmcm(valon, adcCal, roach, bof, freq):
    """
    Sets the given bof file and frequency (Hz) for a roach board using
    the given valon and ADCCalibration objects, returns the ADCs'
    MMCM optimal phase results.
    """

    # switch to the given bof file
    roach.progdev(bof)
    tmsg = "Roach BOF file set to: %s" % bof
    logger.info(tmsg)
    time.sleep(2)

    # we also need to switch to the given frequency
    valonSynth = 0 # neither should this (0: A, 8: B)
    current_clkrate = valon.get_frequency(valonSynth)
    tmsg = "Valon Synth set to frequency: %f MHz" % current_clkrate
    clkrate = freq / 1e6 # Hz -> MHz
    logger.info(tmsg)
    if abs(current_clkrate - clkrate) > 0.001:
        valon.set_frequency(valonSynth, clkrate)
        time.sleep(1)
        current_clkrate = valon.get_frequency(valonSynth)
        tmsg = "Valon Synth changed to frequency: %f MHz" % current_clkrate
        logger.info(tmsg)

    # Now actually find the MMCM optimal phase for each ADC
    set_phase = False # TBF?
    adcCal.set_zdok(0)
    adc0, g = adcCal.mmcm.calibrate_mmcm_phase(set_phase = set_phase)  
    tmsg = "MMCM (Opt. Phase, Glitches) for zdok %d: %s, %s" % (0, adc0, g)
    logger.info(tmsg)
    adcCal.set_zdok(1)
    adc1, g = adcCal.mmcm.calibrate_mmcm_phase(set_phase = set_phase)  
    tmsg = "MMCM (Opt. Phase, Glitches) for zdok %d: %s, %s" % (1, adc1, g)
    logger.info(tmsg)

    return adc0, adc1



if __name__ == "__main__":
    main()
