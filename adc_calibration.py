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
from valon_katcp import ValonKATCP

# This is the entry point for ADCalibrate, which calibrates the
# ADC cards in the Vegas Roach boards.
# The primary responsiblity of this script is to translate the various
# command line options into how to interact with ADCCalibrate, as well
# as the calling order.

def main():

    p = OptionParser()
    
    p.set_usage('%prog [options]')
    p.set_description(__doc__)
    p.add_option('-p', '--skip_prog', dest='prog_fpga',action='store_false', default=True,
        help='Skip FPGA programming (assumes already programmed).  Default: program the FPGAs')
    p.add_option('-v', '--verbosity', dest='verbosity',type='int', default=1,
        help='Verbosity level. Default: 1')
    p.add_option('-r', '--roach', dest='roach',type='str', default='srbsr2-1',
        help='ROACH IP address or hostname. Default: srbsr2-1')
    p.add_option('-b', '--boffile', dest='boffile',type='str', default='h1k_ver105_2013_Dec_02_1551.bof',
        help='Boffile to program. Default: h1k_ver105_2013_Dec_02_1551.bof')
    p.add_option('-N', '--n_trials', dest='n_trials',type='int', default=10,
        help='Number of snap/fit trials. Default: 10')
    p.add_option('-c', '--clockrate', dest='clockrate', type='float', default=1500.0,
        help='Clock rate in MHz, for use when plotting frequency axes. If none is given, rate will be estimated from FPGA clock')
    p.add_option('-f', '--testfreq', dest='testfreq', type='float', default=18.3105,
        help='sine wave test frequency input in MHz. Default = 18.3105')
    p.add_option('-l', '--ampl', dest='ampl', type='float', default=3.0,
        help='Power level of test tone input in dBm. Default = 3.0')
    p.add_option('-g', '--gpibaddr', dest='gpibaddr', type='str', default='10.16.96.174',
        help='IP Address of the GPIB.  Current default is set to tape room machine. Default = 10.16.96.174')
    p.add_option('-s', '--snapname', dest='snapname', type='str', default='adcsnap',
        help='snapname. Default = adcsnap')
    p.add_option('-z', '--zdok', dest='zdok', type='int', default=2,
        help='ZDOK, 0 or 1, if input is 2, then refers to both. Default = 2')
    p.add_option('-d', '--directory', dest='dir', type='str', default='.',    
        help='name of directory to put all files')
    p.add_option('-o', '--ogp', dest='do_ogp', type='int', default=1,
        help='Do OGP calibration? Default = 1')
    p.add_option('-i', '--inl', dest='do_inl', type='int', default=1,
        help='Do INL calibration (OGP must be completed first)? Default = 1')
    p.add_option('-t', '--test', dest='test', type='int', default=1,
        help='Test after calibration is completed. Default=1')
    p.add_option('-m', '--manual', dest='manual', type='int', default=1,
        help='Manual control of the calibration process. Default=1')
    p.add_option('-S', '--save', dest='save', type='int', default=1,
        help='To save the plots. Default=1 (save)')
    p.add_option('-V', '--view', dest='view', type='int', default=1,
        help='To show the plots interactively (will be forced to 0 if manual is off). Default=1 (show)')
    p.add_option('-u', '--update_conf', dest='update_conf', action='store_false', default=True,
        help='Update the <roach_name>-adc.conf file?')

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

    tmsg = 'Estimating clock speed...'
    logger.info(tmsg)
    clk_est = r.est_brd_clk()
    tmsg = 'Clock estimated speed is %d MHz'%clk_est
    logger.info(tmsg)

    if opts.clockrate is None:
        clkrate = clk_est*16
        print "SETTING clkrate to: ", clkrate
    else:
        clkrate = opts.clockrate

    # Before progressing furth, check that the Valon Synth
    # is actually set to the clkrate.
    # ValonKATCP is not a worker class belonging to ADCCalibrate
    # since ADCCalibrate is inherited code, while Valon is ours.
    valonSerial = "/dev/ttyS1" # this should never change
    valonSynth = 0 # neither should this (0: A, 8: B)
    v = ValonKATCP(r, valonSerial) 
    current_clkrate = v.get_frequency(valonSynth)
    tmsg = "Valon Synth set to frequency: %f MHz" % current_clkrate
    logger.info(tmsg)
    if abs(current_clkrate - clkrate) > 0.001:
        v.set_frequency(valonSynth, clkrate)
        time.sleep(1)
        current_clkrate = v.get_frequency(valonSynth)
        tmsg = "Valon Synth changed to frequency: %f MHz" % current_clkrate
        logger.info(tmsg)

    # Time to make our worker class
    cal = ADCCalibrate(dir = opts.dir 
                     , roach_name = opts.roach
                     , gpib_addr = opts.gpibaddr
                     , clockrate = clkrate
                     , bof = opts.boffile
                     , config = opts.update_conf
                     , roach = r)

    #
    cal.ogp.set_zdok(0)
    fn = "old_ogps/vegasr2-4/ogp0_vegasr2-4_z2_2014-0424-085259"
    cal.ogp.load_from_file(fn)
    cal.ogp.set_zdok(1)
    fn = "old_ogps/vegasr2-4/ogp1_vegasr2-4_z2_2014-0424-085259"
    cal.ogp.load_from_file(fn)
    print 'done'
    return

    cal.set_freq(opts.testfreq)
    cal.set_ampl(opts.ampl)

    if opts.prog_fpga:
        tmsg = 'Calibrating ADCs (MMCM)'
        logger.info(tmsg)
        cal.do_mmcm(opts.zdok)
        if opts.manual:
            if cal.user_input("Check the test ramps now?"):
                cal.check_ramp(opts.zdok, save=opts.save, view=opts.view) #, filename = fn)


    if opts.do_ogp or opts.test:
        if  cal.gpib_test(opts.zdok, opts.testfreq, opts.ampl, manual=opts.manual): 
            tmsg = 'Current test tone power level: %.4f'%opts.ampl
            logger.debug(tmsg)
            tmsg ='Current test tone frequency: %.4f'%opts.testfreq
            logger.debug(tmsg)
            cal.check_raw(opts.zdok, save=opts.save, view=(opts.manual and opts.view))
            if opts.manual:
                if cal.user_input("Adjust power level now?"):
                    cal.ampl_setup(opts.zdok, manual = True)
        else:
            tmsg = "Problem with synthesizer, aborting OGP calibration & testing..."
            logger.warning(tmsg)
            opts.do_ogp = 0
            opts.test = 0


    if opts.do_ogp:
        cal.do_ogp(opts.zdok, opts.testfreq, opts.n_trials)
        if opts.do_inl:
            cal.do_inl(opts.zdok) 

    if opts.test:
        if opts.manual:
            logger.info("Startinging manual testing...")
            check_spec = cal.user_input("Check spectrum?")
            while(check_spec):
                cal.freq_setup(opts.zdok, manual=True)
                cal.ampl_setup(opts.zdok, manual=True)
                fn = cal.get_check_filename("post_adjustment_test_%.4fMHz" % cal.gpib.freq, opts.zdok) 
                cal.check_spec(opts.zdok, save=opts.save, view=opts.view, filename=fn) #, filename=fn)
                check_spec = cal.user_input("Check spectrum?")
            if cal.user_input("Do frequency scan?"):
                cal.freq_scan(save=opts.save, view=opts.view) #, filename=fn)
        else:
            logger.info("Starting automatic testing...")
            for i in range(0, 5):
                test_freq = random.random()*cal.clockrate
                cal.freq_setup(manual=False, freq = test_freq)
                fn = "post_adjustment_test_%.4fMHz"%cal.gpib.freq + cal.file_label
                cal.check_spec(save=opts.save, view=False, filename=fn)
            fn = 'freq_scan' + cal.file_label #timestamp
            cal.freq_scan(save=opts.save, view=False, filename=fn)

if __name__ == "__main__":
    main()
