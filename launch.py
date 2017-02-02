#!/usr/bin/env python3

'''
Check if it's time (or past time) to ping. If so, catch up on missed pings
and/or launch ping.py for the current ping.
This should be called by the daemon (tagtimed.py) every time a ping is due.
'''

import datetime
import subprocess
import time

from settings import settings
import util

import os
import sys
import re

rand = settings.rand
logger = settings.logger

test = 'test' in sys.argv
quiet = 'quiet' in sys.argv

launchtime = time.time()


def editor(f, t):
    '''Launch an editor to edit file f, labeling the window with title t.'''
    if not os.environ.get('DISPLAY', None):
        os.environ['DISPLAY'] = ':0.0'  # must set explicitly if run from cron
    cmd = settings.get_edit_cmd(f, t)
    util.callcmd(cmd)


# Launch the tagtime pinger for the given time (in unix time).
def launch(t):
    lt = time.localtime(t)
    hour, min, sec = ('{:02}'.format(i) for i in [lt.tm_hour, lt.tm_min, lt.tm_sec])
    # os.environ['DISPLAY'] = ':0.0' # have to set this explicitly if
    # invoked by cron.
    util.playsound()
    pingpath = os.path.join(settings.path, 'ping.py')
    cmd = settings.get_xt_cmd(
        'TagTime {hour}:{min}:{sec}'.format(hour=hour, min=min, sec=sec),
        pingpath, str(t))
    util.callcmd(cmd)


def lastln():
    '''Returns the last line in the log but as a 2-tuple
    consisting of timestamp and rest of the line.'''
    x = None
    with open(settings.logf) as f:
        for x in f:
            pass
    m = re.search(r'^\s*(\d+)\s*(.*)$', x)
    if m:
        return int(m.group(1)), m.group(2)
    return None, None


if test:  # just pop up the editor and exit; mainly for testing.
    editor(settings.logf, "TagTime Log Editor " +
           "(invoked explicitly with \"test\" arg)")
    sys.exit(0)

# figure out the next ping after the last one that's in the log file
if os.path.exists(settings.logf):
    lll = subprocess.check_output(['tail', '-1', settings.logf])  # last line
    # parse out the timestamp for the last line, which better
    # be equal to nextping@prevping of itself.
    m = re.search(br'^\s*(\d+)', lll)
    lstping = int(m.group(1)) if m is not None else 0

    tmp = rand.nextping(rand.prevping(lstping))
    # NB: must call prevping before nextping

    if lstping == tmp:
        nxtping = rand.nextping(lstping)
    else:
        # XXX configurable encoding
        print("TagTime log file ({logf}) has bad last line:\n{lll}".format(
            logf=settings.logf, lll=lll.decode('ascii')))
        nxtping = rand.prevping(launchtime)
else:
    nxtping = rand.prevping(launchtime)

# XXX locking
# if(!lockn()) {
#    print "Can't get lock. Exiting.\n" unless $quiet;
#    exit(1);
# } # Don't wait if we can't get the lock.

editorflag = False

# First, if we missed any pings by more than $retrothresh seconds for no
# apparent reason, then assume the computer was off and auto-log them.
while nxtping < launchtime - settings.retrothresh:
    line = "{nxtping} afk off RETRO".format(nxtping=nxtping)
    logger.log(util.annotime(line, nxtping))
    nxtping = rand.nextping(nxtping)
    editorflag = True

# # Next, ping for any pings in the last retrothresh seconds.
while True:
    while nxtping <= time.time():
        if nxtping < time.time() - settings.retrothresh:
            line = util.annotime('{} afk RETRO'.format(nxtping),
                                 nxtping) + "\n"
            logger.log(line)
            editorflag = True
        else:
            launch(nxtping)  # this shouldn't complete till you answer

        ts, ln = lastln()
        if ts != nxtping:  # in case, eg, we closed the window w/o answering.
            # suppose there's a ping window waiting (call it ping 1),
            # and while it's sitting there unanswered another ping
            # (ping 2) pings.  then you kill the ping 1 window.  the
            # editor will then pop up for you to fix the err ping but
            # there will be nothing in the log yet for ping 2.
            # perhaps that's ok, just thinking out loud here...
            logger.log(util.annotime(
                '{nxtping} err [missed ping from {pingdelta} ago]'.format(
                    nxtping=nxtping,
                    pingdelta=datetime.timedelta(seconds=time.time()-nxtping)),
                nxtping
            ))
            editor(settings.logf,
                   'TagTime Log Editor (unanswered pings logged as "err")')
            editorflag = False
        elif not ln.strip():  # no tags in last line of log.
            # editor(settings.logf,
            # "TagTime Log Editor (add tags for last ping)")
            editorflag = True
        lstping = nxtping
        nxtping = rand.nextping(nxtping)
        # Here's where we would add an artificial gap of $nxtping-$lstping.
    if editorflag:
        editor(settings.logf, "TagTime Log Editor (fill in your RETRO pings)")
        # when editor finishes there may be new pings missed!
        # that's why we have the outer do-while loop here, to start over if
        # there are new pings in the past after we finish editing.
    if nxtping > time.time():
        break

util.unlock()

# SCHDEL (SCHEDULED FOR DELETION): (discussion and code for artificial gaps)
# It can happen that 2 pings can both occur since we last checked (a minute
# ago if using cron) which means that this script would notice them both *now*
# and ping you twice in a row with zero gap.  That's bad.
# This fixes that by checking if the next ping is overdue but not a
# retro-ping (ie, a *now* ping), in which case pause for the number of
# seconds between lstping and nxtping (but not more than retrothresh seconds).
# UPDATE: There were too many subtle corner cases with the above (like what
# if the computer was turned off (hibernating) while executing sleep()) so
# I got rid of it.
#
# We're now counting on this script being run within a
# couple seconds of each ping else all pings within retrothresh will come up
# with zero gap.

# if another ping is overdue, mind the gap! (ie delay the 2nd ping so as to
# maintain the original gap betw them (but not more than retrothresh)):

# if another ping is overdue, mind the gap! (ie delay the 2nd ping so as to
# maintain the original gap betw them (but not more than retrothresh)):
# my $now = time();
# my $eaten = $now - $prompt;   # subtract amount of time eaten up
#                                 #   answering last ping
# if ($nxtping<$now && $nxtping>=$now-$retrothresh) {
#    sleep(max(0, $nxtping - max($lstping,$now-$retrothresh) - $eaten));
# }
