import os
import time
import logging
import corr
import fnmatch
import numpy as np
from numpy import random
from numpy import log
from datetime import datetime
from struct import pack, unpack
from matplotlib.pyplot import *

import AdcCalLoggingFileHandler
from SPI import SPI
from MMCM import MMCM
from GPIB import GPIB
from INL import INL
from OGP import OGP
from ADCConfFile import ADCConfFile
from AdcSnapshot import AdcSnapshot

logger = logging.getLogger('adc5gLogging')

class ADCCalibrate:

    """
    This is a high-level class responsible for the calibration
    of the two ADC cards (zdoks) in each of Vegas's Roach 2 boards.
    It may interact with the user, and leverages a suite of lower
    level helper classes.
    """

    def __init__(self
               , roach = None
               , roach_name = None
               , zdok = 0
               , gpib_addr = None
               , test = False
               , dir = '.'
               , now = None
               , config = False
               , bof = False
               , clockrate = None):

        self.zdok = zdok
        self.test = test
        self.dir = dir
        self.clockrate = clockrate if clockrate is not None else 1500.0
        self.config = 0 #config
        self.bof = bof

        # Removing this check because you may be using ADCCalibrate in a read-only
        # mode where gpib is not needed (since it is write-only, TBF)
        #if not test and gpib_addr is None:
        #   raise Exception, "Must specify gpib_addr if ADCCalibrate is not in test mode."

        if not test and roach_name is None:
           raise Exception, "Must specify Roach if ADCCalibrate is not in test mode."

        self.roach_name = roach_name if not test else "noroach"

        if not test and roach is None:
            self.roach = corr.katcp_wrapper.FpgaClient(self.roach_name)
            time.sleep(3)
            if not self.roach.is_connected():
                raise Exception, "%s did not work" % self.roach_name
        else:
            self.roach = roach

        self.now = datetime.now() if now is None else now

        self.time_frmt = '%Y-%m-%d-%H%M%S'
        self.current_time = self.now.strftime(self.time_frmt)

        #self.set_file_label()

        # helper classes
        self.gpib = GPIB(gpib_addr, test = test)
        self.spi = SPI(zdok = zdok, test = test, roach = self.roach)
        self.adc = AdcSnapshot(zdok = zdok, test = test, roach = self.roach, clockrate = self.clockrate)

        # higher-level classes
        self.ogp = OGP(zdok = zdok
                     , spi = self.spi
                     , adc = self.adc
                     , roach_name = roach_name
                     , clockrate = self.clockrate
                     , now = now
                     , dir = dir)
        self.inl = INL(zdok = zdok
                     , spi = self.spi
                     , roach_name = roach_name
                     , now = now
                     , dir = dir)
        self.mmcm = MMCM(zdok = zdok, spi = self.spi, adc = self.adc) 

        self.configFile = "%s-adc.conf" % roach_name
        self.configPath = "%s/%s" % (dir, self.configFile)
        self.cf = ADCConfFile(self.configPath)

        self.n_cores = 4
        self.cores = range(1,self.n_cores+1)

        #self.clockrate = 1500.0
        self.samp_freq = 2*self.clockrate
 
        # file prefixes
        self.post_mmcm_ramp_check_name = "post_mmcm_ramp_check"
        self.post_ramp_check_raw_name = "post_ramp_check_raw"
        self.raw_startup_name = "raw_startup"

        self.loaded_files = []

    def set_zdok(self, zdok):

        # Note: this is zdok - or ADC ('0' or '1') that 
        # the lower level classes interact with.  In this
        # upper level class we sometimes see zdok == '2',
        # which means "work on both '0' and '1'"
        # Pass it down
        self.spi.set_zdok(zdok)
        self.adc.set_zdok(zdok)
        self.ogp.set_zdok(zdok)
        self.inl.set_zdok(zdok)
        self.mmcm.set_zdok(zdok)

    #    self.set_file_label()

    def set_clockrate(self, clockrate):
        self.adc.set_clockrate(clockrate)
        self.ogp.set_clockrate(clockrate)

    def set_freq(self, freq):
        self.gpib.freq = freq

    def set_ampl(self, ampl):
        self.gpib.ampl = ampl

    def get_check_filename(self, title, zdoks):
        return "%s/%s_%s_zs%d_%s" % (self.dir
                                  , title
                                  , self.roach_name
                                  , zdoks
                                  , self.current_time)

    #def set_file_label(self):
    #    self.file_label = "_%s_z%d_%s" % (self.roach_name
    #                                    , self.zdok
    #                                    , self.current_time)

    #def get_post_ramp_check_raw_filename(self):
    #    return "post_ramp_check_raw%s" % self.file_label

    def user_input(self, prompt):

        prompt = "%s (Y/N)" % prompt
        logger.debug(prompt)
        response = raw_input(prompt)
        logger.debug("user response: \t%s" % response)
        return response in ["Y", "y"]
        
    def load_calibrations(self
                        , indir = None
                        , zdoks = None
                        , types = None
                        , use_conf = False
                        , freq = None):

        "Loads the most recent ogp, inl calibration files and loads them into the ADC Cards."

        # where to find the calibration files?
        if indir is None:
            var = "YGOR_TELESCOPE"
            if not os.environ.has_key(var):
                msg = "If directory for calibration files is not given, YGOR_TELESCOPE must be set."
                logger.debug(msg)
                raise Exception, msg 
            else:
                indir = os.path.join(os.environ[var], "etc/config") 
                
        # which zdok (ADC card) to load calibrations into?
        if zdoks is None or zdoks == 2:
            zdoks = range(2)
        elif zdoks == 0 or zdoks == 1:
            zdoks = [zdoks]
        else:    
            msg = "Zdoks value must be 0,1,2; unsupported: %d" % zdoks
            logger.debug(msg)
            raise Exception, msg 

        # which type of calibration?
        allTypes = ['ogp', 'inl']
        if types is None:
            types = allTypes 
        else:
            if not all([t in allTypes for t in types]):
                msg = "Types %s not in %s" % (types, allTypes)
                logger.debug(msg)
                raise Exception, msg 

        if use_conf and freq is None:
            msg = "Must specify freq (MHz) if .conf file is used for loading calibrations."
            logger.debug(msg)
            raise Exception, msg

        if use_conf:
            self.load_calibrations_from_conf(indir, zdoks, types, freq)
        else:
            # go through and find the most recent of each type
            # of file needed
            #example file: ogp_noroach_z0_2014-04-24-090838
            self.loaded_files = []
            for type in types: 
                for zdok in zdoks:
                    ext = "" if type == 'ogp' else ".meas"
                    base_name = "%s_%s_z%s_*%s" % (type, self.roach_name, zdok, ext)
                    # Rely on the timestamp at the end of the file name to make sure we
                    # get the most recent file
                    files = sorted([f for f in os.listdir(indir) if fnmatch.fnmatch(f, base_name)]
                                  , reverse = True)
                    if len(files) > 0:
                        f = "%s/%s" % (indir, files[0])
                        if type == 'ogp':
                            self.ogp.load_from_file(f, zdok = zdok)
                        else:    
                            self.inl.load_from_file(f, zdok = zdok)
                        logger.info("Loading file for calibration: %s" % f)    
                        self.loaded_files.append(f)    
                    else:
                        msg = "load_calibrations: Could not find files in %s matching pattern %s" % (indir, base_name)
                        logger.debug(msg)
                        raise Exception, msg 
                    
                    
    def load_calibrations_from_conf(self, indir, zdoks, types, freq):
        "Load calibrations from the <roach>-adc.conf file found in given directory."
        filename = "%s/%s" % (indir, self.configFile)
        self.cf.read_file(filename)
        for type in types:
            for zdok in zdoks:
                if type == 'ogp':
                    self.ogp.set_zdok(zdok)
                    self.ogp.spi.set_control()
                    self.ogp.set_offsets(self.cf.get_ogp_offsets(freq, zdok))
                    self.ogp.set_gains(  self.cf.get_ogp_gains(freq, zdok))
                    self.ogp.set_phases(  self.cf.get_ogp_phases(freq, zdok))
                elif type == 'inl':
                    self.inl.set_inls(self.cf.get_inls(zdok))


                    



    def do_ogp(self, zdoks, freq, n_trails):
        "Handles single zdok, or both"
        if zdoks==2:
           self.gpib.set_freq(freq)
           self.do_ogp(0, freq, n_trails)
           self.do_ogp(1, freq, n_trails)
        elif zdoks!=1 and zdoks!=0:
           logger.error("ZDOK " + str(zdoks) + " is not a valid input, aborting...")
        else:
           self.gpib.set_freq(freq)
           self.ogp.do_ogp(zdoks, freq, n_trails)
           if self.config:
               self.cf.write_ogps(self.clockrate*1e6, zdoks, self.ogp.ogps)
               self.cf.write_to_file()
           

    def do_inl(self, zdoks):
        "Handles single zdok, or both"
        if zdoks==2:
           self.do_inl(0)
           self.do_inl(1)
        elif zdoks!=1 and zdoks!=0:
           logger.error("ZDOK " + str(zdoks) + " is not a valid input, aborting...")
        else:
           self.inl.do_inl(zdoks)
           if self.config:
               self.cf.write_inls(zdoks, self.inl.inls)
               self.cf.write_to_file()

    def do_mmcm(self, zdok):
        "Handles single zdok, or both"
        if zdok==2:
            self.do_mmcm(0)
            self.do_mmcm(1)
        elif zdok==1 or zdok==0:
            logger.info("doing MMCM calibration for zdok " + str(zdok))
            self.mmcm.set_zdok(zdok)
            opt, g = self.mmcm.calibrate_mmcm_phase()
            logger.debug("MMCM (Optimal Phase, [Glitches]) for zdok " + str(zdok) + " : " + str((opt, g)))
            if self.config:
                self.cf.write_mmcms(self.bof, self.clockrate*1e6, zdok, opt)
                self.cf.write_to_file()
        else:
            logger.error("ZDOK " + str(zdok) + " is not a valid input")

    def gpib_test(self, zdok, freq, ampl, manual=True):
        logger.info("Checking if the synthesizer is connected correctly...")
        #if self.gpib is None:
        #    logger.info('Initializing the synthesizer...')
        #    try:
        #        with time_limit(15):
        #            self.gpib = GPIB(self.freq, self.ampl)
        #    except TimeoutException, msg:
        #        to_continue = 'N'
        #        logger.error("Time out trying to connect to the synthesizer at " \
        #                     + addr+ "...aborting...")
        #    time.sleep(2)
        logger.debug("ampl " + str(ampl))
        logger.debug("test_freq " + str(freq))
        self.gpib.set_freq(freq)
        self.gpib.set_ampl(ampl)
        if manual:
            self.check_raw(zdok, save=False)
            self.check_spec(zdok, save=False)
            tprompt = "Does the system look OK so far, and you wish to continue?"
            to_continue = self.user_input(tprompt)
        else:
           to_continue = True #'Y' 
        return to_continue 


    def get_ramp(self, zdok, set_mode = True):
        self.set_zdok(zdok)
        if set_mode:
            self.spi.set_test_mode()
        else:
            print "Getting Ramp WITHOUT setting to test mode!"
        snap_name = "adcsnap%s" % zdok #self.get_snap_name(zdok)
        a, b, c, d = self.adc.get_test_vector([snap_name], man_trig=True, wait_period=2)
        if set_mode:
            self.spi.unset_test_mode()
        return a, b, c, d
        
    def check_ramp(self, zdok, save=True, view=True, filename=None, set_mode = True): #"ramp"):
        filename = filename if filename is not None else self.get_check_filename(self.post_mmcm_ramp_check_name, zdok)
        # get test vectors
        logmsg = "Checking ramp test... zdok: "+str(zdok)+" save:" + str(save)
        logmsg += " filename: " + str(filename) + "\n"
        logger.info(logmsg)
        if zdok==2:
            a0, b0, c0, d0 = self.get_ramp(0, set_mode = set_mode)
            a1, b1, c1, d1 = self.get_ramp(1, set_mode = set_mode)
        elif zdok==0:
            a0, b0, c0, d0 = self.get_ramp(0, set_mode = set_mode)
            a1 = np.zeros(len(a0))
            b1 = np.zeros(len(b0))
            c1 = np.zeros(len(c0))
            d1 = np.zeros(len(d0))
        elif zdok==1:
            a1, b1, c1, d1 = self.get_ramp(1, set_mode = set_mode)
            a0 = np.zeros(len(a1))
            b0 = np.zeros(len(b1))
            c0 = np.zeros(len(c1))
            d0 = np.zeros(len(d1))
        else:
            logmsg = "Invalid input for zdok: "+ str(zdok) + " aborting..."
            logger.error(logmsg)

        # plot stuff    
        f = figure()
        ax0 = f.add_subplot(211)
        ax1 = f.add_subplot(212)
        ax0.plot(a0, '-o', b0, '-d', c0, '-^', d0, '-s')
        ax1.plot(a1, '-o', b1, '-d', c1, '-^', d1, '-s')
        ax0.set_title('ADC0')
        ax1.set_title('ADC1')
        f.suptitle(filename)
        if save:
            logger.debug("Saving file :%s"%(filename+'.png'))
            savefig(filename+'.png', dpi=300)
        if view:
            show()
        else:
            close()
        logger.debug("Now check raw data to make sure ADCs are back in data capturing mode...")
        # make sure the ADCs are succesfully set back to regular data capturing mode
        #self.check_raw(save=save, filename="post_ramp_check_raw" + timestamp)
        fn = self.get_check_filename(self.post_ramp_check_raw_name, zdok)
        self.check_raw(zdok, save=save, view=view, filename=fn)
    
    def check_raw(self, zdok, save=True, view=True, filename=None):
       
        filename = filename if filename is not None else self.get_check_filename(self.raw_startup_name, zdok)
        
        # get the data
        logmsg = "Checking raw data... zdok: "+str(zdok)+" save:" + str(save)
        logmsg += " filename: " + str(filename)
        logger.info(logmsg)
        if zdok == 2:
            raw0 = self.adc.get_raw(0)
            raw1 = self.adc.get_raw(1)  
        elif zdok == 0:
            raw0 = self.adc.get_raw(0)
            raw1 = np.zeros(len(raw0))
        elif zdok == 1:
            raw1 = self.adc.get_raw(1)
            raw0 = np.zeros(len(raw1))
        else:
            logmsg = "Invalid input for zdok: "+ str(zdok) + " aborting..."
            logger.error(logmsg)
        m0 = max(np.abs(raw0))
        m1 = max(np.abs(raw1))
        if m0>=128 or m1>=128:
            logger.warning("Power too high, clipping might be occurring...please check")

        # plot stuff    
        f = figure()
        ax0 = f.add_subplot(231)
        ax1 = f.add_subplot(234)
        ax0.plot(raw0, '-o')
        ax0.set_title('ADC0')
        ax1.plot(raw1, '-d')
        ax1.set_title('ADC1')
        ax00 = f.add_subplot(232)
        ax10 = f.add_subplot(235)
        ax00.plot(raw0[0:int(len(raw0)/100)], '-o')
        ax00.set_title('ADC0 - Zoom 100x')
        ax10.plot(raw1[0:int(len(raw0)/100)], '-d')
        ax10.set_title('ADC1 - Zoom 100x')
        ax01 = f.add_subplot(233)
        ax11 = f.add_subplot(236)
        ax01.plot(raw0[0:int(len(raw0)/20)], '-o')
        ax01.set_title('ADC0 - Zoom 20x')
        ax11.plot(raw1[0:int(len(raw0)/20)], '-d')
        ax11.set_title('ADC1 - Zoom 20x')
        f.suptitle(filename)
        f.text(0.5, 0.04, 'time', ha='center', va='center')
        f.text(0.06, 0.5, 'amplitude', ha='center', va='center', rotation='vertical')
        if save:
            logger.debug("Saving file :%s"%(filename+'.png'))
            f.set_size_inches(18, 12)
            savefig(filename+'.png', dpi=150)
        if view:
            show()
        else:
            close()
        return
            
    def check_spec(self, zdok, save=True,  view=True, filename = None): #filename="spec"):

        filename = filename if filename is not None else self.get_check_filename("spec", zdok)
        logmsg = "Checking spectrum... zdok: "+str(zdok)+" save:" + str(save)
        logmsg += " filename: " + str(filename) + "\n"
        logger.info(logmsg)
        if zdok == 2:
            nfr0 = self.adc.get_spec(0)
            spikes0 = self.adc.find_spike(nfr0)
            nfr1 =self.adc.get_spec(1)
            spikes1 = self.adc.find_spike(nfr1)
        elif zdok == 0:
            nfr0 = self.adc.get_spec(0)
            spikes0 = self.adc.find_spike(nfr0)
            nfr1 = np.zeros(len(nfr0)) - 1.0
            spikes1 = np.array([-1.0])
        elif zdok == 1:
            nfr1 = self.adc.get_spec(1)
            spikes1 = self.adc.find_spike(nfr1)
            nfr0 = np.zeros(len(nfr1)) - 1.0
            spikes0 = np.array([-1.0])
        else:
            logmsg = "Invalid input for zdok: "+ str(zdok) + " aborting..."
            logger.error(logmsg)
        nchan = len(nfr0) # this is NOT related to the FPGA design
        freqs = np.arange(0, self.clockrate, self.clockrate*1./nchan)
        logger.debug("Doing " + str(nchan) + " points FFT. ")
        logger.debug("Nyquist : " + str(self.clockrate) )
        logger.debug("Found spikes at %.4fMHz for ADC0"%spikes0)
        logger.debug("Found spikes at %.4fMHz for ADC1"%spikes1)

        # plot stuff
        f = figure()
        ax0 = f.add_subplot(211)
        ax1 = f.add_subplot(212)
        ax0.plot(freqs, 10*np.log(nfr0))
        ax0.annotate('spike ~%.4fMHz'%spikes0[0], xy=(spikes0[0], 0), xycoords='data', 
                  xytext=(spikes0[0]+500,-30), textcoords='data', 
                  arrowprops=dict(arrowstyle="->",connectionstyle="arc3"),
                  ha='right', va='top')
        ax0.set_title('ADC0')
        ax1y = 10*np.log(nfr1)
        ax1.plot(freqs, ax1y)
        ax1.annotate('spike ~%.4fMHz'%spikes1[0], xy=(spikes1[0], 0), xycoords='data', 
                  xytext=(spikes1[0]+500,-30), textcoords='data', 
                  arrowprops=dict(arrowstyle="->",connectionstyle="arc3"),
                  ha='right', va='top')
        info_str = ""
        if self.gpib.freq is not None:
            info_str += "Current input test tone frequency: %.4f"%self.gpib.freq
        if self.gpib.ampl is not None:    
            info_str += "\nCurrent input power level: %.4f"%self.gpib.ampl
        ax1.text(450, min(ax1y)+20, info_str, bbox={'facecolor':'yellow', 'alpha':0.9})
        ax1.set_title('ADC1')
        f.suptitle(filename)
        f.text(0.5, 0.04, 'frequency (MHz)', ha='center', va='center')
        f.text(0.06, 0.5, 'power (dB)', ha='center', va='center', rotation='vertical')
        if save:
            logger.debug("Saving file :%s"%(filename+'.png'))
            savefig(filename+'.png', dpi=300)
        if view:
            show()
        else:
            close()
        return
            
    def ampl_setup(self, zdok, manual=True, new_ampl=None, check_ampl=False):
        ampl = self.gpib.ampl
        # User interactions
        logmsg = "Changing input power level...current: " + str(ampl)
        logger.info(logmsg)
        if manual:
            tprompt = "Please enter the new Power level (dbM): (press enter to skip)"
            new_ampl_raw = raw_input(tprompt)
            logger.debug(tprompt)
            logger.debug("user input:    " + new_ampl_raw)
            if new_ampl_raw=="":
                logger.debug("Keeping current power level...")
                return
            else:
                new_ampl = float(new_ampl_raw)
        # TBF: these limits seem arbitrary        
        too_low = -15
        too_high = 10
        if check_ampl and (new_ampl<too_low or new_ampl>too_high):
            logmsg = "ampl " + str(new_ampl) + " too big or too small (range: " + str(too_low) + "-" + str(too_high) + ")"
            logger.error(logmsg)
            raise Exception, logmsg
            exit()
        # Finally, set the new amplitude    
        logger.debug(" New ampl is: " + str(new_ampl))
        ampl = new_ampl
        self.gpib.set_ampl(ampl)
        time.sleep(2)
        if manual:
            # Double check?
            tprompt = " Check raw ADC data now?" # (Y/N)"
            if self.user_input(tprompt):
            #logger.debug(tprompt)
            #to_check = raw_input(tprompt)
            #logger.debug("user input:    " + to_check)
            #if to_check=='Y' or to_check=='y':
                self.check_raw(zdok, save=False, view=True)
                # Add notes to logger 
                tprompt = "Does the raw data look okay? If not, "\
                           + "please briefly describe the problem here "\
                           + "(or press enter to proceed): "
                notes = raw_input(tprompt)
                logger.debug(notes)
                #if not isempty(notes):
                if len(notes) > 0:
                    logger.warning(notes)   

    def freq_setup(self, zdok, manual=True, freq=None):
        #global test_freq
        test_freq = freq if freq is not None else self.gpib.freq
        logmsg = "Changing input frequency...current: " + str(test_freq)
        logger.info(logmsg)
        if manual:
            tprompt = "Please enter the new test frequency (MHz): (press enter to skip)"
            logger.debug(tprompt)
            freq_raw = raw_input(tprompt)
            logger.debug("user input:    " + freq_raw)
            if freq_raw == "":
                logger.debug("Keeping current frequency...")
                return
            else:
                freq = float(freq_raw)
        if freq < 0 or freq > 1500:
            logmsg = "freq " + str(freq) + " too big or too small"
            logger.error(logmsg)
            raise Exception, logmsg
            exit()
        logger.debug(" New frequency is: " + str(freq))
        test_freq = freq
        self.gpib.set_freq(test_freq)
        time.sleep(2)
        if manual:
            tprompt = " Check raw ADC data now? (Y/N)"
            to_check = raw_input(tprompt)
            logger.debug(tprompt)
            logger.debug("user input:    " + to_check)
            if to_check=='Y' or to_check=='y':
                self.check_raw(zdok, save=False, view=True)
                tprompt = "Does the raw data look okay? If not, "\
                           + "please briefly describe the problem here "\
                           + "(or press enter to proceed): "
                notes = raw_input(tprompt)
                logger.debug(tprompt)
                logger.debug(notes)
                logger.warning(notes)

    def freq_scan(self, save=True,  view=True, filename=None): #"freq_scan"):

        filename = filename if filename is not None else self.get_check_filename("freq_scan", 2)

        test_freq = self.gpib.freq
        logger.info("Starting frequency scan (both ADCs)... save: " +str(save))

        # Gather the data
        freqs = []
        f0 = []
        f1 = []
        spikes0_arr = []
        spikes1_arr = []
        rng = 50
        for i in range(0, rng):
            test_freq = i*30+random.random()*30
            logger.debug("freq : " + str(test_freq))
            self.gpib.set_freq(test_freq)
            time.sleep(2)
            nfr0 = self.adc.get_spec(0) 
            spikes0 = self.adc.find_spike(nfr0)
            nfr1 = self.adc.get_spec(1)
            spikes1 = self.adc.find_spike(nfr1)
            logger.debug("Found spikes at %.4fMHz for ADC0"%spikes0)
            logger.debug("Found spikes at %.4fMHz for ADC1"%spikes1)
            freqs.append(test_freq)
            f0.append(10*log(nfr0))
            f1.append(10*log(nfr1))
            spikes0_arr.append(spikes0)
            spikes1_arr.append(spikes1)

        # plot it!    
        f = figure()
        ax0 = f.add_subplot(211)
        ax1 = f.add_subplot(212)
        logger.debug(" Plotting now...")
        nchan = len(nfr0) # this is NOT related to the FPGA design
        freqs_ind = np.arange(0, self.clockrate, self.clockrate*1./nchan)
        for i in range(1, rng, 10):
            logger.debug(" \ttest_freq: " + str(freqs[i]))
            ax0.plot(freqs_ind, f0[i])
            ax0.annotate('spike ~%.4fMHz'%spikes0_arr[i][0], xy=(spikes0_arr[i][0], 0), xycoords='data', 
                      xytext=(spikes0_arr[i][0]+500,-1*i), textcoords='data', 
                      arrowprops=dict(arrowstyle="->",connectionstyle="arc3"),
                      ha='right', va='top')
            logger.debug(" \tannotated spike (ADC0): %.4fMHz"%spikes0_arr[i][0])
            ax1.plot(freqs_ind, f1[i])
            ax1.annotate('spike ~%.4fMHz'%spikes1_arr[i][0], xy=(spikes1_arr[i][0], 0), xycoords='data', 
                      xytext=(spikes1_arr[i][0]+500,-1*i), textcoords='data', 
                      arrowprops=dict(arrowstyle="->",connectionstyle="arc3"),
                      ha='right', va='top')
            logger.debug(" \tannotated spike (ADC1): %.4fMHz"%spikes1_arr[i][0])
        ax0.set_title('ADC0')
        ax1.set_title('ADC1')
        f.suptitle(filename)
        info_str = "Current input power level: %.4f"%self.gpib.ampl
        ax1.text(450, min(f1[0])+20, info_str, bbox={'facecolor':'yellow', 'alpha':0.9})
        f.text(0.5, 0.04, 'frequency (MHz)', ha='center', va='center')
        f.text(0.06, 0.5, 'power (dB)', ha='center', va='center', rotation='vertical')
        if save:
            logger.debug("Saving file :%s"%(filename+'.png'))
            savefig(filename+'.png', dpi=300)
        if view:
            show() 
        else:
            close()
    
if __name__ == "__main__":

    AdcCalLoggingFileHandler.timestamp = "_"

    logging.config.fileConfig('adc5g_logging_config.conf')
    logger = logging.getLogger('adc5gLogging')
    logger.info("Started")

    import corr
    rn = 'srbsr2-1'
    test = False #False

    roach = corr.katcp_wrapper.FpgaClient(rn)
    time.sleep(3)
    print "connected: ", roach.is_connected()
    adc = ADCCalibrate(dir = 'tmp2', roach = roach , test = test, roach_name = rn)

    #adc.check_raw()
    #adc.check_ramp()
    adc.check_spec()
    #adc.ampl_setup(new_ampl = 1.0)



