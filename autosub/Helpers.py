# Autosub Helpers.py - https://code.google.com/p/autosub-bootstrapbill/
#
# The Autosub helper functions
#

import logging
import re
import subprocess
from string import capwords
import time
import urllib2
import codecs
import os
from ast import literal_eval

from library import version
from autosub.version import autosubversion

import autosub
import Tvdb

from autosub.Db import idCache, a7idCache
from autosub.ID_lookup import a7IdDict
from autosub.Addic7ed import Addic7edAPI

# Settings
log = logging.getLogger('thelogger')

REGEXES = [
        re.compile("^((?P<title>.+?)[. _-]+)?s(?P<season>\d+)[x. _-]*e(?P<episode>\d+)(([. _-]*e|-)(?P<extra_ep_num>(?!(1080|720)[pi])\d+))*[. _-]*((?P<quality>(1080|720|SD))*[pi]*[. _-]*(?P<source>(hdtv|dvdrip|bdrip|blu[e]*ray|web[. _-]*dl))*[. _]*(?P<extra_info>.+?)((?<![. _-])-(?P<releasegrp>[^-]+))?)?$", re.IGNORECASE),
        re.compile("^((?P<title>.+?)[\[. _-]+)?(?P<season>\d+)x(?P<episode>\d+)(([. _-]*x|-)(?P<extra_ep_num>(?!(1080|720)[pi])\d+))*[. _-]*((?P<quality>(1080|720|SD))*[pi]*[. _-]*(?P<source>(hdtv|dvdrip|bdrip|blu[e]*ray|web[. _-]*dl))*[. _]*(?P<extra_info>.+?)((?<![. _-])-(?P<releasegrp>[^-]+))?)?$", re.IGNORECASE),
        re.compile("^(?P<title>.+?)[. _-]+(?P<season>\d{1,2})(?P<episode>\d{2})([. _-]*(?P<quality>(1080|720|SD))*[pi]*[. _-]*(?P<source>(hdtv|dvdrip|bdrip|blu[e]*ray|web[. _-]*dl))*[. _]*(?P<extra_info>.+?)((?<![. _-])-(?P<releasegrp>[^-]+))?)?$", re.IGNORECASE)
        ]
SOURCE_PARSER = re.compile("(hdtv|tv|dvdrip|dvd|bdrip|blu[e]*ray|web[. _-]*dl)", re.IGNORECASE)
QUALITY_PARSER = re.compile("(1080|720|HD|SD)" , re.IGNORECASE)
LOG_PARSER = re.compile('^((?P<date>\d{4}\-\d{2}\-\d{2})\ (?P<time>\d{2}:\d{2}:\d{2},\d{3}) (?P<loglevel>\w+))', re.IGNORECASE)

def RunCmd(cmd):
    process = subprocess.Popen(cmd,
                            shell = True,
                            stdin = subprocess.PIPE,
                            stdout = subprocess.PIPE,
                            stderr = subprocess.PIPE)
    shell = process.stdout.read()
    shellerr = process.stderr.read()
    process.wait()
    return shell, shellerr

def CheckVersion():
    '''
    CheckVersion
    
    Return values:
    0 Same version
    1 New version
    2 New (higher) release, same version
    3 New lower release, higher version
    4 Release lower, version lower
    '''
    
    # Check this because it's faulty
    try:
        req = urllib2.Request(autosub.VERSIONURL)
        req.add_header("User-agent", autosub.USERAGENT) 
        resp = urllib2.urlopen(req,None,autosub.TIMEOUT)
        response = resp.read()
        resp.close()
    except:
        log.error("checkVersion: The server returned an error for request %s" % autosub.VERSIONURL)
        return None
    try:
        version_online = response.split("'")[1]
    except:
        return None
    
    release = version_online.split(' ')[0]
    versionnumber = version_online.split(' ')[1]
    
    running_release = autosubversion.split(' ')[0]
    running_versionnumber = autosubversion.split(' ')[1]
    log.info("checkVersion: %s %s vs. %s %s" %(running_release, running_versionnumber, release, versionnumber))
    
    if release == running_release: #Alpha = Alpha
        if versionnumber > running_versionnumber: #0.5.6 > 0.5.5
            return 1
        else: #0.5.6 = 0.5.6
            return 0
    elif release > running_release: #Beta > Alpha
        if versionnumber == running_versionnumber: #0.5.5 = 0.5.5
            return 2
        elif versionnumber > running_versionnumber: #0.5.6 > 0.5.5
            return 4
    elif release < running_release: #Alpha < Beta
        if versionnumber > running_versionnumber: #0.5.6 > 0.5.5
            return 3        

