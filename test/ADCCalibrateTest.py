import unittest
import logging
import os
import numpy as np
from datetime import datetime

from ADCCalibrate import ADCCalibrate

class ADCCalibrateTest(unittest.TestCase):
    'Unit tests for .'

    def setUp(self):
        # setup this class for unit tests
        now =  datetime(2014, 4, 24, 9, 8, 38)
        self.adc = ADCCalibrate(dir = 'testdata'
                              , now = now
                              , test = True)

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

        # clean up .png's
        fs = os.listdir(self.adc.dir)
        
    def test_load_calibrations(self):

        indir = 'testdata'
        self.adc.load_calibrations(indir = indir) 

        # did we load the right files?
        exp = ["%s/ogp_noroach_z%d_2014-04-24-090838" % (indir, i) for i in range(2)]
        exp.extend(["%s/inl_noroach_z%d_2014-04-24-090838.meas" % (indir, i) for i in range(2)])
        self.assertEquals(exp, self.adc.loaded_files)

        # probe the lower level objects to make sure commands were sent
        self.assertEqual(138, len(self.adc.spi.regs))

        # test filters
        self.adc.load_calibrations(indir = indir, zdoks = 1, types = ['ogp'])
        exp = ["%s/ogp_noroach_z%d_2014-04-24-090838" % (indir, 1)]
        self.assertEquals(exp, self.adc.loaded_files)

    # *************** The below tests are using dummy input data, so checking their
    # results is of limited value.  Here we basically make sure theres failures.

    def test_check_ramp(self):

        # setup
        zdok = 0
        fn1 = self.adc.get_check_filename(self.adc.post_mmcm_ramp_check_name, zdok) + ".png"
        fn2 = self.adc.get_check_filename(self.adc.post_ramp_check_raw_name, zdok) + ".png"
        for f in [fn1, fn2]:
            if os.path.isfile(f):
                os.remove(f)

        self.adc.check_ramp(zdok, save=True, view = False)

        # test & cleanup
        for f in [fn1, fn2]:
            self.assertTrue(os.path.isfile(f))
            if os.path.isfile(f):
                os.remove(f)

    def test_check_raw(self):

        # setup
        zdok = 0
        fn = self.adc.get_check_filename(self.adc.raw_startup_name, zdok) + ".png"
        if os.path.isfile(fn):
            os.remove(fn)

        self.adc.check_raw(zdok, save=True, view = False)

        self.assertTrue(os.path.isfile(fn))
        if os.path.isfile(fn):
            os.remove(fn)
        
    # skipping this for now ...    
    def skip_test_check_spec(self):

        # setup
        zdok = 0
        fn = self.adc.get_check_filename("spec", zdok) + ".png"
        if os.path.isfile(fn):
            os.remove(fn)

        self.adc.gpib.set_freq(1.0)
        self.adc.gpib.set_ampl(1.0)

        # not saving because the FFT causes NaN's, which the figure has 
        # problems with
        self.adc.check_spec(zdok, save=False, view = False)

        self.assertTrue(not os.path.isfile(fn))
        if os.path.isfile(fn):
            os.remove(fn)

if __name__ == '__main__':
    unittest.main()

