from struct import pack, unpack
from matplotlib.pyplot import *
import logging
import numpy as np
import time

from SPI import OPB_CONTROLLER


logger = logging.getLogger('adc5gLogging')

class MMCM:

    def __init__(self, zdok = 0, spi = None, adc = None,  test = False, file_label = None):

        self.adc = adc
        self.test = test
        self.spi = spi
        #self.file_label = file_label

        #self.roach_original_control = {'0':None, '1':None}

        self.set_zdok(zdok)

    def set_zdok(self, zdok):
        self.zdok = zdok
        self.snap_name = self.get_snap_name(zdok)
        self.spi.set_zdok(zdok)
        self.adc.set_zdok(zdok)

    def get_snap_name(self, zdok):
        return "adcsnap%d" % zdok

    def calibrate_mmcm_phase(self, bitwidth=8, man_trig=True, wait_period=2, ps_range=56, set_phase = True):
        """
        This function steps through all 56 steps of the MMCM clk-to-out 
        phase and finds total number of glitchss in the test vector ramp 
        per core. It then finds the least glitchy phase step and sets it.
        """

        snap_names = [self.snap_name] #["adcsnap%d" % self.zdok]
        self.spi.set_test_mode(counter=True)
        logger.debug("current spi control: " + str(self.spi.roach_original_control[str(self.zdok)]))
        self.spi.sync_adc()

        glitches_per_ps = []

        #start off by decrementing the mmcm right back to the beginning
        logger.debug("decrementing mmcm to start")
        for ps in range(ps_range):
            self.spi.inc_mmcm_phase(inc=0)

        # then step back up throught the phases counting glitches
        for ps in range(ps_range):
            glitches = self.get_total_glitches(snap_names, man_trig, wait_period, ps)
            glitches_per_ps.append(glitches)
            self.spi.inc_mmcm_phase()

        # now that you've gathered that data, use it to find
        # the optimal phase for the MMCM
        optimal_ps = self.find_optimal_phase(glitches_per_ps)
        if optimal_ps is not None and set_phase:
            # if you found something, set the hardware!
            # first, get back to the start
            for ps in range(ps_range):
                self.spi.inc_mmcm_phase(inc=0)
            # then step up to the optimal phase    
            for ps in range(optimal_ps):
                self.spi.inc_mmcm_phase()
            # now just double check that there's no glitches here    
            glitches = self.get_total_glitches(snap_names, man_trig, wait_period, ps)
            if glitches != 0:
                tmsg = "MMCM Optimal Phase of %d should not produce any glitches of %d" % (optimal_ps, glitches)
                logger.info(tmsg);
                raise Exception(tmsg)

        # get us back to our original mode
        self.spi.unset_test_mode()

        return optimal_ps, glitches_per_ps        

   
    def get_total_glitches(self, snap_names, man_trig, wait_period, iteration):

        cores = self.adc.get_test_vector(snap_names, man_trig=man_trig, wait_period=wait_period, iteration=iteration)
        return sum([self.count_glitches(core, 8) for core in cores]) 

    def count_glitches(self, core, bitwidth=8):
        "Counts number of times the expected result is not found in the ramp."
        ramp_max = 2**bitwidth - 1
        glitches = 0
        for i in range(len(core)-1):
            diff = core[i+1] - core[i]
            if (diff!=1) and (diff!=-ramp_max):
                glitches += 1
        return glitches        

    def find_optimal_phase_old(self, glitches_per_ps):    
        "Historical method: has bugs concerning edge cases"
        zero_glitches = [gl==0 for gl in glitches_per_ps]
        n_zero = 0
        longest_min = None
        while True:
            try:
                rising  = zero_glitches.index(True, n_zero)
                logger.debug("rising, nzero "+ str(rising) + " " + str(n_zero))
                n_zero  = rising + 1
                falling = zero_glitches.index(False, n_zero)
                logger.debug( "falling, nzero " + str(falling) + " " + str(n_zero))
                n_zero  = falling + 1
                min_len = falling - rising
                if min_len > longest_min:
                    longest_min = min_len
                    logger.debug( "  longest_min %d"%longest_min)
                    optimal_ps = rising + int((falling-rising)/2)
            except ValueError:
                break
        if longest_min==None:
            #raise ValueError("No optimal MMCM phase found!")
            return None #, glitches_per_ps
        else:
            #for ps in range(optimal_ps):
            #    self.spi.inc_mmcm_phase()
            return optimal_ps #, glitches_per_ps
        

    def find_optimal_phase(self, glitches_per_ps):

        optimal_phase = None

        # find where all the sequences of zero glitches are
        bs = [gl!=0 for gl in glitches_per_ps]
        sqs = self.find_false_sequences(bs)
        logger.debug("False sequences in glitches_per_ps: " + str(sqs))
        
        if len(sqs) == 0:
            # no where were there no glitches!
            return optimal_phase

        # now figure out which sequence is longest    
        sqLens = np.array([end - start for start, end in sqs])
        indx = np.where(sqLens == sqLens.max())
        if len(indx) > 0:
            # if there is more then one sequence of zero glitches
            # with the largest length, arbitrarily choose the first
            rgIndx = indx[0] if len(indx[0]) == 1 else indx[0][0]
            range = sqs[rgIndx]
            # choose the midpoint
            optimal_phase = range[0] + int((range[1] - range[0])/2) 
        return optimal_phase    
            

    def find_false_sequences(self, data): #, value=False):
        "Returns the indicies in given boolean array where value is false"
        # make sure of the data type
        data = np.array(data, dtype=bool)
        # Catch edge cases first
        if data.all():
            # they are ALL true - no sequence to return
            return []
        if np.array([not b for b in data], dtype=bool).all():
            # they are ALL false
            return [(0, len(data)-1)]
        # find where the switches occur
        sw = (data[:-1] ^ data[1:])
        # convert these to indicies
        isw = np.arange(len(sw))[sw]
        # now convert the list of indicies to a list of ranges
        n = 2
        sq = zip(*[isw[i::n] for i in range(n)])
        # add on the last one if necessary
        if len(isw) % 2 == 1:
            sq.append((isw[-1], len(data)-1))
        # adjust the ranges so that they don't mark transitions,
        # but *just* where the value is false
        sq = [(start+1, end) for start, end in sq]
        # Finally, does this represent where the values are True or False?
        if not data[0]:
            # We have a sequence fo where the values are True, so flip it.
            nsq = [(sq[i][1]+1, sq[i+1][0]-1) for i in range(len(sq)-1)]
            # take care of endpoints
            if sq[0][0] != 0:
                nsq.insert(0, (0,sq[0][0]-1))
            if sq[-1][1] != len(data)-1:
                nsq.append((sq[-1][1]+1, len(data)-1))
            sq = nsq
        return sq

                
if __name__ == "__main__":

    #myHandlers.timestamp = "_"

    import corr
    import time
    from SPI import SPI
    from AdcSnapshot import AdcSnapshot

    #logging.config.fileConfig('adc5g_logging_config.conf')
    #logger = logging.getLogger('adc5gLogging')
    #logger.info("Started")

    roach_name = "srbsr2-1"
    roach = corr.katcp_wrapper.FpgaClient(roach_name)
    time.sleep(3)
    print "connected: ", roach.is_connected()
    #bof = 'h1k_ver105_2013_Dec_02_1551.bof'
    #roach.progdev(bof)
    #time.sleep(5)

    test = False

    spi = SPI(roach = roach, test = test)
    adc = AdcSnapshot(roach = roach, test = test)

    mmcm = MMCM(spi = spi, adc = adc, test = test)

    mmcm.calibrate_mmcm_phase()

       