def CleanSerieName(series_name):
    """Clean up series name by removing any . and _
    characters, along with any trailing hyphens.

    Is basically equivalent to replacing all _ and . with a
    space, but handles decimal numbers in string, for example:

    >>> cleanRegexedSeriesName("an.example.1.0.test")
    'an example 1.0 test'
    >>> cleanRegexedSeriesName("an_example_1.0_test")
    'an example 1.0 test'

    Stolen from dbr's tvnamer
    """
    try:
        series_name = re.sub("(\D)\.(?!\s)(\D)", "\\1 \\2", series_name)
        series_name = re.sub("(\d)\.(\d{4})", "\\1 \\2", series_name)  # if it ends in a year then don't keep the dot
        series_name = re.sub("(\D)\.(?!\s)", "\\1 ", series_name)
        series_name = re.sub("\.(?!\s)(\D)", " \\1", series_name)
        series_name = series_name.replace("_", " ")
        series_name = re.sub("-$", "", series_name)
        
        words = [x.strip() for x in series_name.split()]
        tempword=[]
        for word in words:
            if not word.isupper():
                word = capwords(word)
            tempword.append(word)
        new_series_name = " ".join(tempword)

        return new_series_name.strip()
    except TypeError:
        log.debug("CleanSerieName: There is no SerieName to clean")


def ReturnUpper(text):
    """
    Return the text converted to uppercase.
    When not possible return nothing.
    """
    try:
        text = text.upper()
        return text
    except:
        pass

def matchQuality(quality, item):
    if quality == u"SD":
        if re.search('720', item):
            log.debug("matchQuality: Quality SD did not match to %s" % item)
            return None
        elif re.search('1080', item):
            log.debug("matchQuality: Quality SD did not match to %s" % item)
            return None
        else:
            log.debug("matchQuality: Quality matched SD to %s" % item)
            return 1
    elif quality == u"1080p" and re.search('1080', item):
        log.debug("matchQuality: Quality is 1080 matched to %s" % item)
        return 1
    elif quality == u"720p" and re.search('720', item):
        log.debug("matchQuality: Quality is 720 matched to %s" % item)
        return 1


def scoreMatch(releasedict, release, quality, releasegrp, source, codec):
    """
    Return how high the match is. Currently 15 is the best match
    This function give the flexibility to change the most important attribute for matching or even give the user the possibility to set his own preference
    release is the filename as it is in the result from subtitleseeker
    If quality is matched, score increased with 4
    If releasegrp is matched, score is increased with 1
    If source is matched, score is increased with 8
    If releasegroup is matched, score is increased with 4
    """
    score = 0
    log.debug("scoreMatch: Giving a matchscore for: %r. Try to match it with Q: %r GRP: %r S: %r" % (releasedict, quality, releasegrp, source))
    
    releasesource = None
    releasequality = None
    releasereleasegrp = None
    releasecodec = None
    
    if 'source' in releasedict.keys(): releasesource = releasedict['source']
    if 'quality' in releasedict.keys(): releasequality = releasedict['quality']
    if 'releasegrp' in releasedict.keys(): releasereleasegrp = releasedict['releasegrp']
    if 'codec' in releasedict.keys(): releasecodec = releasedict['codec']
    
    if releasegrp and releasereleasegrp:
        if releasereleasegrp == releasegrp:
            score += 1
    if source and releasesource:
        if releasesource == source:
            score += 8
    if quality and releasequality:
        if quality == releasequality:
            score += 4
    if codec and releasecodec:
        if codec == releasecodec:
            score += 2
    
    if not releasedict:
        log.warning("scoreMatch: Something went wrong, ProcessFileName could not process the file, %s, please report this!" %release)
        log.info("scoreMatch: Falling back to old matching system, to make sure you get your subtitle!")
        if releasegrp:
            if (re.search(re.escape(releasegrp), release, re.IGNORECASE)):
                score += 1
        if source:
            if (re.search(re.escape(source), release, re.IGNORECASE)):
                score += 8
        if quality:
            if (matchQuality(re.escape(quality), release)):
                score += 4
        if codec:
            if (re.search(re.escape(codec), release, re.IGNORECASE)):
                score += 2
         
    log.debug("scoreMatch: MatchScore is %s" % str(score))
    return score


