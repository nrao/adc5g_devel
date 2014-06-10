import unittest
import logging
import os
import numpy as np
from datetime import datetime

from ADCCalibrations import ADCCalibrations

class ADCCalibrationsTest(unittest.TestCase):
    'Unit tests for .'

    def setUp(self):
        # setup this class for unit tests
        now =  datetime(2014, 4, 24, 9, 8, 38)
        self.adc = ADCCalibrations(dir = 'testdata'
                                 , test = True
                                 , mmcm_trials = 1
                                 , roaches = ['noroach']
                                 , now = now
                                  )
        





        # Uncomment this code if you want the logs to stdout 
        #logging.config.fileConfig('adc5g_logging_config.conf')
        #logger = logging.getLogger('adc5gLogging')
        #logger.info("Started")

    # TBF: need to do this still?
    #def tearDown(self):

        # clean up all the generated files
        #files = []
        #basename = "%s/snapshot_raw_%s_z%d_%s.dat.%s" 
        #exts = ["fit", "ogp", "a", "b", "c", "d", "res"]
        #for zdok in [0,1]:
        #    for i in range(10):
        #        for ext in exts:
        #            e = "%d.%s" % (i, ext) 
        #            f = basename % (self.adc.dir, self.adc.roach_name, zdok, self.adc.current_time, e)
        #            files.append(f)
        #for f in files:
        #    if os.path.isfile(f):
        #        os.remove(f)

        # clean up .png's
        #fs = os.listdir(self.adc.dir)

    def test_find_all_mmcms(self):

        self.adc.find_all_mmcms()
