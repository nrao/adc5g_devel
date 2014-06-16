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

# This is another entry point for ADCalibrate, where we specify how
# to load in the calibration results (ogp, inl) for the ADC Cards.
# This primary responsibility of this script is to translate the various
# command line options into how to interact with ADCCalibrate.

def main():

    p = OptionParser()
    
    p.set_usage('%prog [options]')
    p.set_description(__doc__)
    p.add_option('-v', '--verbosity', dest='verbosity',type='int', default=1,
        help='Verbosity level. Default: 1')
    p.add_option('-p', '--skip_prog', dest='prog_fpga',action='store_false', default=True,
        help='Skip FPGA programming (assumes already programmed).  Default: program the FPGAs')     
    p.add_option('-r', '--roach', dest='roach',type='str', default='srbsr2-1',
        help='ROACH IP address or hostname. Default: srbsr2-1')
    p.add_option('-z', '--zdok', dest='zdok', type='int', default=2,
        help='ZDOK, 0 or 1, if input is 2, then refers to both. Default = 2')
    p.add_option('-t', '--types', dest='types', type='str', default='all',
        help='Which type of calibrations to load: [all, ogp, inl]')
    p.add_option('-l', '--caldir', dest='caldir', type='str', default=None,
        help='What directory to find the calibration files in')
    p.add_option('-f', '--file', dest='file', type='str', default=None,
        help='What specific file to use? -type & -zdok options must be used as well')
    p.add_option('-b', '--boffile', dest='boffile',type='str', default='h1k_ver105_2013_Dec_02_1551.bof',
        help='Boffile to program. Default: h1k_ver105_2013_Dec_02_1551.bof')
    p.add_option('-g', '--gpibaddr', dest='gpibaddr', type='str', default='10.16.96.174',
        help='IP Address of the GPIB.  Current default is set to tape room machine. Default = 10.16.96.174')
    p.add_option('-d', '--directory', dest='dir', type='str', default='.',    
        help='name of directory to put all files')
    p.add_option('-u', '--use_conifg', dest='use_conifg', action='store_true', default=False,
        help='Load calibrations found in <roachname>-adc.conf file?')
    p.add_option('-c', '--clockrate', dest='clockrate', type='float', default=1500.0,
        help='Clock rate in MHz; must be specified if --use_config option is specified')

    opts, args = p.parse_args(sys.argv[1:])

    # setup log file name:
    current_time = datetime.datetime.now().strftime('%Y-%m%d-%H%M%S')
    timestamp = "_%s_z%d_%s"%(opts.roach, opts.zdok, current_time)
    AdcCalLoggingFileHandler.timestamp = timestamp

    # load log config file
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

    if opts.prog_fpga:
        tmsg = 'Programming ROACH with boffile %s'%opts.boffile
        r.progdev(opts.boffile)
        time.sleep(0.5)
        logger.info(tmsg)   

    # Time to make our worker class
    cal = ADCCalibrate(dir = opts.dir 
                     , gpib_addr = opts.gpibaddr
                     , roach_name = opts.roach
                     , roach = r)

    # First, check out the noise before we load
    logger.info("Checking initial state of spectrum.")
    fn = cal.get_check_filename("inital_spec", opts.zdok)
    cal.check_spec(opts.zdok, filename = fn)
        

    # TBF: we have to do this, or some subset, after the roach has
    # has been rebooted.  WHY?
    if opts.prog_fpga:
        cal.do_mmcm(opts.zdok)

    logger.info("Checking of spectrum after MMCM calibration.")
    fn = cal.get_check_filename("after_mmcm_spec", opts.zdok)
    cal.check_spec(opts.zdok, filename = fn)

    if opts.types == 'all':
        types = None
    else:
        types = [opts.types]

    if opts.file is not None:
        if opts.types is 'all':
            raise Exception, "Must specify --types when specifiying --file"
        if opts.zdok == 2:
            raise Exception, "Must specify --zdok as 0 or 1 when specifiying --file"
        if opts.types == 'ogp':
            cal.ogp.load_from_file(opts.file)
            logger.info("Loading calibration file %s" % opts.file)
        elif opts.types == 'inl':
            cal.inl.load_from_file(opts.file)
            logger.info("Loading calibration file %s" % opts.file)
        else:
            msg = "--type value unsupported (all, ogp, inl): ", opts.types
            logger.debug(msg)
            raise Exception, msg 
    else:
        cal.load_calibrations(indir = opts.caldir
                            , use_conf = opts.use_conf
                            , freq = opts.clockrate
                            , zdoks = opts.zdok
                            , types = types)

    # Finally, check out the noise
    logger.info("Checking final state of spectrum.")
    fn = cal.get_check_filename("after_load_cals_spec", opts.zdok)
    cal.check_spec(opts.zdok, filename = fn)

if __name__ == "__main__":
    main()
