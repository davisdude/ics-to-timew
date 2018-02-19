# Parses ICS files
#
# For brief specs, see https://www.kanzaki.com/docs/ical/, for detailed specs,
# see https://tools.ietf.org/html/rfc5545
# Assumes all input is valid
import re
import parse_iso8601_periods as isoPeriods

try:
    import dateutil.parser
    import dateutil.rrule
except ImportError:
    raise ImportError( ( 'Make sure you have the python2 dateutil package '
                         'installed' ) )

try:
    import pytz
except ImportError:
    raise ImportError( 'Make sure you have the python2 pytz package installed' )

def getEventMatch( eventStr, name, separator = ':' ):
    match = re.search( r'^' + name + separator + '(.*?)\s*$', eventStr, re.M )
    if match:
        return match.group( 1 )

def getRruleMatch( rruleStr, name ):
    match = re.search( r'' + name + '=(.*?)($|;)', rruleStr, re.M )
    if match:
        return match.group( 1 )

def standardizeDatetime( timeStr, timezone ):
    if not timeStr:
        return None

    specialFormat = re.search( r'^(TZID=|VALUE=DATE).*?:(.*?)\s*$', timeStr, re.M )

    if specialFormat:
        timeStr = specialFormat.group( 2 )

    # Handles dates input as zulu time
    # Datetime objects must be naive for use by rrules
    # (see https://github.com/dateutil/dateutil/issues/102)
    if timeStr[-1:] == 'Z':
        timeStr = timeStr[:-1]
        return pytz.utc.localize( dateutil.parser.parse( timeStr ) )\
                .astimezone( timezone ).replace( tzinfo = None )

    return dateutil.parser.parse( timeStr )

def datetimeToZulu( datetime, timezone ):
    if not datetime:
        return None
    return timezone.normalize( timezone.localize( datetime ) )\
            .astimezone( pytz.utc ).strftime( '%Y%m%dT%H%M%SZ' )

dateutil_ids = {
    'YEARLY':   0,
    'MONTHLY':  1,
    'WEEKLY':   2,
    'DAILY':    3,
    'HOURLY':   4,
    'MINUTELY': 5,
    'SECONDLY': 6,

    'MO': 0,
    'TU': 1,
    'WE': 2,
    'TH': 3,
    'FR': 4,
    'SA': 5,
    'SU': 6,
}

def getDateutilId( obj ):
    if not obj:
        return None
    return dateutil_ids[obj]

def getDateutilIds( objs ):
    if not objs:
        return None

    ids = []
    match = re.compile( '([^,]+?)(?=,|$)', re.M )
    for obj in re.findall( match, objs ):
        ids.append( getDateutilId( obj ) )

    return tuple( ids )

class RepeatedEvent:
    def __init__( self, ruleStr, event ):
        if not ruleStr:
            self.until = None
            self.count = None
            self.rule = None
            return None

        self.freq =       getRruleMatch( ruleStr, 'FREQ' )
        self.until =      getRruleMatch( ruleStr, 'UNTIL' )
        self.count =      getRruleMatch( ruleStr, 'COUNT' )

        self.interval =   getRruleMatch( ruleStr, 'INTERVAL' ) or 1
        self.bysecond =   getRruleMatch( ruleStr, 'BYSECOND' )
        self.byminute =   getRruleMatch( ruleStr, 'BYMINUTE' )
        self.byhour =     getRruleMatch( ruleStr, 'BYHOUR' )
        self.byday =      getRruleMatch( ruleStr, 'BYDAY' )
        self.bymonthday = getRruleMatch( ruleStr, 'BYMONTHDAY' )
        self.byyearday =  getRruleMatch( ruleStr, 'BYYEARDAY' )
        self.byweekno =   getRruleMatch( ruleStr, 'BYWEEKNO' )
        self.bymonth =    getRruleMatch( ruleStr, 'BYMONTH' )
        self.bysetpos =   getRruleMatch( ruleStr, 'BYMONTH' )
        self.wkst =       getRruleMatch( ruleStr, 'WKST' ) or 'MO'

        self.count = int( self.count ) if self.count else None

        # timezone shouldn't be needed since UNTIL must be in UTC (spec pg. 41)
        self.datetime_until  = standardizeDatetime( self.until, pytz.utc )

        self.rule = dateutil.rrule.rrule( getDateutilId( self.freq ),
            dtstart =    event.datetime_dtstart,
            interval =   self.interval,
            wkst =       getDateutilId( self.wkst ),
            count =      self.count,
            until =      self.datetime_until,
            bysetpos =   getDateutilIds( self.bysetpos ),
            bymonth =    getDateutilIds( self.bymonth ),
            bymonthday = getDateutilIds( self.bymonthday ),
            byyearday =  getDateutilIds( self.byyearday ),
            byweekno =   getDateutilId( self.byweekno ),
            byweekday =  getDateutilIds( self.byday ),
            byhour =     getDateutilIds( self.byhour ),
            byminute =   getDateutilIds( self.byminute ),
            bysecond =   getDateutilIds( self.bysecond ),
        )

        # Standardizes all rrules to use UNTIL if applicable
        if not self.until and self.count:
            self.datetime_until = list( self.rule )[-1]

        self.formatted_until = datetimeToZulu( self.datetime_until, pytz.utc )

    def isForever( self ):
        if self.until or self.count:
            return False
        return True

