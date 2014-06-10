import ConfigParser 
import datetime

class ADCConfFile:

    """
    Responsible for reading and writing from the <roachname>-adc.conf
    files which hold our ADC Calibration info.
    """

    def __init__(self, filename = None):

        self.cp = ConfigParser.ConfigParser()

        self.general_sec = "GENERAL"
        self.mmcm_sec = "MMCM"
        self.mmcm_info = {}
        self.ogp_sec = "OGP"
        self.ogp_info = {}
        self.inl_sec = "INL"
        self.inl_info = []

        if filename is not None:
            self.read_file(filename)
 

    def read_file(self, filename):
        self.filename = filename
        r = self.cp.read(filename)
        if len(r)==0:
            raise Exception("Could not read file: %s" % filename)

        # TBF: convert all srtings from file to floats?
        self.read_mmcm_section()    
        self.read_ogp_section()    
        self.read_inl_section()    
    
    def read_mmcm_section(self):
        nentries = int(self.cp.get(self.mmcm_sec, "num_entries"))
        #logger.debug("Loading %d groups of entries in MMCM section." % nentries)
        info = []
        for i in range(nentries):
            opt = "mode[%d]" % i
            modes = self.cp.get(self.mmcm_sec,opt)
    
            opt = "boff[%d]" % i
            bof = self.cp.get(self.mmcm_sec,opt)
    
            opt = "freq[%d]" % i
            frq = self.cp.getfloat(self.mmcm_sec,opt)
    
            opt = "adc0[%d]" % i
            try:
                adc0 = self.cp.get(self.mmcm_sec,opt)
            except ValueError:
                adc0 = None # there are Nones in here
    
            opt = "adc1[%d]" % i
            try:
                adc1 = self.cp.get(self.mmcm_sec,opt)
            except ValueError:
                adc1 = None
    
            info.append((modes, bof, frq, adc0, adc1))
            tmsg = "Modes: %s, Freq: %s, Bof: %s, Adc0: %s, Adc1: %s" % (modes, frq, bof, adc0, adc1)
            #logger.debug(tmsg)
            self.mmcm_info[(bof, frq)] = (i, adc0, adc1, modes)
    
        return info

    def write_mmcms(self, bof, freq, zdok, mmcms):
        """
        Writes the given comma-separated mmcm values to the appropriate part
        of the config file.
        """
        # overload this for use with different types
        if str(type(mmcms)) == "<type 'int'>":
            mmcms = str(mmcms)
        elif str(type(mmcms)) == "<type 'list'>":
            mmcms = ",".join([str(m) for m in mmcms])

        mmcm_entry, _, _, _ = self.mmcm_info[(bof, freq)]
        opt = "adc%d[%d]" % (zdok, mmcm_entry)
        self.cp.set(self.mmcm_sec, opt, mmcms)

    def read_ogp_section(self):
        nentries = int(self.cp.get(self.ogp_sec, "num_entries"))
        #logger.debug("Loading %d groups of entries in MMCM section." % nentries)
        info = []
        for i in range(nentries):
            opt = "freq[%d]" % i
            frq = self.cp.getfloat(self.ogp_sec,opt)

            opt = "ogp0[%d]" % i
            ogp0 = self.cp.get(self.ogp_sec, opt)

            opt = "ogp1[%d]" % i
            ogp1 = self.cp.get(self.ogp_sec, opt)

            self.ogp_info[frq] = (i, ogp0, ogp1)

    def write_ogps(self, freq, zdok, values): 
        # overload this for use with different types
        ty = str(type(values))
        if ty in ["<type 'list'>", "<type 'tuple'>"]:
            values = ",".join(["%.4f" % o for o in values])

        i, _, _ = self.ogp_info[freq]
        opt = "ogp%d[%d]" % (zdok, i)
        self.cp.set(self.ogp_sec, opt, values)

    def read_inl_section(self):

        self.inl_info = []
        for zdok in range(2):
            self.inl_info.append([])
            for i in range(4):
                opt = "inl%d[%d]" % (zdok, i)
                inls = self.cp.get(self.inl_sec, opt)
                self.inl_info[zdok].append(inls)

    def write_inls(self, zdok, inls):
        assert len(inls) == 4
        for i, inl in enumerate(inls):
            self.write_core_inls(zdok, i, inl)

    def write_core_inls(self, zdok, core, values): 
        # overload this for use with different types
        ty = str(type(values))
        if ty == "<type 'numpy.ndarray'>":
            values = list(values)
            ty = str(type(values))
        if ty in ["<type 'list'>", "<type 'tuple'>"]:
            values = ",".join(["%.5f" % o for o in values])

        opt = "inl%d[%d]" % (zdok, core)
        self.cp.set(self.inl_sec, opt, values)

    def write_to_file(self):
        self.cp.set(self.general_sec, "last_updated", datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"))
        with open(self.filename, 'wb') as configfile:
            self.cp.write(configfile) 



if __name__ == "__main__":

    cf = ADCConfFile("test.conf")
    print cf.mmcm_info
    print cf.ogp_info
    print cf.inl_info
    #cf.write_mmcms('h16k_ver109_2013_Nov_27_1633.bof', 1000*1e6, 0, [2,4])
    #cf.write_ogps(1000*1e6, 0, range(4))
    #cf.write_inls(0, [range(3), range(4,8), range(8,12), range(12,16)])
    #cf.write_to_file()