def Addic7edMapping(imdb_id):
    if imdb_id in autosub.USERADDIC7EDMAPPINGUPPER.keys():
        log.debug("nameMapping: found match in user's addic7edmapping for %s" % imdb_id)
        return autosub.USERADDIC7EDMAPPINGUPPER[imdb_id]

def nameMapping(showName):
    if showName.upper() in autosub.USERNAMEMAPPINGUPPER.keys():
        log.debug("nameMapping: found match in user's namemapping for %s" % showName)
        return autosub.USERNAMEMAPPINGUPPER[showName.upper()]
    elif showName.upper() in autosub.NAMEMAPPINGUPPER.keys():
        log.debug("nameMapping: found match for %s" % showName)
        return autosub.NAMEMAPPINGUPPER[showName.upper()]

def SkipShow(showName, season, episode):
    if showName.upper() in autosub.SKIPSHOWUPPER.keys():
        log.debug("SkipShow: Found %s in skipshow dictonary" % showName)
        for seasontmp in autosub.SKIPSHOWUPPER[showName.upper()]:
            # Skip entire TV show
            if seasontmp == '-1':
                log.debug("SkipShow: variable of %s is set to -1, skipping the complete Serie" % showName)
                return True
            try:
                toskip = literal_eval(seasontmp)
            except:
                log.error("SkipShow: %s is not a valid parameter, check your Skipshow settings" % seasontmp)
                continue
            # Skip specific season:
            if isinstance(toskip, int):
                if int(season) == toskip:
                    log.debug("SkipShow: Season %s matches variable of %s, skipping season" % (season, showName))
                    return True
            # Skip specific episode
            elif isinstance(toskip, float):
                seasontoskip = int(toskip)
                episodetoskip = int(round((toskip-seasontoskip) * 100))
                if int(season) == seasontoskip:
                    if episodetoskip == 0:
                        log.debug("SkipShow: Season %s matches variable of %s, skipping season" % (season, showName))
                        return True
                    elif int(episode) == episodetoskip:
                        format = season + 'x' + episode
                        log.debug("SkipShow: Episode %s matches variable of %s, skipping episode" % (format, showName))
                        return True


def checkAPICallsSubSeeker(use=False):
    """
    Checks if there are still API calls left
    Set true if a API call is being made.
    """
    currentime = time.time()
    lastrun  = autosub.APICALLSLASTRESET
    interval = autosub.APICALLSRESETINT
    
    if currentime - lastrun > interval:
        autosub.APICALLS_SUBSEEKER = autosub.APICALLSMAX_SUBSEEKER
        autosub.APICALLSLASTRESET = time.time()
    
    if autosub.APICALLS_SUBSEEKER > 0:
        if use==True:
            autosub.APICALLS_SUBSEEKER-=1
        return True
    else:
        return False
        
