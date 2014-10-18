# Utility functions for tagtime.
# This uses settings from ~/.tagtimerc so that must have been loaded first. # XXX

import datetime
import math
import re
import subprocess
import sys
import time

linelen = 79 # XXX put this in settings

def clip(x, a, b):
    return max(a, min(b, x))

def callcmd(cmd):
    if subprocess.call(cmd) != 0:
        print('SYSERR:', cmd, file=sys.stderr)


class Random:

    def __init__(self, gap, seed):
        self.IA = 16807      # constant used for RNG
                             # (see p37 of Simulation by Ross)
        self.IM = 2147483647 # constant used for RNG (2^31-1)
        self.seed = seed     # state of the RNG
        self.initseed = seed
        self.gap = gap

    def ran0(self):
        '''Returns a random integer in [1,$IM-1]; changes self.seed, ie, RNG
        state.  (This is ran0 from Numerical Recipes and has a period
        of ~2 billion.)

        '''
        self.seed = self.IA * self.seed % self.IM
        return self.seed

    def ran01(self):
        '''Returns a U(0,1) random number.'''
        return self.ran0() / self.IM


    def exprand(self):
        '''Returns a random number drawn from an exponential distribution with mean
        self.gap.

        '''
        return -1 * self.gap * math.log(self.ran01())

    def nextping(self, prev):
        '''Takes previous ping time, returns random next ping time (unixtime).
        NB: this has the side effect of changing the RNG state ($seed)
            and so should only be called once per next ping to calculate,
            after calling prevping.
        '''
        # XXX round1
        return max(prev + 1, round(prev + self.exprand()))

    def prevping(self, t):
        '''Computes the last scheduled ping time before time t.'''
        self.seed = self.initseed
        # Starting at the beginning of time, walk forward computing
        # next pings until the next ping is >= t.
        nxtping = 1184083200  # the birth of timepie/tagtime!
        # import time
        # nxtping = time.time() - 1000 # XXX debugging
        lstping = nxtping
        lstseed = self.seed
        while nxtping < t:
            lstping = nxtping
            lstseed = self.seed # XXX this is an ugly way to handle state
            nxtping = self.nextping(nxtping)
        self.seed = lstseed
        return lstping


def strip(s):
    '''Strips out stuff in parens and brackets;
    remaining parens/brackets means they were unmatched.

    '''
    while True:
        s, n = re.subn(r'\([^\(\)]*\)', '', s)
        if n == 0:
            break
    while True:
        s, n = re.subn(r'\[[^\[\]]*\]', '', s)
        if n == 0:
            break
    # Also remove trailing whitespace? (this breaks cntpings)
    # s = re.sub(r'\s*$', '', s)

    return s

def stripb(s):
    '''Strips out stuff in brackets only; remaining brackets means
    they were unmatched.'''
    return re.sub(r'\s*\[[^\[\]]*\]', '', s)


def stripc(s):
    '''Strips out stuff *not* in parens and brackets.'''
    pairs = {
        '(': ')',
        '[': ']'
    }
    reverse_pairs = {pairs[val]: key for key in pairs}

    result = []
    openers = []
    i = 0
    while i < len(s):
        if s[i] in pairs:
            openers.append(i)
        elif s[i] in reverse_pairs:
            if openers and s[openers[-1]] == reverse_pairs[s[i]]:
                start = openers.pop()
                if not openers:  # closed all parens
                    result.append(s[start:i+1])
                # else ignore/continue, will be appended to the
                # result when the last parens is closed
            # else unmatched closer, ignore
        i += 1

    # Here is the original perl implementation
    # sub stripc {
    #   my($s) = @_;
    #   my $tmp = $s;
    #   while($tmp =~ s/\([^\(\)]*\)/UNIQUE78DIV/g) {}
    #   while($tmp =~ s/\[[^\[\]]*\]/UNIQUE78DIV/g) {}
    #   my @a = split('UNIQUE78DIV', $tmp);
    #   for(@a) {
    #     my $i = index($s, $_);
    #     substr($s, $i, length($_)) = "";
    #   }
    #   return $s;
    # }

def parsable(s):
    '''Whether the given string is valid line in a tagtime log file'''
    s = self.strip(s)
    # return not (not re.search(r'^\d+\s+', s) or
    #             re.search(r'(\(|\)|\[|\])', s))
    return re.search(r'^\d+\s+', s) and not re.search(r'(\(|\)|\[|\])', s)

