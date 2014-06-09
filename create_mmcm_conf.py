import ConfigParser
cp = ConfigParser.ConfigParser()
fn = "/home/gbt/etc/config/vegas.conf"

cp.read(fn)

#info = []
info = {}
modes = range(1,31)
for m in modes:
    mstr = "MODE%s" % m
    if cp.has_section(mstr):
        bof = cp.get(mstr, "bof_file")
        frq = cp.getfloat(mstr, "frequency")
        #info.append((m, bof, frq))
        if not info.has_key((bof, frq)):
            info[(bof, frq)] = [m]
        else:
            info[(bof, frq)].append(m)

print info        
    
# now create a cnf file for it
rn = "test" #"srbsr2-1"
fn2 = "%s-mmcm.conf" % rn
cp = ConfigParser.ConfigParser()
#cp.read(fn2)

sec = "MMCM" 
cp.add_section(sec)
keys = sorted(info.keys())
for i, key in enumerate(keys):
#for i in range(len(info)):
    bof, frq = key
    modes = info[(bof, frq)]
    opt = "mode[%d]" % i
    cp.set(sec, opt, value = ",".join([str(x) for x in modes]))
    opt = "boff[%d]" % i
    cp.set(sec, opt, value = bof)
    opt = "freq[%d]" % i
    cp.set(sec, opt, value = frq)
    opt = "adc0[%d]" % i
    cp.set(sec, opt, value = 0)
    opt = "adc1[%d]" % i
    cp.set(sec, opt, value = 0)

# Writing our configuration file to 'example.cfg'
with open(fn2, 'wb') as configfile:
    cp.write(configfile)        
