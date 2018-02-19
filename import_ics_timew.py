#!/usr/bin/env python2

import argparse
from datetime import datetime
import subprocess

import parse_ics

try:
    import dateutil
except ImportError:
    raise ImportError( ( 'Make sure you have the python2 dateutil package '
                         'installed' ) )
try:
    import pytz
except ImportError:
    raise ImportError( 'Make sure you have the python2 pytz package installed' )

#------------------------------------------------------------------------------
# Command line parameters
#------------------------------------------------------------------------------
argParser = argparse.ArgumentParser()
argParser.add_argument( '--output-directory', '-o', default='./' )
argParser.add_argument( 'args', nargs='+' )
parsedArgs = argParser.parse_args()

# Validates the file's existance
calendarFilename = parsedArgs.args[0]
try:
    calendarFile = open( calendarFilename, 'rb' )
except IOError:
    raise IOError( 'File %s is unreadable' % calendarFilename )

# Gets the tags passed
passedTagsStr = ' '.join( '"' + item + '"' for item in parsedArgs.args[1:] )

#------------------------------------------------------------------------------
# Misc. Functions
#------------------------------------------------------------------------------
def datetimeToZulu( datetime, timezone ):
    if not datetime:
        return None
    return timezone.normalize( timezone.localize( datetime ) )\
            .astimezone( pytz.utc ).strftime( '%Y%m%dT%H%M%SZ' )

def toTimewEntry( event, startTimeStr, endTimeStr, tags ):
    entry = subprocess.Popen(
            [ 'timew', 'track', startTimeStr, '-', endTimeStr, tags ],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
    )

    output, errors = entry.communicate()
    if entry.returncode != 0:
        print( 'Error tracking event %s from %s to %s: %s' % (
            event.summary,
            startTimeStr,
            endTimeStr,
            errors,
        ) )

#------------------------------------------------------------------------------
# Parse file
#------------------------------------------------------------------------------
calString = calendarFile.read()
cal = parse_ics.Calendar( calString )

for event in cal.events:
    if event.isAllDay():
        continue

    tags = '"' + cal.calname + '" "' + event.summary + '" ' + passedTagsStr
    if event.doesRepeat():
        # TODO: Handle infinite events
        # Idea: Create hook event that checks if date is past certain time
        # and populates calendar if true
        if not event.repeatedEvent.isForever():
            for date in list( event.eventRuleset ):
                dtstart = datetimeToZulu( date, event.timezone )
                dtend   = datetimeToZulu( date + event.datetime_duration, event.timezone )

                toTimewEntry( event, dtstart, dtend, tags )
        continue

    toTimewEntry( event, event.formatted_dtstart, event.formatted_dtend, tags )
