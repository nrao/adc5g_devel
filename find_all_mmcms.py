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
from ADCConfFile import ADCConfFile
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
    #sys.exit(0)
else:
    logging.config.fileConfig(conffile)

logger = logging.getLogger('adc5gLogging')
logger.info("Started")

def main():

    if len(sys.argv) == 1:
       # no roach names supplied in arguments, use vegas.conf
       roaches = get_roach_names_from_config(confdir)
    else:
       # use the passed in name
       roaches = sys.argv[1].split(',')

    # examples:   
    #roaches = ["vegasr2-%d" % i for i in range(1,9)] 
    #roaches = ["srbsr2-1"]

    print "roaches: ", roaches
    for r in roaches:
         find_mmcms(r)

def get_roach_names_from_config(confdir):

    fn = "%s/%s" % (confdir, "vegas.conf")
    cp = ConfigParser.ConfigParser()
    r = cp.read(fn)
    if len(r)==0:
        print "Could not find roach names from: ", fn
        return []
    
    # what banks to read?
    sec = "DEFAULTS"
    subsys = cp.get(sec, "subsystems")
    subsys = [int(s) for s in subsys.split(',')]
    banks = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

    # what roaches corresopond to those banks?
    roaches = []
    for s in subsys:
        bank = banks[s-1]
        sec = "BANK%s" % bank
        # roach_host = vegasr2-1.gb.nrao.edu
        roaches.append(cp.get(sec, "roach_host").split('.')[0])
    return roaches    
    
def get_config_filename(roach_name): 
    fn = "%s/%s-adc.conf" % (confdir, roach_name)
    logger.info("MMCM config file: %s" % fn)
    return fn

def find_mmcms(roach_name):
    """
    For the given roach, determine all the MMCM optimal phase values
    for all the different combinations of bof file and frequency.
    """

    # connect to roach
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
    fn = get_config_filename(roach_name)
    cp = ADCConfFile(fn)

    for key, value in cp.mmcm_info.items():
        bof, frq = key
        i, adc0, adc1, _ = value
        # determine the MMCM optimal phase values for this combo
        # of bof file and frequency
        adc0s = []
        adc1s = []
        trails = 1
        for trial in range(trails):
            adc0, adc1 = find_this_mmcm(v, cal, roach, bof, frq)
            tmsg = "Found ADC mmcm's for trial %d: %s, %s" % (trial, adc0, adc1)
            print tmsg
            logger.info(tmsg)
            if has_adc_difference(adc0, adc1, adc0s, adc1s):
                adc0s.append(adc0)
                adc1s.append(adc1)

        cp.write_mmcms(bof, frq, 0, adc0s)
        cp.write_mmcms(bof, frq, 1, adc1s)

    cp.write_to_file()

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
        return True # if this were False we'd get None's written to .conf!
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
