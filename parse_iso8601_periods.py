# Parses durations for iso8601-specified periods
# See https://tools.ietf.org/html/rfc5545#section-3.3.6
import re
from datetime import timedelta

# Assumes input is valid
def parse( periodStr ):
    weeks =   re.search( '^P[^T]*?(\d+)W', periodStr, re.M )
    days =    re.search( '^P[^T]*?(\d+)D', periodStr, re.M )
    hours =   re.search( '^P.*T.*?(\d+)H', periodStr, re.M )
    minutes = re.search( '^P.*T.*?(\d+)M', periodStr, re.M )
    seconds = re.search( '^P.*T.*?(\d+)S', periodStr, re.M )

    weeks =   float( weeks.group( 1 ) )   if weeks   else 0
    days =    float( days.group( 1 ) )    if days    else 0
    hours =   float( hours.group( 1 ) )   if hours   else 0
    minutes = float( minutes.group( 1 ) ) if minutes else 0
    seconds = float( seconds.group( 1 ) ) if seconds else 0

    return timedelta( days, seconds, 0, 0, minutes, hours, weeks )
