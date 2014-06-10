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

class ADCCalibrations:

    def __init__(self, dir = None, roaches = None, mmcm_trials = None):

        self.dir = dir if dir is not None else '.'

        self.roaches = roaches if roaches is not None else self.get_roach_names_from_config()

        self.banks = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

        # mmcms
        self.mmcm_trials = mmcm_trials if mmcm_trials is not None else 5
        self.mmcm_tolerance = 4

        
        # ogps/inls
        self.ogp_bof = 'h1k_ver106_2014_Apr_11_1612.bof'
        # TBF: how to change this?
        self.testfreq = 18.3105 # MHz
        self.ogp_trials = 10

        # helper classes
        self.cp = ConfigParser.ConfigParser()
        self.valon = None
        self.cal = None
        self.adcConf = None

    def find_all_ogps(self):
        for r in self.roaches:
            self.find_ogps(r)

    def find_all_mmcms(self):
        for r in self.roaches:
            self.find_mmcms(r)

    def get_roach_names_from_config(self):
    
        fn = "%s/%s" % (self.dir, "vegas.conf")
        r = cp.read(fn)
        if len(r)==0:
            print "Could not find roach names from: ", fn
            return []
        
        # what banks to read?
        sec = "DEFAULTS"
        subsys = self.cp.get(sec, "subsystems")
        subsys = [int(s) for s in subsys.split(',')]
    
        # what roaches corresopond to those banks?
        roaches = []
        for s in subsys:
            bank = self.banks[s-1]
            sec = "BANK%s" % bank
            # roach_host = vegasr2-1.gb.nrao.edu
            roaches.append(cp.get(sec, "roach_host").split('.')[0])
        return roaches    
        
    def get_config_filename(self, roach_name): 
        fn = "%s/%s-adc.conf" % (self.dir, roach_name)
        logger.info("MMCM config file: %s" % fn)
        return fn

    def init_for_roach(self, roach_name):

        # connect to roach
        tmsg = 'Connecting to %s'%roach_name
        logger.info(tmsg)
        self.roach = corr.katcp_wrapper.FpgaClient(roach_name)
        time.sleep(1)
        if not self.roach.is_connected():
            raise Exception("Cannot connect to %s" % roach_name)
    
        # we'll need this to change the frequency
        valonSerial = "/dev/ttyS1" # this should never change
        self.valon = ValonKATCP(self.roach, valonSerial) 
    
        # this is the object that will find the MMCM value
        self.cal = ADCCalibrate(dir = '.' #opts.dir 
                         , roach_name = roach_name
                         #, gpib_addr = gpibaddr
                         , roach = self.roach)
                         #, test = True)
    
        # read the config file and find the mmcm  through each mode
        fn = self.get_config_filename(roach_name)
        self.adcConf = ADCConfFile(fn)

    def find_ogps(self, roach_name):

        self.init_for_roach(roach_name)

        for frq, value in self.adcConf.ogp_info.items():
            #i, ogp0, ogp1 = value
            # determine the OGP values for this clockrate
            tmsg = "Finding OGPs for clockrate: %s" % frq
            logger.info(tmsg)
            ogp0, ogp1 = self.find_this_ogp(frq)
            self.adcConf.write_ogps(frq, 0, ogp0)
            self.adcConf.write_ogps(frq, 1, ogp1)

        self.adcConf.write_to_file()

    def change_bof(self, bof):

        # switch to the given bof file
        self.roach.progdev(bof)
        tmsg = "Roach BOF file set to: %s" % bof
        logger.info(tmsg)
        time.sleep(2)
    
    def change_frequency(self, freq):

        # we also need to switch to the given frequency
        valonSynth = 0 # neither should this (0: A, 8: B)
        current_clkrate = self.valon.get_frequency(valonSynth)
        tmsg = "Valon Synth set to frequency: %f MHz" % current_clkrate
        clkrate = freq / 1e6 # Hz -> MHz
        logger.info(tmsg)
        if abs(current_clkrate - clkrate) > 0.001:
            self.valon.set_frequency(valonSynth, clkrate)
            time.sleep(1)
            current_clkrate = self.valon.get_frequency(valonSynth)
            tmsg = "Valon Synth changed to frequency: %f MHz" % current_clkrate
            logger.info(tmsg)

    def find_this_ogp(self, freq):

    
        self.change_bof(self.ogp_bof)

        self.change_frequency(freq)

        # since we reprogrammed the roach, mmcm calibrate
        self.cal.do_mmcm(2)

        # now find the ogps
        self.cal.do_ogp(0, self.testfreq, self.ogp_trials)
        #self.adcConf.write_ogps(freq, 0, self.cal.ogp.ogps)
        ogp0 = self.cal.ogp.ogps
        self.cal.do_ogp(0, self.testfreq, self.ogp_trials)
        #self.adcConf.write_ogps(freq, 0, self.cal.ogp.ogps)
        ogp1 = self.cal.ogp.ogps
        return ogp0, ogp1

    def find_mmcms(self, roach_name):
        """
        For the given roach, determine all the MMCM optimal phase values
        for all the different combinations of bof file and frequency.
        """
   
        self.init_for_roach(roach_name)
    
        for key, value in self.adcConf.mmcm_info.items():
            bof, frq = key
            i, adc0, adc1, _ = value
            # determine the MMCM optimal phase values for this combo
            # of bof file and frequency
            adc0s = []
            adc1s = []
            for trial in range(self.mmcm_trials):
                adc0, adc1 = self.find_this_mmcm(bof, frq) #v, cal, roach, bof, frq)
                tmsg = "Found ADC mmcm's for trial %d: %s, %s" % (trial, adc0, adc1)
                print tmsg
                logger.info(tmsg)
                if self.has_adc_difference(adc0, adc1, adc0s, adc1s):
                    adc0s.append(adc0)
                    adc1s.append(adc1)
    
            self.adcConf.write_mmcms(bof, frq, 0, adc0s)
            self.adcConf.write_mmcms(bof, frq, 1, adc1s)
    
        self.adcConf.write_to_file()
    
    def has_adc_difference(self, adc0, adc1, adc0s, adc1s):
        assert len(adc0s) == len(adc1s)
        if len(adc0s) == 0:
            return True
        has_diff = True    
        adcs = zip(adc0s, adc1s)    
        t = self.mmcm_tolerance 
        for i in range(len(adc0s)):
            #if ((abs(adc0s[i] - adc0) < tolerance) and (abs(adc1s[i] - adc1) < tolerance)): 
            if self.is_within_tolerance(adc0, adc0s[i], t) \
                and self.is_within_tolerance(adc1, adc1s[i], t):
                has_diff = False
        return has_diff        
    
    def is_within_tolerance(self, x, y, tolerance):
        # they are both None
        if x is None and y is None:
            return True
        # one of them is None and the other isn't    
        if x is None or y is None:
            return True # if this were False we'd get None's written to .conf!
        # none of them are none
        return abs(x - y) < tolerance
    
    def find_this_mmcm(self, bof, freq): #valon, adcCal, roach, bof, freq):
        """
        Sets the given bof file and frequency (Hz) for a roach board using
        the given valon and ADCCalibration objects, returns the ADCs'
        MMCM optimal phase results.
        """
    
        # switch to the given bof file
        self.change_bof(bof)
    
        # we also need to switch to the given frequency
        self.change_frequency(freq)
    
        # Now actually find the MMCM optimal phase for each ADC
        set_phase = False # TBF?
        self.cal.set_zdok(0)
        adc0, g = self.cal.mmcm.calibrate_mmcm_phase(set_phase = set_phase)  
        tmsg = "MMCM (Opt. Phase, Glitches) for zdok %d: %s, %s" % (0, adc0, g)
        logger.info(tmsg)
        self.cal.set_zdok(1)
        adc1, g = self.cal.mmcm.calibrate_mmcm_phase(set_phase = set_phase)  
        tmsg = "MMCM (Opt. Phase, Glitches) for zdok %d: %s, %s" % (1, adc1, g)
        logger.info(tmsg)
    
        return adc0, adc1
            
if __name__ == "__main__":    
    logger = logging.getLogger('adc5gLogging')
    logger.info("Started")
    cals = ADCCalibrations(roaches = ['srbsr2-1'], mmcm_trials = 1)
    #cals.find_all_mmcms()
    cals.find_all_ogps()

