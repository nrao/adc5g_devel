import logging
import logging.config
import logging.handlers
import corr
import time
import datetime
import sys
import os
from optparse import OptionParser

import AdcCalLoggingFileHandler
from ADCCalibrations import ADCCalibrations


def main():

    p = OptionParser()
    
    p.set_usage('%prog [options]')
    p.set_description(__doc__)
    p.add_option('-v', '--verbosity', dest='verbosity',type='int', default=1,
        help='Verbosity level. Default: 1')
    p.add_option('-r', '--roaches', dest='roaches',type='str', default='srbsr2-1',
        help='Comma-separated list of roach hostnames. Default: srbsr2-1')
    p.add_option('-M', '--n_mmcm_trials', dest='n_mmcm_trials',type='int', default=5,
        help='Number of mmcm trials. Default: 5')
    p.add_option('-N', '--n_trials', dest='n_trials',type='int', default=10,
        help='Number of snap/fit trials. Default: 10')
    p.add_option('-f', '--testfreq', dest='testfreq', type='float', default=18.3105,
        help='sine wave test frequency input in MHz. Default = 18.3105')
    p.add_option('-l', '--ampl', dest='ampl', type='float', default=3.0,
        help='Power level of test tone input in dBm. Default = 3.0')
    p.add_option('-g', '--gpibaddr', dest='gpibaddr', type='str', default='10.16.96.174',
        help='IP Address of the GPIB.  Current default is set to tape room machine. Default = 10.16.96.174')
    p.add_option('-d', '--data_dir', dest='data_dir', type='str', default='.',    
        help='name of directory to put all files')
    p.add_option('-c', '--conf_dir', dest='conf_dir', type='str', default='.',    
        help='name of directory where configuration files are found') 
    p.add_option('-m', '--manual', dest='manual', action='store_true', default=False,
        help='Manual control of the calibration process. Default=False')
    opts, args = p.parse_args(sys.argv[1:])

    # setup log file name:
    current_time = datetime.datetime.now().strftime('%Y-%m%d-%H%M%S')
    timestamp = "_all_%s"%current_time
    AdcCalLoggingFileHandler.timestamp = timestamp

    # load log config file
    if opts.conf_dir is not None:
        conf_dir = opts.conf_dir
    else:
        # if they haven't specified configuration directory, try to use env
        var = "YGOR_TELESCOPE"
        conf_dir = '.' if not os.environ.has_key(var) else  os.path.join(os.environ[var], "etc/config")
    conffile = "%s/%s" % (conf_dir, 'adc_cal_logging.conf')
    if not os.path.isfile(conffile):
        print "Cannot find config file for logging: %s" % conffile
        sys.exit(0)

    logging.config.fileConfig(conffile)
    logger = logging.getLogger('adc5gLogging')
    logger.info("Started")
    
    if not opts.verbosity:
        logger.setLevel(logging.INFO)

    logger.info("opts :\n\t" + str(opts))
    logger.info("args :\n\t" + str(args))
    logger.info("log file name:\n\t" + AdcCalLoggingFileHandler.logfilename)

    roaches = [s.strip() for s in opts.roaches.split(",")]
    # Time to make our worker class
    cal = ADCCalibrations(data_dir = opts.data_dir 
                     , conf_dir = conf_dir
                     , roaches = roaches
                     , gpib_addr = opts.gpibaddr
                     , mmcm_trials = opts.n_mmcm_trials 
                     , ogp_trials = opts.n_trials
                     , test_tone = opts.testfreq
                     , ampl = opts.ampl
                     , manual = opts.manual
                         )

     # and use it                    
    cal.find_all_calibrations()


if __name__ == "__main__":
    main()
