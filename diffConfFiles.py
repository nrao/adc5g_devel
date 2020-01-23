import sys
import os
import matplotlib.pylab as plt
import numpy as np
import ConfigParser

"""
This module is for producing plots of the differences between
the OGP values in one vegasr2-adc-*.conf file and another.
"""

def toFloat(values):
    " '1.2, 2.2' -> [1.1, 2.2]"
    vs = values.split(',')
    return [float(v.strip()) for v in vs]

def getConfFileValues(file):

    assert os.path.isfile(file)

    cp = ConfigParser.ConfigParser()

    r = cp.read(file)
    if len(r)==0:
        raise Exception("Could not read file: %s" % fn)

    ogps = {}
    sec = "OGP"
    nentries = int(cp.get(sec, "num_entries"))
    print("Loading %d groups of entries in OGP section." % nentries)
    for i in range(nentries):
        opt = "freq[%d]" % i
        freq = cp.get(sec,opt)
        opt = "ogp0[%d]" % i
        ogp0s = cp.get(sec,opt)
        opt = "ogp1[%d]" % i
        ogp1s = cp.get(sec,opt)

        print(i)
        print(freq)
        print(ogp0s)
        print(ogp1s)

        ogps[freq] = {'opg0': toFloat(ogp0s), 'opg1': toFloat(ogp1s)}

    return ogps    

def diffConfFiles(file1, file2):

    v1 = getConfFileValues(file1)
    v2 = getConfFileValues(file2)

    assert sorted(v1.keys()) == sorted(v2.keys())

    fn1 = os.path.basename(file1)
    fn2 = os.path.basename(file2)
    fn = fn1 if fn1 == fn2 else None

    for freq in sorted(v1.keys()):
        plotOGPFreq(freq, v1[freq], v2[freq], filename=fn)
    
def plotOGPFreq(freq, ogps1, ogps2, filename=None):

    keys = ['opg0', 'opg1']

    for k in keys:
        v1 = ogps1[k]
        v2 = ogps2[k]
        assert len(v1) == len(v2)
        f = plt.figure()
        ax = f.gca()
        xaxis = np.array(range(len(v1)))
        ax.plot(xaxis, np.array(v1), xaxis, np.array(v2))
        ifreq = int(float(freq))/1e6
        if filename is not None:
            title = "%s_%d_%s" % (filename, ifreq, k)
        else:    
            title = "%d_%s" % (ifreq, k)
        plt.title(title)
        #plt.show()
        figFile = title.replace(".", "_")
        #figFile="test.png"
        plt.savefig(figFile)

def main():

    if len(sys.argv) < 3:
        print("Usage: diffConfFiles file1 file2")
        sys.exit(1)

    file1 = sys.argv[1]
    file2 = sys.argv[2]

    diffConfFiles(file1, file2)

if __name__ == '__main__':
    main()
