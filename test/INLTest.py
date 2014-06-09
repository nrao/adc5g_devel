
import unittest
import logging
import os
import numpy as np
from datetime import datetime

from SPI import SPI
from INL import INL

class INLTest(unittest.TestCase):
    'Unit tests for INL.'

    def setUp(self):
        # setup this class for unit tests
        test = True
        spi = SPI(zdok = 0, test = test, roach = None)
        #adc = AdcSnapshot(zdok = zdok, test = test, roach = None)
    

        now =  datetime(2014, 4, 24, 9, 8, 38)
        self.adc = INL(dir = 'testdata'
                     , spi = spi
                     #, adc = adc
                     , now = now
                     , test = test)

        # Uncomment this code if you want the logs to stdout 
        #logging.config.fileConfig('adc5g_logging_config.conf')
        #logger = logging.getLogger('adc5gLogging')
        #logger.info("Started")

    def tearDown(self):

        # clean up all the generated files
        files = []
        basename = "%s/snapshot_raw_%s_z%d_%s.dat.%s" 
        exts = ["fit", "ogp", "a", "b", "c", "d", "res"]
        for zdok in [0,1]:
            for i in range(10):
                for ext in exts:
                    e = "%d.%s" % (i, ext) 
                    f = basename % (self.adc.dir, self.adc.roach_name, zdok, self.adc.current_time, e)
                    files.append(f)
        for f in files:
            if os.path.isfile(f):
                os.remove(f)        

    def test_get_inl_array(self):

        inls = self.adc.get_inl_array()

        # TBF: right now just getting zeros from simulated registers
        exp = np.zeros((5,17), dtype='float')
        exp[0] = range(0, 257, 16)
        exp = exp.transpose()
        for i in range(6):
            self.assertEqual(list(exp[i]), list(inls[i]))

    def test_do_inl(self):

        #logging.config.fileConfig('adc5g_logging_config.conf')
        #logger = logging.getLogger('adc5gLogging')
        #logger.info("Started")

        # TBF: while get_inl_array is returning zeros, then update_inl will simply
        # be adding zeros to what we get from the inl*.meas file.  so, the resulting
        # inl* file should be identical
        self.adc.do_inl(0)

        meas_inl = np.genfromtxt(self.adc.get_inl_meas_filename())
        final_inl = np.genfromtxt(self.adc.get_inl_filename())
 
        for i in range(17):
            self.assertEquals(list(meas_inl[i]), list(final_inl[i]))

    def test_load_from_file(self):

        self.adc.load_from_file('testdata/inl')

        exp = [('0x8f', '0x1'), ('0xb0', '0x20'), ('0xb1', '0x1400'), ('0xb2', '0x0'), ('0xb3', '0x19'), ('0xb4', '0x6140'), ('0xb5', '0xa000'), ('0x90', '0x2'), ('0x8f', '0x2'), ('0xb0', '0x4'), ('0xb1', '0x2'), ('0xb2', '0x0'), ('0xb3', '0x9'), ('0xb4', '0x6949'), ('0xb5', '0x8000'), ('0x90', '0x2'), ('0x8f', '0x3'), ('0xb0', '0x28'), ('0xb1', '0x5002'), ('0xb2', '0x0'), ('0xb3', '0x15'), ('0xb4', '0x559'), ('0xb5', '0x8000'), ('0x90', '0x2'), ('0x8f', '0x4'), ('0xb0', '0x0'), ('0xb1', '0x14a8'), ('0xb2', '0x0'), ('0xb3', '0x25'), ('0xb4', '0x4854'), ('0xb5', '0x0'), ('0x90', '0x2')]

        regs = [(hex(int(x)), hex(int(y))) for x, y in self.adc.spi.regs]
        self.assertEquals(exp, regs)

if __name__ == '__main__':
    unittest.main()
                