def fetchp(s):
    '''Fetches stuff in parens. Not currently used.'''
    tmp = stripc(s)
    return NotImplemented
    #sub fetchp {
    #  my($s) = @_;
    #  my $tmp = $s;
    #  while($tmp =~ s/\([^\(\)]*\)/UNIQUE78DIV/g) {}
    #  my @a = split('UNIQUE78DIV', $tmp);
    #  for(@a) {
    #    my $i = index($s, $_);
    #    substr($s, $i, length($_)) = "";
    #  }
    #  $s =~ s/^\(//;
    #  $s =~ s/\)$//;
    #  return $s;
    #}

def gettags(s):
    '''Extracts tags prepended with colons and returns them space-separated.
    Eg: "blah blah :foo blah :bar" --> "foo bar"'''
    return re.findall(r'\s\:([\w\_]+)', strip(s))

def lockb():
    '''Blocking lock -- try to get the lock and wait if we can't.'''
    okFlag = True # False if we had to override the lock or something.
    # okFlag is currently just "whether we had to wait at all for the lock"
    if cygwin: # stupid windows # XXX cygwin
        while os.path.exists(lockf): # XXX lockf
            print("TagTime is locked.  Waiting 30 seconds...\n")
            time.sleep(30)
            okFlag = False
        cmd = ["/usr/bin/touch", lockf]
        if subprocess.call(cmd) != 0:
            print("SYSERR:", cmd, file=sys.stderr)
    else: # nice unix (including mac)
        #  my $okFlag = 1;
        #  if($cygwin) {
        #    while(-e $lockf) {

        #      sleep(30);
        #      $okFlag = 0;
        #    }
        #    $cmd = "/usr/bin/touch $lockf";
        #    system($cmd) == 0 or print "SYSERR: $cmd\n";
        #  } else {
        #    sysopen(LF, $lockf, O_RDONLY | O_CREAT) or die "Can't open lock file: $!";
        with open(lockf, 'r') as lf:
            try:
                fcntl.lockf(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError as e:
                if e.errno in (errno.EACCES, errno.EAGAIN):
                    print('Tagtime is locked.  Waiting...',
                          end=' ', file=sys.stderr)
                    try:
                        fcntl.lockf(lf, LOCK_EX)
                    except IOError as e2:
                        print("Can't lock {}: {}".format(lockf, e2))
                        raise
                    print('ready!', end='\n\n')
                    okFlag = False
        return okFlag
        #    if(!flock(LF, LOCK_EX | LOCK_NB)) {  # exclusive, nonblocking lock.
        #      print "TagTime is locked.  Waiting...";
        #      flock(LF, LOCK_EX) or die "Can't lock $lockf: $!";
        #      print " ready!\n\n";
        #      $okFlag = 0;
        #    }


# def lockn():
#     '''Nonblocking lock -- try to get the lock and return 0 if we can't.'''
#     if settings.cygwin:  # stupid windows
#         if os.path.exists(lockf): return False
#         cmd = ["/usr/bin/touch", lockf]
#         if subprocess.call(cmd) != 0:
#             print("SYSERR:", cmd, file=sys.stderr)
#     else:
#         pass


#sub lockn {
#  if($cygwin) {  # stupid windows
#    if(-e $lockf) { return 0; }
#    $cmd = "/usr/bin/touch $lockf";
#    system($cmd) == 0 or print "SYSERR: $cmd\n";
#  } else {  # nice unix (including mac)
#    sysopen(LF, $lockf, O_RDONLY | O_CREAT) or die "Can't open lock file: $!";
#    # Don't wait if we can't get the lock, the next cron'd version'll get it
#    if(!flock(LF, LOCK_EX | LOCK_NB)) { return 0; }
#    flock(LF, LOCK_EX) or die "Can't lock $lockf: $!";
#  }
#  return 1;
#}
#
## Release the lock.
#sub unlock {
#  if($cygwin) {  # stupid windows
#    $cmd = "/bin/rm -f $lockf";
#    system($cmd) == 0 or print "SYSERR: $cmd\n";
#  } else {  # nice unix
#    close(LF);  # release the lock.
#  }
#}
#
def splur(n, noun):
    '''Singular or Plural:  Pluralize the given noun properly, if n is not 1.
    Eg: splur(3, "boy") -> "3 boys"'''
    return '{n} {noun}{end}'.format(
        n=n, noun=noun, end='' if n == 1 else 's')

def divider(label, ll=linelen):
    '''Takes a string "foo" and returns "-----foo-----" of length $linelen.'''
    n = len(label)
    left = (ll - n) // 2
    right = ll - left - n
    return ('-' * left) + label + ('-' * right)

def lrjust(a, b, x=linelen):
    '''Takes 2 strings and returns them concatenated with enough space in
    the middle so the whole string is x long (default: linelen).'''
    return '{a}{spaces}{b}'.format(
        a=a, spaces=' ' * max(0, x - len(a) - len(b)), b=b)

def annotime(a, t, ll=linelen):
    '''Annotates a line of text with the given timestamp.'''
    tt = datetime.datetime.fromtimestamp(t).timetuple()
    candidates = [
       "[%Y-%m-%d %H:%M:%S %a]",   # 24 chars
       "[%m.%d %H:%M:%S %a]",      # 18 chars
       "[%d %H:%M:%S %a]",         # 15 chars
       "[%m.%d %H:%M:%S]",         # 14 chars
       "[%H:%M:%S %a]",            # 12 chars
       "[%m.%d %H:%M]",            # 11 chars
       "[%d %H:%M:%S]",            # also 11 so this will never get chosen
       "[%H:%M %a]",               #  9 chars
       "[%H:%M:%S]",               #  8 chars
       "[%d %H:%M]",               # also 8 so this will never get chosen
       "[%H:%M]",                  #  5 chars
       "[%M]"                      #  2 chars
    ]

    maxlen = linelen - len(a) - 1

    for candidate_format in candidates:
        candidate = time.strftime(candidate_format, tt)
        if len(candidate) + len(a) + 1 <= ll:
            return lrjust(a, candidate, ll)
    return a


class Logger:

    def __init__(self, logf, linelen = 80):
        self.logf = logf
        self.linelen = linelen

    def log(self, s):
        '''append a string to the log file'''
        if s and s[-1] != '\n':
            s = s + '\n'
        with open(self.logf, 'a') as f:
            f.write(s)
    slog = log # original name


def dd(n):
    '''double-digit: takes number from 0-99,
    returns 2-char string eg "03" or "42".'''
    return '{:02}'.format(n)



def padl(x, p, w):
    '''pad left: returns string x but with p's prepended so it has width w'''
    if len(x) >= w:
        return x[:len(w)]
    return p * (w - len(x)) + x

## pad right: returns string x but with p's appended so it has width w
#sub padr {
#  my($x,$p,$w) = @_;
#  if(length($x) >= $w) { return substr($x,0,$w); }
#  return $x . $p x ($w-length($x));
#}
#
##
#sub isnum { my($x)=@_; return ($x=~ /^\s*(\+|\-)?(\d+\.?\d*|\d*\.?\d+)\s*$/); }
def isnum(x):
    '''Whether the argument is a valid real number.'''
    return re.search(r'^\s*(\+|\-)?(\d+\.?\d*|\d*\.?\d+)\s*$', x)

## DATE/TIME FUNCTIONS FOLLOW
#
## Date/time: Takes unixtime in seconds and returns list of
##   year, mon, day, hr, min, sec, day-of-week, day-of-year, is-daylight-time
## In python this is going to translate to time.localtime()
#sub dt { my($t) = @_;
#  $t = time unless defined($t);
#  my($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime($t);
#  $year += 1900;  $mon = dd($mon+1);  $mday = dd($mday);
#  $hour = dd($hour);  $min = dd($min); $sec = dd($sec);
#  my %wh = ( 0=>"SUN",1=>"MON",2=>"TUE",3=>"WED",4=>"THU",5=>"FRI",6=>"SAT" );
#  return ($year,$mon,$mday,$hour,$min,$sec,$wh{$wday},$yday,$isdst);
#}
#
## Time string: takes unixtime and returns a formated YMD HMS string.
#sub ts { my($t) = @_;
#  my($year,$mon,$mday,$hour,$min,$sec,$wday,$yday,$isdst) = dt($t);
#  return "$year-$mon-$mday $hour:$min:$sec $wday";
#}
#
## Human-Compressed Time String: like 0711281947 for 2007-11-28 19:47
#sub hcts { my($t) = @_;
#  if($t % 60 >= 30) { $t += 60; } # round to the nearest minute.
#  my($year,$mon,$mday,$hour,$min,$sec,$wday,$yday,$isdst) = dt($t);
#  return substr($year,-2)."${mon}${mday}${hour}${min}";
#}
#
## Seconds to str: takes number of seconds, returns a string like 1d02h03:04:05
#sub ss { my($s) = @_;
#  my($d,$h,$m);
#  my $incl = "s";
#
#  if($s < 0) { return "-".ss(-$s); }
#
#  $m = int($s/60);
#  if($m > 0) { $incl = "ms"; }
#  $s %= 60;
#  $h = int($m/60);
#  if($h > 0) { $incl = "hms"; }
#  $m %= 60;
#  $d = int($h/24);
#  if($d > 0) { $incl = "dhms"; }
#  $h %= 24;
#
#  return ($incl=~"d" ? "$d"."d" : "").
#         ($incl=~"h" ? dd($h)."h" : "").
#         ($incl=~"m" ? dd($m).":" : "").
#         ($incl!~"m" ? $s : dd($s))."s";
#}
#
## just like above but with the biggest possible unit being hours instead of days
#sub ss2 { my($s) = @_;
#  my($d,$h,$m);
#  my $incl = "s";
#
#  if($s < 0) { return "-".ss2(-$s); }
#
#  $m = int($s/60);
#  if($m > 0) { $incl = "ms"; }
#  $s %= 60;
#  $h = int($m/60);
#  if($h > 0) { $incl = "hms"; }
#  $m %= 60;
#
#  return ($incl=~"h" ? $h."h" : "").
#         ($incl=~"m" ? dd($m).":" : "").
#         ($incl!~"m" ? $s : dd($s))."s";
#}
#
#
## Parse ss: takes a string like the one returned from ss() and parses it,
## returning a number of seconds.
#sub pss { my($s) = @_;
#  $s =~ /^\s*(\-?)(\d*?)d?(\d*?)h?(\d*?)(?:\:|m)?(\d*?)s?\s*$/;
#  return ($1 eq '-' ? -1 : 1) * ($2*24*3600+$3*3600+$4*60+$5);
#}
#
def pd(s):
    '''Parse Date: must be in year, month, day, hour, min, sec order,
    returns unixtime.'''
    #  my($year, $month, $day, $hour, $minute, $second);
    m = re.search(
        '''^\s*(\d{1,4})\W*0*(\d{1,2})\W*0*(\d{1,2})\W*0*
        (\d{0,2})\W*0*(\d{0,2})\W*0*(\d{0,2})\s*.*$''', s, re.VERBOSE)
    if m:
        year = int(m.group(1)) if m.group(1) else 0
        month = int(m.group(2)) if m.group(2) else 0
        day = int(m.group(3)) if m.group(3) else 0
        hour = int(m.group(4)) if m.group(4) else 0
        minute = int(m.group(5)) if m.group(5) else 0
        second = int(m.group(6)) if m.group(6) else 0
        if year < 100:
            if year < 70:
                year = 2000 + year
            else:
                year = 1900 + year
    else:
        year, month, day, hour, minute, second = 1969, 12, 31, 23, 59, 59
        # indicates couldn't parse it.

    tm = (year, month, day, hour, minute, second, 0, 0, -1)
    return time.mktime(tm)


## SCRATCH AREA:
#
## Implementation of ran0 in C, from numerical recipes:
#
## #define IA 16807
## #define IM 2147483647
## #define AM (1.0/IM)
## #define IQ 127773
## #define IR 2836
## static long seed = 1;
## long ran0() {
##   long k = (seed)/IQ;
##   seed = IA*((seed) - k*IQ) - IR*k;
##   if (seed < 0) { seed += IM; }
##   return (seed);
## }
#
## Implementation of ran0 in Mathematica:
#
## IA = 7^5;  IM = 2^31-1;
## RAN = Rationalize[AbsoluteTime[]*1000,1];
## setSeed[i_] := (RAN = i)
## ran0[] := (RAN = Mod[IA * RAN, IM])
#