def checkAPICallsTvdb(use=False):
    """
    Checks if there are still API calls left
    Set true if a API call is being made.
    """
    currentime = time.time()
    lastrun  = autosub.APICALLSLASTRESET
    interval = autosub.APICALLSRESETINT
    
    if currentime - lastrun > interval:
        autosub.APICALLS_TVDB = autosub.APICALLSMAX_TVDB
        autosub.APICALLSLASTRESET = time.time()
    
    if autosub.APICALLS_TVDB > 0:
        if use==True:
            autosub.APICALLS_TVDB-=1
        return True
    else:
        return False

def getShowid(show_name):
    log.debug('getShowid: trying to get showid for %s' %show_name)
    show_id = nameMapping(show_name)
    if show_id:
        log.debug('getShowid: showid from namemapping %s' %show_id)
        return show_id
    
    show_id = idCache().getId(show_name)
    if show_id:
        log.debug('getShowid: showid from cache %s' %show_id)
        if int(show_id) == -1:
            log.error('getShowid: showid not found for %s' %show_name)
            return
        return show_id
    
    #do we have enough api calls?
    if checkAPICallsTvdb(use=False): 
        show_id = Tvdb.getShowidApi(show_name)
    else:
        log.warning("getShowid: Out of API calls")
        return None
    
    if show_id:
        log.debug('getShowid: showid from api %s' %show_id)
        idCache().setId(show_id, show_name)
        log.info('getShowid: %s added to cache with %s' %(show_name, show_id))
        
        return str(show_id)
    
    log.error('getShowid: showid not found for %s' %show_name)
    #idCache().setId(-1, show_name)
    
def geta7id(showTitle, imdb_id):
    
    #imdb_id = getShowid(showTitle)
    #imdb_id = str(imdb_id)

    log.debug('geta7id: trying to get addic7ed ID for show %s with IMDB ID %s' % (showTitle, imdb_id))
    
    # From user addic7ed mapping
    a7_id = Addic7edMapping(imdb_id)
    if a7_id:
        log.debug('geta7ID: showid from addic7edmapping %s' %a7_id)
        return a7_id

    # From lookup table
    if imdb_id in a7IdDict.keys():
        a7_id = a7IdDict[imdb_id]
        log.debug('geta7ID: showid from lookup table %s' % a7_id)
        return a7_id 
    
    
    # From cache
    a7_id = a7idCache().getId(imdb_id)
    if a7_id:
        log.debug('geta7id: addic7ed ID from cache %s' %a7_id)
        if int(a7_id) == -1:
            log.error('geta7id: addic7ed ID not found for %s' %showTitle)
            return
        return a7_id
    
    # From Addic7ed show overview page
    a7_id = Addic7edAPI().geta7ID(imdb_id, showTitle)
    if a7_id:
        log.debug('geta7id: addic7ed ID from Addic7ed show overview page %s' %a7_id)
        a7idCache().setId(a7_id, imdb_id)
        log.info('geta7id: %s added to cache with %s' %(a7_id, imdb_id))       
        return a7_id
    
    log.error('geta7id: addic7ed ID not found for %s' %showTitle)
    
    #a7idCache().setId(-1, imdb_id)
    

def DisplayLogFile(loglevel):
    maxLines = 500
    data = []
    if os.path.isfile(autosub.LOGFILE):
        f = codecs.open(autosub.LOGFILE, 'r', autosub.SYSENCODING)
        data = f.readlines()
        f.close()
    
    finalData = []
    
    numLines = 0
    
    for x in reversed(data):
        try:
            matches = LOG_PARSER.search(x)
            matchdic = matches.groupdict()
            if (matchdic['loglevel'] == loglevel.upper()) or (loglevel == ''):
                numLines += 1
                if numLines >= maxLines:
                    break
                finalData.append(x)
        except:
            continue
    result = "".join(finalData)
    return result

def ClearLogFile():
    if os.path.isfile(autosub.LOGFILE):
        try:
            open(autosub.LOGFILE, 'w').close()
            message = "Logfile has been cleared!"
        except IOError:
            message = "Logfile is currently being used by another process. Please try again later."
        return message

