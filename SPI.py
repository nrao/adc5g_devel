import numpy as np
from struct import pack, unpack
from math import floor

CONTROL_REG_ADDR = 0x01 + 0x80
CHANSEL_REG_ADDR = 0x0f + 0x80
EXTOFFS_REG_ADDR = 0x20 + 0x80
EXTGAIN_REG_ADDR = 0x22 + 0x80
EXTPHAS_REG_ADDR = 0x24 + 0x80
CALCTRL_REG_ADDR = 0x10 + 0x80
FIRST_EXTINL_REG_ADDR = 0x30 + 0x80

OPB_CONTROLLER = 'adc5g_controller'
OPB_DATA_FMT = '>H2B'

class SPI:

    """
    The Serial Peripheral Interface or SPI bus is a synchronous serial data link, a 
    de facto standard, named by Motorola, that operates in full duplex mode. It is 
    used for short distance, single master communication, for example in embedded 
    systems, sensors, and SD cards.

    This class is responsible for writing .... TBF
    """

    def __init__(self, zdok = 0, roach = None, test = False):


        if roach is None and not test:
            raise "If you aren't testing, you have to provide a roach to use."

        self.test = test
        self.roach = roach

        self.set_zdok(zdok)

        self.n_cores = 4
        self.cores = range(1,self.n_cores+1)

        # scales
        self.offset_scale = 100.
        self.gain_scale   = 36.
        self.phase_scale  = 28.
  
        # value to set for the CALCTRL_REG_ADDR
        self.offset_calctrl = 2<<2
        self.gain_calctrl   = 2<<4
        self.phase_calctrl  = 2<<6
  
        self.roach_original_control = {'0':None, '1':None}

        # for testing
        self.regs = []
        self.writes = []

    def set_zdok(self, zdok):
        assert zdok == 0 or zdok == 1
        self.zdok = zdok

    def get_zdok_offset(self):
        """
        The different zdok's must be written at different locations in the 
        Roach's register.
        """
        return 0x04 + (self.zdok*0x04)

    def set_offsets(self, values):
        assert (len(values) == self.n_cores)
        for i in range(self.n_cores):
            self.set_offset(self.cores[i], values[i])

    def set_gains(self, values):
        assert (len(values) == self.n_cores)
        for i in range(self.n_cores):
            self.set_gain(self.cores[i], values[i])

    def set_phases(self, values):
        assert (len(values) == self.n_cores)
        for i in range(self.n_cores):
            self.set_phase(self.cores[i], values[i])

    def scale_value(self, value, scale):
        return floor(0.5 + value*(255/scale)) + 0x80

    def unscale_value(self, value, scale):
        #return floor(0.5 + value*(255/scale)) + 0x80
        return (value - 0x80) * (scale/255)

    def set_spi_value(self, chn, value, scale, ext_reg_addr, calctrl_reg_addr):
        "Worker function for setting offset/gain/phase values to a channel on the ADC over SPI."
        reg_val = self.scale_value(value, scale)
        self.set_spi_register(CHANSEL_REG_ADDR, chn)
        self.set_spi_register(ext_reg_addr, reg_val)
        self.set_spi_register(CALCTRL_REG_ADDR, calctrl_reg_addr)

    def get_spi_value(self, chn, addr, scale):
        self.set_spi_register(CHANSEL_REG_ADDR, chn)
        reg_val = self.get_spi_register(addr-0x80)
        return self.unscale_value(reg_val, scale) 

    def get_offset(self, chn):
        return self.get_spi_value(chn, EXTOFFS_REG_ADDR, self.offset_scale)

    def get_gain(self, chn):
        return self.get_spi_value(chn, EXTGAIN_REG_ADDR, self.gain_scale)

    def get_phase(self, chn):
        return self.get_spi_value(chn, EXTPHAS_REG_ADDR, self.phase_scale)

    def set_offset(self, chn, offset):

        """
        Sets the offset value of one of the four channels on an ADC over SPI.
        The offset is a float ranging from -50 mV to +50 mV (with a resolution of 0.4 mV).
        """
        self.set_spi_value(chn, offset, self.offset_scale, EXTOFFS_REG_ADDR, self.offset_calctrl)

        #reg_val = self.scale_value(offset, self.offset_scale)
        #self.set_spi_register(CHANSEL_REG_ADDR, chn)
        #self.set_spi_register(EXTOFFS_REG_ADDR, reg_val)
        #self.set_spi_register(CALCTRL_REG_ADDR, 2<<2)

    def set_gain(self, chn, gain):

        """
        Sets the gain value of one of the four channels on an ADC over SPI.
        The gain is a float ranging from -18% to +18% (with a resolution of 0.14%).
        """
        self.set_spi_value(chn, gain, self.gain_scale, EXTGAIN_REG_ADDR, self.gain_calctrl)

    def set_phase(self, chn, phase):
        """
        Sets the phase value of one of the four channels on an ADC over SPI.
        The phase is a float ranging from -14 ps to +14 ps (with a resolution of 110 fs).       
        """
        self.set_spi_value(chn, phase, self.phase_scale, EXTPHAS_REG_ADDR, self.phase_calctrl)

    def set_spi_register(self, reg_addr, reg_val):
        """
        Sets the value of an ADC's register over SPI
        """
        #if self.test:
        # record what our values are
        self.regs.append((reg_addr, reg_val))

        spi_data = pack(OPB_DATA_FMT, reg_val, reg_addr, 0x01)

        zdok_offset = self.get_zdok_offset()

        self.blindwrite(spi_data, zdok_offset)

    def blindwrite(self, data, offset):

        # record what we do
        self.writes.append((offset, data))

        if not self.test:
            # actually send it to the roach
            self.roach.blindwrite(OPB_CONTROLLER, data, offset=offset)

    def get_spi_register(self, reg_addr):
        """
        Gets the value of an ADC's register over SPI
        """
        spi_data = pack(OPB_DATA_FMT, 0x0, reg_addr, 0x01)
        offset = self.get_zdok_offset()
        if not self.test:
            self.roach.blindwrite(OPB_CONTROLLER, spi_data, offset=offset) #0x4+self.zdok_n*0x4)
            raw = self.roach.read(OPB_CONTROLLER, 0x4, offset=offset) #0x4+zdok_n*0x4)
            reg_val, old_reg_addr, config_done = unpack(OPB_DATA_FMT, raw)
        else:
            reg_val = 1 # TBF?
            old_reg_addr = reg_addr
        if old_reg_addr is not reg_addr:
            raise ValueError("Could not read SPI register!")
        else:
            return reg_val

    def inl_values_to_reg_values(self, offs):
        level_to_bits = np.array([5,4,6,1,0,2,9,8,10])
    
        # create a array of 6 ints to hold the values for the registers
        regs = np.zeros((6), dtype='int32')
        r = 2	# r is the relative register number.  R = 2 for 0x32 and 0x35
        regbit = 8 #  regbit is the bit in the register
        for level in range(17):	# n is the bit number in the incoming bits aray
            n = int(floor(0.5 + offs[level]/0.15))
            if n > 4:
                n = 4
            if n < -4:
                n = -4
    	    i = level_to_bits[4-n]
            regs[r] |= ((i >>2) & 3) << regbit
            regs[r + 3] |= (i & 3)<< regbit
            if regbit == 14:
                r -= 1
                regbit = 0
            else:
                regbit += 2
        return regs

    def set_inl_registers(self, chan, offs):
        """
        Sets the Integral NonLinearity bits of one of the four channels on
        an ADC over SPI.
        
        The bits are packed into six 16-bit registers on the adc in a way
        that must make sense to the hardware designer. This subroutine takes
        its arguments in a way that is easier to explain
    
        The argument offs should be a list or array of 17 floats containing
        the fraction of an lsb to offset the adc's reference ladder at 0,
        16, ... 240, 255.  The possible offsets are 0, +-0.15, +-0.3, +-0.45
        and +-0.0.  The values given will be rounded to the nearest of these
        values and converted to the bits in the hardware registerd.
    
        See: http://www.e2v.com/e2v/assets/File/documents/broadband-data-converters/doc0846I.pdf,
         specifically section 8.7.19 through 8.8, for more details.
        """
        regs = self.inl_values_to_reg_values(offs)
        self.set_spi_register(CHANSEL_REG_ADDR, chan)
        for n in range(6):
    	    reg_val = float(regs[n])
            self.set_spi_register(FIRST_EXTINL_REG_ADDR+n, reg_val)
        self.set_spi_register(CALCTRL_REG_ADDR, 2)

    def get_inl_registers(self, chan):
        regs = np.zeros((6), dtype='int32')
        self.set_spi_register(CHANSEL_REG_ADDR, chan)
        for n in range(6):
            if not self.test:
                regs[n] = self.get_spi_register(FIRST_EXTINL_REG_ADDR-0x80+n)
        return self.inl_regs_to_inl_vals(regs)


    def inl_regs_to_inl_vals(self, regs):
        bits_to_off = np.array([0,1,-1,0,3,4,2,0,-3,-2,-4])
        offs = np.zeros((17), dtype = float)
        r = 2	# r is the relative register number.  R = 2 for 0x32 and 0x35
        regbit = 8	#  regbit is the bit in the register
        for level in range(17):	# n is the bit number in the incoming bits aray
            bits = 0xc & ((regs[r]>>regbit)<<2) | 3 & (regs[r+3]>>regbit)
    	    offs[level] = 0.15 * bits_to_off[bits]
    	    if regbit == 14:
    	        regbit = 0
    	        r -= 1
    	    else:
    	        regbit += 2
        return offs

    def set_control(self, adcmode=8, stdby=0, dmux=1, bg=1, bdw=3, fs=0, test=0):
        """
        Sets the control register of an ADC over SPI.
        
        Default mode is DMUX=1:1, gray-code, and channel A only.
        """
        reg_val = adcmode + (stdby<<4) + (dmux<<6) + (bg<<7) + (bdw<<8) + (fs<<10) + (test<<12)
        self.set_spi_register(CONTROL_REG_ADDR, reg_val)             

    def get_control(self):
        """
        Gets the current value of the control register of an ADC over SPI.
        """
        if not self.test:
            reg_val = self.get_spi_register(CONTROL_REG_ADDR-0x80)
        else: 
            reg_val = 0x3c8
        return {'adcmode' : reg_val & 0xf,
                'stdby'   : (reg_val>>4) & 0x3,
                'dmux'    : (reg_val>>6) & 0x1,
                'bg'      : (reg_val>>7) & 0x1,
                'bdw'     : (reg_val>>8) & 0x3,
                'fs'      : (reg_val>>10) & 0x1,
                'test'    : (reg_val>>12) & 0x1}

