#!/usr/bin/env python3

# Prompt for what you're doing RIGHT NOW.
# In the future this should show a cool pie chart that lets you click on the
# appropriate pie slice, making that slice grow slightly. And the slice
# boundaries could be fuzzy to indicate the confidence intervals! Ooh, and you
# can drag the slices around to change the order so similar things are next to
# each other and it remembers that order for next time! That's gonna rock.

from settings import settings
import util
import ansi

import re
import time
import sys

logger = settings.logger

eflag = 0  # Error flag

# Send pings to the given beeminder goal, e.g. passing "alice/foo" sends
# appropriate (as defined in .tagtimerc) pings to bmndr.com/alice/foo
def bm(s):
    cmd = [os.path.join(settings.path, "beeminder.py"), settings.logf, s]
    if not util.callcmd(cmd):
        eflag += 1


# Return what the user was last doing by extracting it from their logfile.
# Timestamps and comments are removed.
# On error, throws an exception.
def get_last_doing():
    with open(settings.logf, 'r') as f:
        last = list(f)[-1]
    respm = re.search(r'''
^
    \d+      # Timestamp
    \s+      # Spaces after timestamp
    (.*)         # Om nom nom
                      ''', last, re.X)

    if not respm:
        print("ERROR: Failed to find any tags for ditto function. "
              "Last line in TagTime log:\n", last, file=sys.stderr)
        sys.exit(1)
    return util.strip(respm.group(1)).strip()  # remove comments and timestamps


pingtime = time.time()
autotags = ''


eflag = 0 # if any problems then prompt before exiting

# if passed a parameter, take that to be the timestamp for this ping.
# if not, then this must not have been called by launch.py so tag as UNSCHED.
if len(sys.argv) > 1:
    t = int(sys.argv[1])
else:
    autotags += " UNSCHED"
    t = time.time()

# Can't lock the same lockfile here since launch.pl will have the lock!
# This script may want to lock a separate lock file, just in case multiple
# instances are invoked, but launch.pl will only launch one at a time.
# lockb();  wait till we can get the lock.

if pingtime - t > 9:
    print(util.divider(''))
    print(util.divider(" WARNING "*8))
    print(util.divider(''))
    print("This popup is", pingtime - t, "seconds late.")
    print('Either you were answering a previous ping when '
          'this tried to pop up, or you just started the '
          'tagtime daemon (tagtimed.py), '
          'or your computer\'s extremely sluggish.')
    print(util.divider(''))

# XXX tasks
# TODO
# Figure out what to do with taskfiles (as per the perl version)
# taskfile = str(settings.path) + str(settings.user) + ".tsk"
# walk through the task file, printing the active tasks and capturing the list
# of tags for each task (capturing in a hash keyed on task number).
# TODO: have a function that takes a reference to a tasknum->tags hash and a
# tasknum->fulltaskline hash and populates those hashes, purging them first.
# that way we we're not duplicating most of this walk through code. one
# annoyance: we want to print them in the order they appear in the task file.
# maybe an optional parameter to the function that says whether to print the
# tasks to stdout as you encounter them.
# if(-e $tskf) {  # show pending tasks
#   if(open(F, "<$tskf")) {
#     while(<F>) {
#       if(/^\-{4,}/ || /^x\s/i) { print; last; }
#       if(/^(\d+)\s+\S/) {
#         print;
#         $tags{$1} = gettags($_);  # hash mapping task num to tags string
#       } else { print; }
#     }
#     close(F);
#   } else {
#     print "ERROR: Can't read task file ($tskf)\n";
#     $eflag++;
#   }
#   print "\n";
# }

#s, m, h, d, *rest = time.localtime(t)
y, m, d, h, m, s, *rest = time.localtime(t)
s = util.dd(s)
m = util.dd(m)
h = util.dd(h)
d = util.dd(d)

print("It's tag time!  What are you doing RIGHT NOW ({}:{}:{})?".format(h, m, s))

# Get what the user was last doing. In the case this fails, set eflag and
# print the reason why.

try:
    last_doing = get_last_doing()
except Exception as e:
    last_doing = ''
    eflag += 1
    print('ERROR:', e, file=sys.stderr)
else:
    last_doing = last_doing.strip()

ansi_last_doing = last_doing
ansi_last_doing = ansi.cyan + ansi.bold + last_doing + ansi.reset

print('Ditto (") to repeat prev tags: {}\n'.format(ansi_last_doing))

# my($resp, $tagstr, $comments, $a);
# do {
#   use strict;
#   use warnings;

#   our (%tags, $t);
while True:
    resp = input().strip()
    if resp == '"':
        # Responses for lazy people. A response string consisting of only
        # a pair of double-quotes means "ditto", and acts as if we entered
        # the last thing that was in our TagTime log file.
        resp = last_doing

    # TODO
    #   # refetch the task numbers from task file; they may have changed.
    #   if(-e $tskf) {
    #     if(open(F, "<$tskf")) {
    #       %tags = ();  # empty the hash first.
    #       while(<F>) {
    #         if(/^\-{4,}/ || /^x\s/i) { last; }
    #         if(/^(\d+)\s+\S/) { $tags{$1} = gettags($_); }
    #       }
    #       close(F);
    #     } else {
    #       print "ERROR: Can't read task file ($tskf) again\n";
    #       $eflag++;
    #     }
    #   }
    # XXX task file

    tagstr = util.strip(resp).strip()
    comments = util.stripc(resp).strip()
    #tagstr = re.sub(r'\b(\d+)\b', lambda m)
    #$tagstr =~ s//($tags{$1} eq "" ? "$1" : "$1 ").$tags{$1}/eg;
    #$tagstr =~ s/\b(\d+)\b/tsk $1/;
    tagstr += autotags
    tagstr = re.sub(r'\s+', ' ', tagstr)
    a = util.annotime("{} {} {}".format(t, tagstr, comments), t)
    if (not tagstr) or\
        (not settings.enforcenums or re.search(r'\b(\d+|non|afk)\b', tagstr)):
        # if enforcenums is enabled, requires a digit or "non" or "afk" to end
        break

print(a)
logger.log(a)

# Send your TagTime log to Beeminder
#   (maybe should do this after retro pings too but launch.pl would do that).
if settings.beeminder and resp:
    print(util.divider(" sending your tagtime data to beeminder "))
    for key in settings.beeminder:
        print(key)
        bm(key)
    if eflag:
        print('{}, press enter to dismiss...'.format(util.splur(eflag, 'error')))
        tmp = input()


