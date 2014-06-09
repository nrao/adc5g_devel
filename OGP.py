import time
import logging
import numpy as np
from datetime import datetime

import fit_cores

logger = logging.getLogger('adc5gLogging')

class OGP:

    def __init__(self, zdok = 0, dir = None, gpib = None, spi = None, adc = None, now = None, roach_name = None, test = False, clockrate = None):

        self.dir = dir
        self.test = test
        self.roach_name = roach_name if roach_name is not None else "noroach" 
        self.set_clockrate(clockrate)

        self.gpib = gpib
        self.spi = spi
        self.adc = adc

        self.now = datetime.now() if now is None else now

        self.time_frmt = '%Y-%m-%d-%H%M%S'
        self.current_time = self.now.strftime(self.time_frmt)

        self.set_zdok(zdok)
        self.set_file_label()

        self.n_cores = 4
        self.cores = range(1,self.n_cores+1)

        #self.samp_freq = 2*self.clockrate
        self.ogps = []

    def set_clockrate(self, clockrate):
        self.clockrate = clockrate
        self.samp_freq = self.clockrate * 2

    def set_zdok(self, zdok):
        assert zdok == 0 or zdok == 1
        self.zdok = zdok
        if self.spi is not None:
            self.spi.set_zdok(zdok)
        if self.adc is not None:
            self.adc.set_zdok(zdok)
        self.set_file_label()    

    def set_file_label(self):
        self.file_label = "_%s_z%d_%s" % (self.roach_name
                                        , self.zdok
                                        , self.current_time)  
    def get_ogp_filename(self):
        return "%s/ogp%s" % (self.dir, self.file_label)

    def get_snapshot_filename(self):
        return "%s/snapshot_raw%s.dat" % (self.dir, self.file_label)

    def load_from_file(self, filename, zdok = None):
        """
         Clear the control register and then load the offset, gain and phase
         registers for each core.  These values are hard coded for now.
        """
        if zdok is not None:
            self.set_zdok(zdok)
        self.spi.set_control() 
        t = np.genfromtxt(filename)
        # split these up by type and channel
        offs   = [t[i] for i in range(0,10,3)]
        gains  = [t[i] for i in range(1,11,3)]
        phases = [t[i] for i in range(2,12,3)]
        # and send them down
        self.set_offsets(offs)
        self.set_gains(gains)
        self.set_phases(phases)    

    def set_offsets(self, values):
        assert (len(values) == self.n_cores)
        for i in range(self.n_cores):
            self.spi.set_offset(self.cores[i], values[i])

    def set_gains(self, values):
        assert (len(values) == self.n_cores)
        for i in range(self.n_cores):
            self.spi.set_gain(self.cores[i], values[i])

    def set_phases(self, values):
        assert (len(values) == self.n_cores)
        for i in range(self.n_cores):
            self.spi.set_phase(self.cores[i], values[i])

    def do_ogp(self, zdok, test_freq=18.3105, repeat=10): 

        self.set_zdok(zdok)

        time.sleep(1)
      
        logger.debug('doing ogp calibration for zdok %d' % zdok)
        logger.debug('test_freq: ' + str(test_freq) + '  repeat: ' + str(repeat))

        #timestamp = "_"
        #FNAME = 'snapshot_adc%d_raw%s.dat'%(zdok, timestamp)
    
        logger.debug("Clearing OGP")
        #rww_tools.clear_ogp()
        self.clear_ogp()
        logger.debug("sleeping for 1 secs")
        time.sleep(1)

        #ogp, sinad = rww_tools.dosnap(fr=test_freq,name=FNAME,rpt=repeat,donot_clear=False)
        fname = self.get_snapshot_filename()
        ogp, sinad = self.do_snap(freq = test_freq
                                , fname = fname
                                , repeat = repeat
                                , donot_clear = False)

        #ogp = np.zeros(16)
        #sinad = np.zeros(10)
        
        self.ogps = ogp[3:]
        logger.debug('OGP:' + str(self.ogps))
        logger.debug('SINAD:' + str(sinad))
    
        np.savetxt(self.get_ogp_filename(), self.ogps, fmt='%8.4f')
    
        # TBF: just use what's in memory, instead of the file
        logger.debug('Setting ogp')
        self.load_from_file(self.get_ogp_filename())
        logger.debug('done')

    def clear_ogp(self):
        "Sets Offset, Gain, and Phase for all cores to zero."

        for core in self.cores:
            self.spi.set_gain(core, 0)
            self.spi.set_offset(core, 0)
            self.spi.set_phase(core, 0)

    def do_snap(self, freq=0, fname="t", repeat = 1, donot_clear=False):
        """
        Takes a snapshot and uses fit_cores to fit a sine function to each
        core separately assuming a CW signal is connected to the input.  The
        offset, gain and phase differences are reoprted for each core as
        well as the average of all four.
      
        The parameters are:
          fr   The frequency of the signal generator.  It will default to the last
               frequency set by set_freq()
          name the name of the file into which the snapshot is written.  5 other
               files are written.  Name.c1 .. name.c4 contain themeasurements from
           cores a, b, c and d.  Note that data is taken from cores in the order
           a, c, b, d.  A line is appended to the file name.fit containing
           signal freq, average zero, average amplitude followed by triplets
           of zero, amplitude and phase differences for cores a, b, c and d
      
          rpt  The number of repeats.  Defaults to 1.  The c1 .. c4 files mentioned
               above are overwritten with each repeat, but new rows of data are added
           to the .fit file for each pass.
        """
        avg_pwr_sinad = 0
        for i in range(repeat):
          # We skip this interaction with hardware if this is a test, use 
          if not self.test:
              snap = self.adc.get_adc_snapshot(man_trig=True, wait_period=2)
              np.savetxt(fname, snap,fmt='%d')
              fname2 = fname
          else:
              # if we're testing, use the intermediate files
              fname2 = "%s.%d" % (fname, i)
          ogp, pwr_sinad = fit_cores.fit_snap(freq
                                            , self.samp_freq
                                            , fname2
                                            , clear_avgs = i == 0 and not donot_clear
                                            , prnt = i == repeat-1)
          avg_pwr_sinad += pwr_sinad
        return ogp, avg_pwr_sinad/repeat        