# *********** below are stuff that writes to OPB_CONTROLLER, but looks different then
# *********** the other SPI stuff.  How to categorize?

    def inc_mmcm_phase(self, inc=1):
        """
        This increments (or decrements) the MMCM clk-to-data phase relationship by 
        (1/56) * Pvco, where VCO is depends on the MMCM configuration.
    
        inc_mmcm_phase(roach, zdok_n)        # default increments
        inc_mmcm_phase(roach, zdok_n, inc=0) # set inc=0 to decrement
        """
        data = (1<<(self.zdok*4)) + (inc<<(1+self.zdok*4))
        reg_val = pack(OPB_DATA_FMT, data, 0x0, 0x0)
        self.blindwrite(reg_val, offset=0x0)        

    def sync_adc(self, zdok_0=True, zdok_1=True):
        """
        This sends an external SYNC pulse to the ADC. Set either zdok_0 or 
        zdok_1 to False to not sync those boards
    
        This should be used after setting test mode on.
        """
        self.blindwrite(pack('>BBBB', 0x00, 0x00, 0x00, 0x0), 0)
        self.blindwrite(pack('>BBBB', 0x00, 0x00, 0x00, zdok_0 + zdok_1*2), 0)
        self.blindwrite(pack('>BBBB', 0x00, 0x00, 0x00, 0x00), 0)            

    def set_test_mode(self, counter=True):
        if counter:
            self.use_counter_test()
        else:
            self.use_strobe_test()
        orig_control = self.get_control()
        if orig_control['test'] == 1:
            self.roach_original_control[str(self.zdok)] = orig_control    
            #raise Exception, "This ADC is already in test mode"
            print "This ADC is already in test mode"
            return

        #logger.debug( "current spi control: " + str(orig_control))
        # keep track of the original control
        # TBF: why?  set mem var instead?
        #if hasattr(self.roach, "adc5g_control"):
        #    roach.adc5g_control[zdok_n] = orig_control
        #else:
        #    roach.adc5g_control = {zdok_n: orig_control}
        self.roach_original_control[str(self.zdok)] = orig_control    
        new_control = orig_control.copy()
        new_control['test'] = 1
        self.set_control(**new_control)

    def unset_test_mode(self):
        try:
            #self.roach_original_control[str(self.zdok)]['test'] = 0
            self.set_control(**self.roach_original_control[str(self.zdok)])
        except AttributeError:
            raise Exception, "Please use set_test_mode before trying to unset"

    def set_not_test_mode(self):
        "Regardless of what was set before, make sure its no longer in test mode."
        current_control = self.get_control()
        cnt = current_control.copy()
        cnt["test"] = 0
        self.set_control(**cnt)

    def use_strobe_test(self):
        self.set_spi_register(0x05+0x80,1)

    def use_counter_test(self):
        self.set_spi_register(0x05+0x80,0)

    def get_hex_regs(self):
        "Its convinient to look at the address and values written in hex."
        return [(hex(int(x)), hex(int(y))) for x, y in self.regs]

    def get_int_roach_writes(self):
        "Its convinient to look at what we wrote to the roach as an unsigned int."
        return [unpack(">I", data) for offset, data in self.writes]

#    def get_adc_snapshot(self, snap_name = None, bitwidth=8, man_trig=True, wait_period=2):
#        """
#        Reads a one-channel snapshot off the given 
#        ROACH and returns the time-ordered samples.
#        """
#    
#        snap_name = "adcsnap%d" % self.zdok if snap_name is None else snap_name
#        print "snap: ", snap_name
#        grab = self.roach.snapshot_get(snap_name, man_trig=man_trig, wait_period=wait_period)
#        
#        data = unpack('%ib' %grab['length'], grab['data'])
#    
#        return list(d for d in data)        
