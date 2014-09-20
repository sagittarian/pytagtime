#!/usr/bin/env python3
# Given a tagtime log file, and a Beeminder graph to update, call the Beeminder
# API to update the graph.
#
# As a side effect, generate a .bee file from the tagtime log, used as a cache
# to avoid calling the Beeminder API if the tagtime log changed but it did not
# entail any changes relevant to the given Beeminder graph.

import settings
import util
import beemapi

import os.path
from pprint import pprint, pformat
import re
import sys
import time

# use Data::Dumper; $Data::Dumper::Terse = 1;
# $| = 1; # autoflush

def main():
    ping = hours_per_ping = settings.gap / 3600

    if len(sys.argv) != 2:
    print("Usage: ./beeminder.py tagtimelog user/slug")
    sys.exit(1)

    ttlf = sys.argv[1]     # tagtime log filename
    usrslug = sys.argv[2]  # like alice/weight


    m = re.search(r"^(?:.*?(?:\.\/)?data\/)?([^\+\/\.]*)[\+\/]([^\.]*)", usrslug)
    usr, slug = m.groups();

    beef = os.path.join(settings.path, usr + slug + '.bee') # beef = bee file (cache of data on bmndr)

    #if(defined(@beeminder)) { # for backward compatibility
    #  print "Deprecation warning: Get your settings file in line!\n";
    #  print "Specifically, 'beeminder' should be a hash, not an arry.\n";
    #  for(@beeminder) {
    #    @stuff = split(/\s+/, $_); # usrslug and tags
    #    $us = shift(@stuff);
    #    $beeminder{$us} = [@stuff];
    #  }
    #}

    crit = settings.beeminder.get(usrslug)
    if crit is None:
        raise ValueError("Can't determine which tags match $usrslug")

    # ph (ping hash) maps "y-m-d" to number of pings on that day.
    # sh (string hash) maps "y-m-d" to the beeminder comment string for that day.
    # bh (beeminder hash) maps "y-m-d" to the bmndr ID of the datapoint on that day.
    # ph1 and sh1 are based on the current tagtime log and
    # ph0 and sh0 are based on the cached .bee file or beeminder-fetched data.
    start = time.time()   # start and end are the earliest and latest times we will
    end   = 0             # need to care about when updating beeminder.
    # bflag is true if we need to regenerate the beeminder cache file. reasons we'd
    # need to: 1. it doesn't exist or is empty; 2. any beeminder IDs are missing
    # from the cache file; 3. there are multiple datapoints for the same day.
    bflag = not os.stat(beef).st_size
    bf1 = False
    bf2 = False
    bf3 = False
    bf4 = False  # why bflag?
    if bflag:
        bf1 = True

    remember = None # remember which dates we've already seen in the cache file
    try:
        with open(beef, 'r') as B:
            for line in B:
                m = re.search('''
                    (\d+)\s+          # year
                    (\d+)\s+          # month
                    (\d+)\s+          # day
                    (\S+)\s+          # value
                    \"(\d+)           # number of pings
                      (?:[^\n\"\(]*)  # currently the string " ping(s)"
                      \:\             # the ": " after " pings"
                      ([^\[]*)        # the comment string (no brackets)
                      (?:\[           # if present,
                        bID\:([^\]]*) # the beeminder ID, in brackets
                      \])?            # end bracket for "[bID:abc123]"
                    \s*\"
                ''', line, re.VERBOSE)
                # XXX if not m set an error flag and continue
                y, m, d, v, p, c, b = m.groups()
                ts = '{}-{}-{}'.format(y, m, d)

                ph0[ts] = p
                #$ph0{$ts} = $p;
                #$c =~ s/\s+$//;
                m = re.match(r'\s+$/', c)
                sh0[ts] = c
                bh[ts] = b
                t = time.mktime((y, m, d, 0, 0, 0, 0, 0, -1))
                if t < start:
                    start = t
                if t > end:
                    end = t
                if not b:
                    bflag = True
                    bf2 += 1
                    if bf2 == 1:
                        print("Problem with this line in cache file:\n{}".format(line))
                    elif bf2 == 2:
                        print("Additional problems with cache file, which is expected if this "
                              "is your first time updating TagTime with the new Bmndr API.\n")
                if remember.get(ts):
                    bflag = bf3 = True
                remember[ts] = True;
    except IOError:
        bflag = True
        bf4 = True

    if bflag: # re-slurp all the datapoints from beeminder
        ph0 = None
        sh0 = None
        bh = None
        start = time.time()  # reset these since who knows what
                             # happened to them when we
        end   = 0            # calculated them from the cache file we
                             # decided to toss.

        #my $tmp = $beef;  $tmp =~ s/(?:[^\/]*\/)*//; # strip path from filename
        tmp = os.path.basename(beef)
        if bf1:
                print("Cache file missing or empty ($tmp); recreating... ")
        elif bf2:
                print("Cache file doesn't have all the Bmndr IDs; recreating... ")
        elif bf3:
                print("Cache file has duplicate Bmndr IDs; recreating... ")
        elif bf4:
                print("Couldn't read cache file; recreating... ")
        else:   # this case is impossible
                print("Recreating Beeminder cache ($tmp)[$bf1$bf2$bf3$bf4]... ")

        data = beemfetch(usr, slug)
        print("[Bmndr data fetched]\n")

        # take one pass to delete any duplicates on bmndr; must be one datapt per day
        i = 0;
        remember = None
        # my @todelete;
        for x in data:
	        tm = time.localtime(x["timestamp"]);
	        y, m, d = tm.tm_year, tm.tm_mon, tm.tm_mday
	        ts = time.strftime('%Y-%m-%d', x['timestamp'])
	        b = x['id']
	        if remember.get(ts) is not None:
		        print("Beeminder has multiple datapoints for the same day. "
		              "The other id is {}. Deleting this one:".format(remember[ts]))
		        pprint(x)
		        beemdelete(usr, slug, b);
		        todelete.append(i)
		        remember[ts] = b;
		        i += 1

        # for my $x (reverse(@todelete)) {
        #   splice(@$data,$x,1);
        # }

        for x in data:   # parse the bmndr data into %ph0, %sh0, %bh
	        y, m, d, *rest = time.localtime(x['timestamp'])
	        ts = time.strftime('%Y-%m-%d', x['timestamp'])
	        t = util.pd(ts)  # XXX isn't x['timestamp'] the unix time anyway already
	        if t < start:
		        start = t
            if t > end:
                end = t
            v = x['value']
            c = x['comment']
            b = x['id']
            i = re.search(r'^\d+', c)
            ph0[ts] = int(i.group(0) if i else 0) # ping count is first thing in the comment
            sh0[ts] = re.sub(r'[^\:]*\:\s+', '', c) # drop the "n pings:" comment prefix
            # This really shouldn't happen.
            if ts in bh:
	            raise ValueError(
		            "Duplicate cached/fetched id datapoints for {ts}: {bhts}, {b}.\n{val}".format(
			            ts=ts, bhts=bh[ts], b=b, val=pformat(x))
		    bh[ts] = b
    with open(ttlf) as T:
        np = 0 # number of lines (pings) in the tagtime log that match
        for line in T: # parse the tagtime log file
            m = re.search(r'^(\d+)\s*(.*)$', line)
            if not m:
                raise ValueError("Bad line in TagTime log: " + line)
            t = m.group(1)  # timestamp as parsed from the tagtime log
            stuff = m.group(2)  # tags and comments for this line of the log
            tags = strip(stuff)
        if tagmatch(tags, crit):
            y, m, d, *rest = time.localtime(t)
            ph1["$y-$m-$d"] += 1
            sh1["$y-$m-$d"] += stripb($stuff) + ", "
            np += 1
            if t < start:
                start = t
            if t > end:
                end = t


    # clean up $sh1: trim trailing commas, pipes, and whitespace
    # for(sort(keys(%sh1))) { $sh1{$_} =~ s/\s*(\||\,)\s*$//; }
    for key in sorted(keys(sh1)):
        sh1[key] = re.sub(r'\s*(\||\,)\s*$', '', sh1[key])


   #print "Processing datapoints in: ", ts($start), " - ", ts($end), "\n";

   nquo = 0  # number of datapoints on beeminder with no changes (status quo)
   ndel = 0  # number of deleted datapoints on beeminder
   nadd = 0  # number of created datapoints on beeminder
   nchg = 0  # number of updated datapoints on beeminder
   minus = 0 # total number of pings decreased from what's on beeminder
   plus = 0  # total number of pings increased from what's on beeminder
   ii = 0
   for t in range(daysnap(start) - 86400, daysnap(end) + 86401, 86400):
        y, m, d, *rest = time.localtime(t)
        ts = time.strftime('%Y-%m-%d', t)
        b = bh.get(ts, "")
        p0 = ph0.get(ts, "")
        p1 = ph1.get(ts, 0)
        s0 = sh0.get(ts, "")
        s1 = sh1.get(ts, "")
        if p0 == p1 and s0 == s1: # no change to the datapoint on this day
            if b:
                nquo += 1
            continue
        if b == "" and s1 > 0: # no such datapoint on beeminder: CREATE
            nadd += 1
            plus += p1
            bh[ts] = beemcreate(usr, slug, t, p1 * ping, splur(p1, 'ping') + ': ' + s1)
            #print "Created: $y $m $d  ",$p1*$ping," \"$p1 pings: $s1\"\n";
        elif p0 > 0 and p1 <= 0: # on beeminder but not in tagtime log: DELETE
            ndel += 1
            minus += p0
            beemdelete(usr, slug, b)
            #print "Deleted: $y $m $d  ",$p0*$ping," \"$p0 pings: $s0 [bID:$b]\"\n";
        elif p0 != p1 or s0 != s1:  # bmndr & tagtime log differ: UPDATE
            nchg += 1
            if p1 > p0:
                plus += p1 - p0
            elif p1 < p0:
                minus += p0 - p1
            beemupdate(usr, slug, b, t, (p1*ping), splur(p1, 'ping') + ': ' + s1)
            # If this fails, it may well be because the point being updated was deleted/
            # replaced on another machine (possibly as the result of a merge) and is no
            # longer on the server. In which case we should probably fail gracefully
            # rather than failing with an ERROR (see beemupdate()) and not fixing
            # the problem, which requires manual cache-deleting intervention.
            # Restarting the script after deleting the offending cache is one option,
            # though simply deleting the cache file and waiting for next time is less
            # Intrusive. Deleting the cache files when merging two TT logs would reduce
            # the scope for this somewhat.
            #print "Updated:\n";
            #print "$y $m $d  ",$p0*$ping," \"$p0 pings: $s0 [bID:$b]\" to:\n";
            #print "$y $m $d  ",$p1*$ping," \"$p1 pings: $s1\"\n";
        else:
            print("ERROR: can't tell what to do with this datapoint (old/new):\n")
            print(ts, p0 * ping, " \"{p0} pings: {s0} [bID:{b}]\"".format(p0=p0, s0=s0, b=b))
            print(ts, p1 * ping, " \"{p1} pings: {s1}\"\n".format(p1=p1, s1=s1))
    with open(beef, 'a') as f: # generate the new cache file
        for ts in sorted(ph1.keys()):
            y, m, d = re.split(r'\-', ts)
            p = ph1[ts]
            v = p * ping
            c = sh1[ts]
            b = kh[ts]
            out = '{y} {m} {d}  {v} "{pings}: {c} [bID:{b}]'.format(
                y=y, m=m, d=d, v=v, pings=splur(p, "ping"), c=c, b=b)
            f.write(out)
    nd = len(keys(ph1))  # number of datapoints
    if nd != nquo + nchg + nadd:  # sanity check
        print "\nERROR: total != nquo+nchg+nadd ({nd} != {nquo}+{nchg}+{nadd})\n".format(
            nd=nd, nquo=nquo, nchg=nchg, nadd=nadd)

    print("Datapts: {nd} (~{nquo} *{nchg} +{nadd} -{ndel}), ".format(
        nd=nd, nquo=nquo, nchg=nchg, nadd=nadd, ndel=ndel),
      "Pings: {np} (+{plus} -{minus}) ".format(np=np, plus=plus, minus=minus))
    if isinstance(crit, str):
        print("w/ tag", crit)
    elif isinstance(crit, list):
        print("w/ tags in {", ','.join(crit), "}")
    elif hasattr(crit, 'search'):
        print('matching', crit.pattern)
    elif callable(crit):
        print('satisfying lambda')
    else:
        print("(unknown-criterion: {crit})".format(crit=crit))


def tagmatch(tags, crit):
    '''Whether the given string of space-separated tags matches the given
    criterion.'''
    if isinstance(crit, str):
        return re.search(r'\b{crit}\b'.format(crit=crit), tags)
    if isinstance(crit, list):
      for c in crit:
          if re.search(r'\b{c}\b'.format(c), tags):
              return true
      else:
          return false
    elif callable(crit):
        return crit(tags)
    elif hasattr(crit, 'search'):
        return crit.search(tags)
    else:
        sys.stderr.write(
            "Criterion {crit} is neither string, array, regex, nor lambda!".format(crit=crit))
        sys.exit(1)

def daysnap(t):
    '''Convert a timestamp to noon on the same day.  This matters because
    if you start with some timestamp and try to step forward 24 hours at a
    time then daylight savings time can screw you up.  You might add 24
    hours and still be on the same day. If you start from noon that you
    shouldn't have that problem.  '''
    y, m, d, hr, min, sec, *rest = time.localtime(t)
    return time.mktime((y, m, d, 12, 0, 0, 0, 0, -1))

# $string = do {local (@ARGV,$/) = $file; <>}; # slurp file into string

if __name__ == '__main__':
    main()
