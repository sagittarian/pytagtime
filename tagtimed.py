#!/usr/bin/env python3
'''
  TagTime daemon: this figures out from scratch when to beep and does so,
    continuously, even when the previous ping is still unanswered.
  After each ping it also runs launch.pl (with the 'quiet' arg since
    this is already doing the beeping) which launches popups or an editor
    for any overdue pings.
  Might be nice to watch ~/.tagtimerc (aka settings.pl) for changes a la
    watching.pl so that we don't have to restart this daemon when settings
    change. (does it suffice to just re-require it?)
'''
#
#=head1 NAME
#
#tagtimed - Stochastic tagging of your time!
#
#=head1 SYNPOSIS
#
#    $ tagtimed.pl     # Start tagtime
#
#    $ tagtimed.pl -l  # Start tagtime if not already running.
#
#    $ tagtimed.pl -s  # Start tagtime if not already running, be silent otherwise.
#
#=head1 DESCRIPTION
#
#See L<http://messymatters.com/tagtime/>
#
#You can add the following to your C<.bashrc> or equivalent to make sure TagTime starts
#when you open a shell:
#
#    tagtimed.pl -l -s &
#
#=head1 BUGS
#
#The C<-l> switch must be used on all processes for locks to work correctly.
#
#The C<-l> switch will exit Tagtime if it's already running with another user using the C<-l>
#switch.
#
#=cut
#
#{
#    use strict;
#    use warnings;
#    use Fcntl qw(:flock);
#    use Getopt::Std qw(getopts);
#
#    # Lock our process if required.  For more details, see:
#    # http://perltraining.com.au/tips/2005-08-08.html
#
#    # Note: without the '-l' switch, we won't even try to create a lock.
#
#    my %opts = ( l => 0, s => 0);   # [l]ock and [s]ilent
#
#    getopts('ls',\%opts);
#
#    # Lock process if called with -l switch
#    if ($opts{l} and not flock(DATA,LOCK_EX|LOCK_NB)) {
#
#        # Oops, we're already locked...
#        exit(0) if $opts{s};        # Silent exit on already locked.
#        die "Already running\n";    # Noisy exit otherwise.
#    }
#}
#
# XXX locking

import datetime
import os
import shlex
import subprocess
import sys
import time
try:
    import pause
except ImportError:
    pause = None

def wait(nextping):
    '''Sleep till the next ping.

    If available, we will use the pause library to get better precision,
    otherwise we'll wait just a few seconds in case the machine is suspended.
    '''
    if pause:
        pause.until(nextping)
    else:
        time.sleep(util.clip(nextping - time.time(), 0, 2))

from settings import settings

launchtime = time.time()

import util

rand = settings.rand

lstping = rand.prevping(launchtime)
nxtping = rand.nextping(lstping)

if settings.cygwin:
	util.unlock()  # on cygwin may have stray lock files around.

# Catch up on any old pings.
cmd = os.path.join(settings.path, 'launch.py')
if subprocess.call(cmd) != 0:
    print('SYSERR:', cmd, file=sys.stderr)

tdelta = datetime.timedelta(seconds=time.time()-lstping)
print("TagTime is watching you! Last ping would've been",
      tdelta, "ago.", file=sys.stderr)

start = time.time()
i = 1

while True:
    # sleep till next ping but check again in at most a few seconds in
    # case computer was off (should be event-based and check upon wake).
    wait(nxtping)

    # time.sleep(util.clip(nextping - time.time(), 0, 2))
    now = time.time()

    if nxtping <= now:
        if settings.catchup or nxtping > now - settings.retrothresh:
	        util.playsound()

        # invokes popup for this ping plus additional popups if there were more
        #   pings while answering this one:
        cmd = [os.path.join(settings.path, 'launch.py'), 'quiet', '&'];
        util.callcmd(cmd)
        s = '{i: 4}: PING! gap {gap} avg {avg} tot {tot}'.format(
            i=i,
            gap=datetime.timedelta(seconds=nxtping-lstping),
            avg=datetime.timedelta(seconds=(0.0 + time.time() - start) / i),
            tot=datetime.timedelta(seconds=(0.0 + time.time() - start)))
        print(util.annotime(s, nxtping, 72), file=sys.stderr)

        lstping = nxtping
        nxtping = rand.nextping(nxtping)
        i += 1


## Invoke popup for this ping plus additional popups if there were more pings
## while answering this one.
def pingery():
    # TODO: move everything from launch.py to here
    return 0


#
#__DATA__
#This section exists to make it trivial to implement the -l (lock)
#feature of tagtimed.
#
