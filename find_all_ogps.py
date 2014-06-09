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
         find_ogps(r)
    #adc0s = [3, 9, None]
    #adc1s = [2, 2, 2]
    #adc0 = None
    #adc1 = None
    #print has_adc_difference(adc0, adc1, adc0s, adc1s)

def get_info(fn, cp):
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

        #opt = "adc0[%d]" % i
        #try:
        #    adc0 = cp.getfloat(sec,opt)
        #except ValueError:
        #    adc0 = None # there are Nones in here
#
        #opt = "adc1[%d]" % i
        #try:
        #    adc1 = cp.getfloat(sec,opt)
        #except ValueError:
        #    adc1 = None
        adc0 = adc1 = 0

        info.append((modes, bof, frq, adc0, adc1))
        tmsg = "Modes: %s, Freq: %s, Bof: %s, Adc0: %s, Adc1: %s" % (modes, frq, bof, adc0, adc1)
        logger.debug(tmsg)
    return info    

def find_ogps(roach_name):
    """
    For the given roach, determine all the OGPs 
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
    gpibaddr = '10.16.96.174' # tape room
    cal = ADCCalibrate(dir = '.' #opts.dir 
                     , roach_name = roach_name
                     , gpib_addr = gpibaddr
                     , roach = roach)
                     #, test = True)

    # read the config file and find the mmcm  through each mode
    fn = "%s-ogp.conf" % roach_name
    logger.info("ADC cal config file: %s" % fn)
    cp = ConfigParser.ConfigParser()

    info = get_info(fn, cp)

    # mark this file as update
    #cp.set("MMCM", "last_updated", datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"))

    #for mode, bof, frq, adc0, adc1 in info:
    for i in [len(info)-1]: #range(len(info)):
        modes, bof, frq, adc0, adc1 = info[i]
        # determine the MMCM optimal phase values for this combo
        # of bof file and frequency

        ogp0, inl0, ogp1, inl1 = find_this_ogp(v, cal, roach, bof, frq)
        ogp0str = ",".join(["%8.4f" % x for x in ogp0])
        ogp1str = ",".join(["%8.4f" % x for x in ogp1])
        inl0str = "%s" % [list(x) for x in inl0]
        inl1str = "%s" % [list(x) for x in inl1]
        #tmsg = "Found ADC mmcm's for trial %d: %s, %s" % (trial, adc0, adc1)
        tmsg = "Found ADC ogps for adc0 %s: " % ogp0str 
        logger.info(tmsg)
        tmsg = "Found ADC ogps for adc1 %s: " % ogp1str 
        logger.info(tmsg)
        tmsg = "Found ADC inls for adc0 %s: " % inl0str 
        logger.info(tmsg)
        tmsg = "Found ADC inls for adc1 %s: " % inl1str 
        logger.info(tmsg)

        # write it to the conf file
        opt = "ogp0[%d]" % i
        cp.set("MMCM", opt, value = ogp0str) 
        opt = "ogp1[%d]" % i
        cp.set("MMCM", opt, value = ogp1str)

        opt = "inl0[%d]" % i
        cp.set("MMCM", opt, value = inl0str) 
        opt = "inl1[%d]" % i
        cp.set("MMCM", opt, value = inl1str) 

        with open(fn, 'wb') as configfile:
            cp.write(configfile) 

def find_this_ogp(valon, adcCal, roach, bof, freq):
    """
    Sets the given bof file and frequency (Hz) for a roach board using
    the given valon and ADCCalibration objects, returns the ADCs'
    MMCM optimal phase results.
    """

    # switch to the given bof file
    roach.progdev(bof)
    tmsg = "************** Roach BOF file set to: %s" % bof
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
        tmsg = "************** Valon Synth changed to frequency: %f MHz" % current_clkrate
        logger.info(tmsg)


    # Now actually find the MMCM optimal phase for each ADC
    #set_phase = False # TBF?
    #adcCal.set_zdok(0)
    #adc0, g = adcCal.mmcm.calibrate_mmcm_phase(set_phase = set_phase)  
    #tmsg = "MMCM (Opt. Phase, Glitches) for zdok %d: %s, %s" % (0, adc0, g)
    #logger.info(tmsg)
    #adcCal.set_zdok(1)
    #adc1, g = adcCal.mmcm.calibrate_mmcm_phase(set_phase = set_phase)  
    #tmsg = "MMCM (Opt. Phase, Glitches) for zdok %d: %s, %s" % (1, adc1, g)
    #logger.info(tmsg)

    adcCal.set_clockrate(clkrate)

    adcCal.do_mmcm(2)
    testfreq = 18.3105 # MHz
    amp = -3.0
    n_trails = 10

    adcCal.gpib_test(2, testfreq, amp, manual=False)



    #adcCal.gpib_test(0, testfreq, amp, manual=False)
    adcCal.set_zdok(0)
    adcCal.ogp.do_ogp(0)  
    adc0 = adcCal.ogp.ogps
    adcCal.inl.do_inl(0)  
    inl0 = adcCal.inl.inls

    #adcCal.gpib_test(1, testfreq, amp, manual=False)
    adcCal.set_zdok(1)
    adcCal.ogp.do_ogp(1)  
    adc1 = adcCal.ogp.ogps
    adcCal.inl.do_inl(1)  
    inl1 = adcCal.inl.inls

    return adc0, inl0, adc1, inl1



if __name__ == "__main__":
    main()
