
import unittest
import logging
import os
import numpy as np
from datetime import datetime

from SPI import SPI
from AdcSnapshot import AdcSnapshot
from MMCM import MMCM

class MMCMTest(unittest.TestCase):
    'Unit tests for MMCM.'

    def setUp(self):
        # setup this class for unit tests
        test = True
        spi = SPI(zdok = 0, test = test, roach = None)
        adc = AdcSnapshot(zdok = 0, test = test, roach = None)
    

        now =  datetime(2014, 4, 24, 9, 8, 38)
        self.mmcm = MMCM(#dir = 'testdata'
                      spi = spi
                     , adc = adc
                     #, now = now
                     , test = test)

        # Uncomment this code if you want the logs to stdout 
        #logging.config.fileConfig('adc5g_logging_config.conf')
        #logger = logging.getLogger('adc5gLogging')
        #logger.info("Started")

    def tearDown(self):
        return
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

    def test_increment_mmcm_phase(self):

        # based off collected data from real snapshots
        op, gl = self.mmcm.calibrate_mmcm_phase()
        self.assertEquals(36, op)
        expGl = [2046, 2146, 2494, 3242, 4466, 6128, 6525, 8774, 9511, 8333, 7926, 7382, 5114, 3467, 1529, 291, 4]
        expGl.extend([0]*39)
        self.assertEquals(expGl, gl)

    def test_count_glitches(self):

        phases = [(0,0), (26, 2472)]
        for ph, exp in phases:
            # test data generated from real snapshots
            fn = "test_core_a_%d" % ph
            core_a = np.genfromtxt(fn) 
            core_a = [int(i) for i in core_a]
            glitches = self.mmcm.count_glitches(core_a)
            self.assertEquals(exp, glitches)

    def test_find_optimal_phase(self):

        # from actual results
        d1 = (19, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 364, 916, 1459, 2009, 2047, 2149, 2381, 3299, 4507, 2154, 3038, 5962, 7187, 8410, 9426, 9938])
        d2 =  (43, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 54, 2034, 2048, 2050, 2628, 4506, 6163, 8226, 9388, 9246, 10311, 10108, 8066, 4978, 2710, 276, 150, 22, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]) # old bug had ph as 6
        # contrived results
        d3 = (None, [100]*56)
        d4 = ((56/2)-1, [0]*56)
        # really contrived.
        d5 = []
        for i in range(2):
           d5.extend([0]*10)
           d5.extend([1]*10);
        d5.extend([0]*10)    
        d5.extend([1]*6)    
        d5 = (4, d5)
        data = [d1, d2, d3, d4, d5 ]
        for expopt, glitches in data:
            opt = self.mmcm.find_optimal_phase(glitches)
            self.assertEqual(expopt, opt)

    def test_find_false_sequences(self):

        # generic cases
        seq = [(0, 2), (6, 8), (13, 14)]
        data = [0,0,0,1,1,1,0,0,0,1,1,1,1,0,0]

        sq = self.mmcm.find_false_sequences(data)
        self.assertEquals(seq, sq)

        fseq = [(3, 5), (9, 12)]
        fdata = [not b for b in data]

        sq = self.mmcm.find_false_sequences(fdata)
        self.assertEquals(fseq, sq)

        seq = [(0, 9), (20, 29), (40, 49)]
        d5 = []
        for i in range(2):
           d5.extend([0]*10)
           d5.extend([1]*10);
        d5.extend([0]*10)    
        d5.extend([1]*6)    
        self.assertEquals(seq, self.mmcm.find_false_sequences(d5))

        # kind of edge case
        seq = [(3,5)]
        data = [1,1,1,0,0,0]
        self.assertEquals(seq, self.mmcm.find_false_sequences(data))
        seq = [(0,2)]
        data = [0,0,0,1,1,1]
        self.assertEquals(seq, self.mmcm.find_false_sequences(data))


        # edge cases: 
        seq = [(1, 3), (5, 7)]
        data = [1,0,0,0,1,0,0,0,1]

        sq = self.mmcm.find_false_sequences(data)
        self.assertEquals(seq, sq)

        fseq = [(0, 0), (4, 4), (8, 8)]
        fdata = [not b for b in data]

        sq = self.mmcm.find_false_sequences(fdata)
        self.assertEquals(fseq, sq)

        # super edge cases
        self.assertEquals([(0,14)], self.mmcm.find_false_sequences([False]*15))
        self.assertEquals([], self.mmcm.find_false_sequences([True]*15))