class Event:
    def __init__( self, eventStr, parent ):
        self.summary =  getEventMatch( eventStr, 'SUMMARY' ).replace( '"', '\'' )
        self.dtstart =  getEventMatch( eventStr, 'DTSTART', '[:;]' )
        self.dtend =    getEventMatch( eventStr, 'DTEND',   '[:;]' )
        self.duration = getEventMatch( eventStr, 'DURATION' )
        self.rrule =    getEventMatch( eventStr, 'RRULE' )
        self.exrule =   getEventMatch( eventStr, 'EXRULE' )

        self.timezone = pytz.timezone( 
                getEventMatch( eventStr, 'DTSTART;TZID=(.*?)' )\
                or parent.defaultTimezone
        )

        self.exdate = []
        exdatePattern = re.compile( r'^EXDATE[;:](.*?)\s*$', re.S | re.M )
        for exdate in exdatePattern.findall( eventStr ):
            self.exdate.append( standardizeDatetime( exdate, self.timezone ) )

        self.datetime_dtstart =  standardizeDatetime( self.dtstart, self.timezone )
        self.datetime_duration = isoPeriods.parse( self.duration or '' )

        # Standardizes events to all use dtend
        if self.dtend:
            self.datetime_dtend = standardizeDatetime( self.dtend, self.timezone )
        elif self.duration:
            self.datetime_dtend = self.datetime_dtstart + self.datetime_duration

        self.datetime_duratin = None
        if self.dtend:
            self.datetime_duration = self.datetime_dtend - self.datetime_dtstart

        self.formatted_dtstart = datetimeToZulu( self.datetime_dtstart, self.timezone )
        self.formatted_dtend =   datetimeToZulu( self.datetime_dtend, self.timezone )

        # Account for repeated events
        # NOTE: In a future version of dateutil, there will be automatic parsing
        # of rrules with dateutil.rrule.rrulestr
        self.eventRuleset = dateutil.rrule.rruleset()
        self.repeatedEvent = RepeatedEvent( self.rrule, self )
        if self.repeatedEvent.rule:
            self.eventRuleset.rrule( self.repeatedEvent.rule )

        self.excludedEvent = RepeatedEvent( self.exrule, self )
        if self.excludedEvent.rule:
            self.eventRuleset.exrule( self.excludedEvent.rule )

        if self.exdate:
            for exdate in self.exdate:
                self.eventRuleset.exdate( exdate )

    def doesRepeat( self ):
        return not not self.rrule

    def getRepetitions( self ):
        if not self.doesRepeat():
            return None

    # See https://stackoverflow.com/a/30249034/2238176
    def isAllDay( self ):
        if re.search( r'^VALUE=DATE:', self.dtstart, re.M ):
            return True

        if not self.dtend and not self.duration:
            return True

        return False

veventPattern = re.compile( r'^BEGIN:VEVENT(.*?)END:VEVENT\s*$', re.S | re.M )

class Calendar:
    def __init__( self, calendarStr ):
        self.calname = getEventMatch( calendarStr, 'X-WR-CALNAME' ).replace( '"', '\'' )
        self.defaultTimezone = getEventMatch( calendarStr, 'X-WR-TIMEZONE' )
        self.events = []

        for eventStr in re.findall( veventPattern, calendarStr ):
            self.events.append( Event( eventStr, self ) )