def DisplaySubtitle(subtitlefile):
    data = []
    if os.path.isfile(subtitlefile):
        f = codecs.open(subtitlefile, 'r', autosub.SYSENCODING)
        #This needs fixing, should prevent a crash for now on Linux based systems.
        try:
            data = f.readlines()
        except:
            data = "Invalid character found"
        f.close()
    
    finalData = []
    
    #Count total lines of file, so we can display the last 30 in correct order and not reversed.
    totalLines = 0
    for line in data:
        totalLines += 1
    
    if totalLines == 0:
        result = "This seems to be an invalid subtitle, it's empty."
        return result
    
    #Define startLine so we know when to start displaying the subtitle
    startLine = totalLines - 30
    
    if startLine <= 0:
        result = "This seems to be an invalid subtitle, it has less than 30 lines to preview."
        return result
    
    numLines = 0
    
    for x in data:       
        try:
            numLines += 1
            if numLines < startLine:
                continue
            if numLines >= totalLines:
                break
            finalData.append(x)
        except:
            continue
    result = "<br>".join(finalData)
    return result

def ConvertTimestamp(datestring):
    try:
        date_object = time.strptime(datestring, "%Y-%m-%d %H:%M:%S")
        message = "%02i-%02i-%i %02i:%02i:%02i " %(date_object[2], date_object[1], date_object[0], date_object[3], date_object[4], date_object[5])
    except ValueError:
        message = "Timestamp error"
    return message

def ConvertTimestampTable(datestring):
    #used for the sorted table
    date_object = time.strptime(datestring, "%Y-%m-%d %H:%M:%S")
    return "%04i%02i%02i%02i%02i%02i" %(date_object[0], date_object[1], date_object[2], date_object[3], date_object[4], date_object[5])

def CheckMobileDevice(req_useragent):
    for MUA in autosub.MOBILEUSERAGENTS:
        if MUA.lower() in req_useragent.lower():
            return True
    return False

# Thanks to: http://stackoverflow.com/questions/1088392/sorting-a-python-list-by-key-while-checking-for-string-or-float
def getAttr(name):
    def inner_func(o):
        try:
            rv = float(o[name])
        except ValueError:
            rv = o[name]
        return rv
    return inner_func
    

class API:
    """
    One place to rule them all, a function that handels all the request to the servers

    Keyword arguments:
    url - the URL that is requested
    
    """
    def __init__(self,url):
        self.errorcode = None        
        self.req = None
        self.req = urllib2.Request(url)
        self.req.add_header("User-agent", autosub.USERAGENT)
        self.connect()
        
    def connect(self):
        import socket
        socket.setdefaulttimeout(autosub.TIMEOUT)
        
        try:
            self.resp = urllib2.urlopen(self.req)
            self.errorcode = self.resp.getcode()
        except urllib2.HTTPError, e:
            self.errorcode = e.getcode()
        
        if self.errorcode == 200:
            log.debug("API: HTTP Code: 200: OK!")
        elif self.errorcode == 429:
            # don't know if this code is valid for subtitleseeker
            log.debug("API: HTTP Code: 429 You have exceeded your number of allowed requests for this period.")
            log.error("API: You have exceeded your number of allowed requests for this period. (1000 con/day))")
            log.warning("API: Forcing a 1 minute rest to relieve subtitleseeker.com. If you see this info more then once. Cleanup your wanted list!")
            time.sleep(54)
        elif self.errorcode == 503:
            log.debug("API: HTTP Code: 503 You have exceeded your number of allowed requests for this period (MyMovieApi).")
            log.error("API: You have exceeded your number of allowed requests for this period. (either 30 con/m or 2500 con/day))")
            log.warning("API: Forcing a 1 minute rest to relieve mymovieapi.com. If you see this info more then once. Cleanup your wanted list!")
            time.sleep(54)
        
        log.debug("API: Resting for 6 seconds to prevent 429 errors")
        time.sleep(6) #Max 0.5 connections each second
    
    def close(self):
        self.resp.close()