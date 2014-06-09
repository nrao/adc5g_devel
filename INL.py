import time
import logging
import numpy as np
from datetime import datetime

import fit_cores

logger = logging.getLogger('adc5gLogging')

class INL:

    def __init__(self, zdok = 0, dir = None, spi = None, now = None, roach_name = None, test = False):

        self.dir = dir
        self.test = test

        self.roach_name = roach_name if roach_name is not None else "noroach" 

        self.spi = spi

        self.now = datetime.now() if now is None else now

        self.time_frmt = '%Y-%m-%d-%H%M%S'
        self.current_time = self.now.strftime(self.time_frmt)

        self.set_zdok(zdok)
        self.set_file_label()

        self.n_cores = 4
        self.cores = range(1,self.n_cores+1)

        self.inls = []

    def set_zdok(self, zdok):
        assert zdok == 0 or zdok == 1
        self.zdok = zdok
        if self.spi is not None:
            self.spi.set_zdok(zdok)
        self.set_file_label()    

    def set_file_label(self):
        self.file_label = "_%s_z%d_%s" % (self.roach_name
                                        , self.zdok
                                        , self.current_time)

    def get_snapshot_filename(self):
        return "%s/snapshot_raw%s.dat" % (self.dir, self.file_label)

    def get_snapshot_res_filename(self):
        return "%s.res" % self.get_snapshot_filename()

    def get_inl_meas_filename(self):
        return "%s/inl%s.meas" % (self.dir, self.file_label)

    def get_inl_filename(self):
        return "%s/inl%s" % (self.dir, self.file_label)

    def load_from_file(self, filename, zdok = None):
        """
        Set the INL registers for all four cores from a file containing 17 rows
        of 5 columns.  The first column contains the level and is ignored.
        Columns 2-5 contain the inl correction for cores a-d
        """
        if zdok is not None:
            self.set_zdok(zdok)
        c = np.genfromtxt(filename, usecols=(1,2,3,4), unpack=True)
        for i in range(self.n_cores):
            self.spi.set_inl_registers(self.cores[i], c[i])

    def do_inl(self, zdok):
       
        self.set_zdok(zdok)

        #timestamp = '_'
        #FNAME = 'snapshot_adc%d_raw%s.dat'%(zdok, timestamp)
        #rww_init(zdok, clockrate)
  
        logger.debug('doing inl calibration for zdok ' + str(zdok))
    
        logger.debug("Clearing INL")
        #rww_tools.clear_inl()
        self.clear_inl()
        logger.debug("sleeping for 1 secs")
        time.sleep(1)

        #fit_cores.fit_inl(FNAME + ".res")
        # The .res file used here is a 256 by 4 (by cores?) list of residuals.  TBF: who writes this?
        # This is used to compute the INLs, which are stored in inl*.meas
        self.inls = fit_cores.fit_inl(self.get_snapshot_res_filename(), outname = self.get_inl_meas_filename())

        #rww_tools.update_inl(fname = 'inl%s.meas'%timestamp)
        self.update_inl() #fname = self.get_inl_meas_filename())
        logger.debug('INL done')

    def clear_inl(self):
        "Clear the INL registers on the ADC"
        offs = [0.0]*17
        #for chan in range(1,5):
        for chan in self.cores:
            self.spi.set_inl_registers(chan, offs)

    def update_inl(self, fname = None, set=True):
        """
        Retreive the INL data from the ADC and add in the corrections from
        the measured inl (in inl.meas).  Store in the file 'inl'
        """
        fname = fname if fname is not None else self.get_inl_meas_filename()

        cur_inl = self.get_inl_array()
        meas_inl = np.genfromtxt(fname)
        for level in range(17):
          cur_inl[level][1:] += meas_inl[level][1:]
        #inlfn = "inl" + timestamp
        inlfn = self.get_inl_filename()
        logger.debug("savtxt to ..." + inlfn)
        np.savetxt(inlfn, cur_inl, fmt=('%3d','%7.4f','%7.4f','%7.4f','%7.4f'))
        if set:
          self.set_inl(fname)

    def get_inl_array(self):
        """
        Read the INL corrections from the adc and put in an array
        """
        inl = np.zeros((5,17), dtype='float')
        for chan in range(1,5):
          inl[chan] = self.spi.get_inl_registers(chan)
        inl[0] = range(0, 257,16)
        return inl.transpose()

    def set_inl(self, fname):
        """
        Set the INL registers for all four cores from a file containing 17 rows
        of 5 columns.  The first column contains the level and is ignored.
        Columns 2-5 contain the inl correction for cores a-d
        """
        c = np.genfromtxt(fname, usecols=(1,2,3,4), unpack=True)
        for i in range(self.n_cores):
            self.spi.set_inl_registers(self.cores[i], c[i])

