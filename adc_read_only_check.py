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
from ADCCalibrate import ADCCalibrate

# This is another entry point for ADCalibrate, where we only produce
# plots of the ADC output.

def main():

    p = OptionParser()
    
    p.set_usage('%prog [options]')
    p.set_description(__doc__)
    p.add_option('-v', '--verbosity', dest='verbosity',type='int', default=1,
        help='Verbosity level. Default: 1')
    p.add_option('-r', '--roach', dest='roach',type='str', default='srbsr2-1',
        help='ROACH IP address or hostname. Default: srbsr2-1')
    p.add_option('-z', '--zdok', dest='zdok', type='int', default=2,
        help='ZDOK, 0 or 1, if input is 2, then refers to both. Default = 2')
    p.add_option('-d', '--directory', dest='dir', type='str', default='.',    
        help='name of directory to put all files')
    p.add_option('-o', '--read_ogp', dest='read_ogp', action='store_true', default=False,
        help='Read the OGP values from the hardware') 
    p.add_option('-i', '--read_inl', dest='read_inl', action='store_true', default=False,
        help='Read the INL values from the hardware') 
    opts, args = p.parse_args(sys.argv[1:])

    # setup log file name:
    current_time = datetime.datetime.now().strftime('%Y-%m%d-%H%M%S')
    timestamp = "_%s_z%d_%s"%(opts.roach, opts.zdok, current_time)
    AdcCalLoggingFileHandler.timestamp = timestamp

    # load log config file
    import os
    var = "YGOR_TELESCOPE"
    confdir = '.' if not os.environ.has_key(var) else  os.path.join(os.environ[var], "etc/config")
    conffile = "%s/%s" % (confdir, 'adc_cal_logging.conf')
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

    tmsg = 'Connecting to %s'%opts.roach
    logger.info(tmsg)
    r = corr.katcp_wrapper.FpgaClient(opts.roach)
    time.sleep(0.2)
    tmsg = 'ROACH is connected? ' +  str(r.is_connected())
    logger.info(tmsg)

    # Time to make our worker class
    cal = ADCCalibrate(dir = opts.dir 
                     , gpib_addr = None #opts.gpibaddr
                     , roach_name = opts.roach
                     , roach = r)

    zdoks = [opts.zdok] if opts.zdok != 2 else [0,1]

    # What are the currently loaded OGP values in the Card?
    chs = range(1,5)
    if opts.read_ogp:
        for z in zdoks:
            cal.set_zdok(z)
            os = [cal.spi.get_offset(c) for c in chs]
            gs = [cal.spi.get_gain(c)   for c in chs]
            ps = [cal.spi.get_phase(c)  for c in chs]
            logger.info("OGPs for zdok %s" % z)
            logger.info("Offsets: %s" % os)
            logger.info("Gains: %s" % gs)
            logger.info("Phases: %s" % ps)

    if opts.read_inl:
        for z in zdoks:
            cal.set_zdok(z)
            logger.info("INLs for zdok %s" % z)
            a = cal.inl.get_inl_array()
            logger.debug( "lvl  A     B     C     D")
            for level in range(17):
                logger.debug( "%3d %5.2f %5.2f %5.2f %5.2f" % tuple(a[level]))

    i = 0
    while cal.user_input("Check ADC output?"):
        fn = cal.get_check_filename("raw_%d" % i, opts.zdok)
        cal.check_raw(opts.zdok, filename = fn)
        fn = cal.get_check_filename("spec_%d" % i, opts.zdok)
        cal.check_spec(opts.zdok, filename = fn)
        i += 1



if __name__ == "__main__":
    main()
