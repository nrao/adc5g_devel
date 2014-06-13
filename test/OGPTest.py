
import unittest
import logging
import os
import numpy as np
from datetime import datetime

from SPI import SPI
from OGP import OGP

class OGPTest(unittest.TestCase):
    'Unit tests for OGP.'

    def setUp(self):
        # setup this class for unit tests
        test = True
        spi = SPI(zdok = 0, test = test, roach = None)
        #adc = AdcSnapshot(zdok = zdok, test = test, roach = None)
    

        now =  datetime(2014, 4, 24, 9, 8, 38)
        self.adc = OGP(dir = 'testdata'
                     , spi = spi
                     #, adc = adc
                     , now = now
                     , clockrate = 1500.
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

        
    def test_do_ogp(self):

        # do both zdoks
        self.adc.do_ogp(0)  
        self.adc.do_ogp(1)  

        # read the results generated from the files
        fns = ['testdata/ogp_noroach_z%d_2014-04-24-090838' % i for i in range(2)]
        ogps = [np.genfromtxt(fn) for fn in fns]

        # expected OGP results for each zdok
        ogp0 = np.array([ 0.3204,  1.5172, -5.4003,  5.6399, -1.2363, -4.3599,  0.0187,
        0.573 ,  4.1971,  4.0154, -0.8539,  5.5631])
        ogp1 = np.array([-2.9787, -1.0081, -2.6508, -2.0572, -0.1586, -2.541 , -1.2939,
        0.4856,  1.7727,  4.8329,  0.6811,  3.4191])

        self.assertEquals(list(ogp0),list(ogps[0])) 
        self.assertEquals(list(ogp1),list(ogps[1])) 

        # make sure gpib got commands properly
        #exp = [':OUTP:STAT ON\r'
        #     , ':FREQ:CW 18.3105E6\r'
        #     , ':FREQ:CW 18.3105E6\r']
        #self.assertEquals(exp, self.adc.gpib.cmds)     

    def test_do_snap(self):

        # This is the base filename that will be used as input: each iteration
        # will use this name + '.i'
        fname = 'testdata/snapshot_raw_noroach_z0_2014-04-24-090838.dat'
        freq = 18.3105
        repeat = 10
        ogp, _ = self.adc.do_snap(freq = freq, fname = fname, repeat = repeat) 
        exp = (18.310500000000001, 2.4986150065254478, 104.76788603357048, 0.32043225809828751, 1.517175579119834, -5.4003278273111848, 5.6399198917743325, -1.2362778942176573, -4.3598573041576856, 0.018731282665579486, 0.57301410206433001, 4.1970603858473625, 4.0153765935635928, -0.85391178696651227, 5.5631247456218258)
        self.assertEquals(ogp, exp)                         

    def test_load_from_file(self):

        file = 'testdata/ogp'
        self.adc.load_from_file(file, zdok = 0)
        exp = [('0x81', '0x3c8'), ('0x8f', '0x1'), ('0xa0', '0x7a'), ('0x90', '0x8'), ('0x8f', '0x2'), ('0xa0', '0x73'), ('0x90', '0x8'), ('0x8f', '0x3'), ('0xa0', '0x6f'), ('0x90', '0x8'), ('0x8f', '0x4'), ('0xa0', '0x79'), ('0x90', '0x8'), ('0x8f', '0x1'), ('0xa2', '0x6d'), ('0x90', '0x20'), ('0x8f', '0x2'), ('0xa2', '0x84'), ('0x90', '0x20'), ('0x8f', '0x3'), ('0xa2', '0x84'), ('0x90', '0x20'), ('0x8f', '0x4'), ('0xa2', '0x8b'), ('0x90', '0x20'), ('0x8f', '0x1'), ('0xa4', '0x4a'), ('0x90', '0x80'), ('0x8f', '0x2'), ('0xa4', '0x45'), ('0x90', '0x80'), ('0x8f', '0x3'), ('0xa4', '0xb6'), ('0x90', '0x80'), ('0x8f', '0x4'), ('0xa4', '0xbb'), ('0x90', '0x80')]
        regs = [(hex(int(x)), hex(int(y))) for x, y in self.adc.spi.regs]
        self.assertEquals(exp, regs)
