#
# Autosub Subtitleseeker.py - http://code.google.com/p/auto-sub/
#
# The Subtitleseeker API module
#

import urllib
import urllib2
import logging
import time

from xml.dom import minidom
from operator import itemgetter

import autosub.Helpers
from autosub.ProcessFilename import ProcessFilename
# Settings
log = logging.getLogger('thelogger')

class API:
    """
    One place to rule them all, a function that handels all the request to the server

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
        
def getShowidApi(showName):
    """
    Search for the IMDB ID by using the MyMovieAPI and the name of the show.
    Keyword arguments:
    showName -- Name of the show to search the showid for
    """
    
    api = autosub.IMDBAPI
    
    getShowIdUrl = "%sGetSeries.php?seriesname=%s" % (api, urllib.quote(showName.encode('utf8')))
    log.debug("getShowid: TvDB API request for %s: %s" % (showName, getShowIdUrl))
    if autosub.Helpers.checkAPICallsTvdb(use=True):
        try:
            tvdbapi = API(getShowIdUrl)
            dom = minidom.parse(tvdbapi.resp)
            tvdbapi.resp.close()
        except:
            log.error("getShowid: The server returned an error for request %s" % getShowIdUrl)
            return None
        
        if not dom or len(dom.getElementsByTagName('Series')) == 0:
            return None
        
        for sub in dom.getElementsByTagName('Series'):
            # Assume that first match is best, maybe adapt this in future
            try:
                showid = sub.getElementsByTagName('IMDB_ID')[0].firstChild.data
            except:
                log.error("getShowid: Error while retrieving the IMDB ID for %s." % showName)
                log.error("getShowid: Recommend to add the IMDB ID for %s manually for the time being." % showName)
                return None    
            # Remove trailing 'tt' from IMDB ID
            return showid[2:]
    else:
        log.error("API: out of api calls for MyMovieAPI")

def getSubLinks(showid, lang, releaseDetails):
    """
    Return all the hits that reach minmatchscore, sorted with the best at the top of the list
    Each element had the downloadlink, score, releasename, and source website)
    Matching is based on the provided release details.

    Keyword arguments:
    showid -- The IMDB id of the show
    lang -- Language of the wanted subtitle, Dutch or English
    releaseDetails -- Dict containing the quality, releasegrp, source season and episode.
    """
    
    api = autosub.API
    
    if showid == -1:
        return None    
    quality = None
    releasegrp = None
    source = None
    season = releaseDetails['season']
    episode = releaseDetails['episode']
    showName = releaseDetails['title']
    
    
    # Get the IMDB ID for the TV show    
    imdbId = autosub.Helpers.getShowid(showName)
    
    # this is the API search 
    getSubLinkUrl = "%s&imdb=%s&season=%s&episode=%s&language=%s" % (api, imdbId, season, episode, lang)
    log.info('this is the subseeker API request %s' % getSubLinkUrl)
    if autosub.Helpers.checkAPICallsSubSeeker(use=True):
        try:
            subseekerapi = API(getSubLinkUrl)
            dom = minidom.parse(subseekerapi.resp)
            subseekerapi.resp.close()
        except:
            log.error("getSubLink: The server returned an error for request %s" % getSubLinkUrl)
            return None
    else:
        log.error("API: out of api calls for SubtitleSeeker.com")
    
    if 'quality' in releaseDetails.keys(): quality = releaseDetails['quality']
    if 'releasegrp' in releaseDetails.keys(): releasegrp = releaseDetails['releasegrp']
    if 'source' in releaseDetails.keys(): source = releaseDetails['source']
    if 'codec' in releaseDetails.keys(): codec = releaseDetails['codec']

    if not dom or len(dom.getElementsByTagName('item')) == 0:
        return None

    scoredict = {}
    releasedict = {}
    websitedict = {}
    
    for sub in dom.getElementsByTagName('item'):
        release = sub.getElementsByTagName('release')[0].firstChild.data
        release = release.lower()
        # Remove the .srt extension some of the uploaders leave on the file
        if release.endswith(".srt"):
            release = release[:-4]
        website = sub.getElementsByTagName('site')[0].firstChild.data  
        website = website.lower() 
        
        SOURCEWEBSITES = []
        
        if autosub.USEPODNAPISI:
            SOURCEWEBSITES.append('podnapisi.net')
        
        if autosub.USESUBSCENE:
            SOURCEWEBSITES.append('subscene.com')
        
        if autosub.USEBIERDOPJEMIRROR:
            SOURCEWEBSITES.append('bierdopje.eu')
        
        if autosub.USEUNDERTEXTER:
            SOURCEWEBSITES.append('undertexter.se')
        
        if autosub.USEOPENSUBTITLES:
            SOURCEWEBSITES.append('opensubtitles.org')
                     
        if not website in SOURCEWEBSITES:
            continue       
        
        tmpDict = ProcessFilename(release, '')
        if not tmpDict:
            continue

        
        # Scoredict is a dictionary with a download link and its match score. This will be used to determine the best match (the highest matchscore)
        scoredict[sub.getElementsByTagName('url')[0].firstChild.data] = autosub.Helpers.scoreMatch(tmpDict, release, quality, releasegrp, source, codec)
    
        # Releasedict is a dictionary with the release name, used for the lastdownload database
        releasedict[sub.getElementsByTagName('url')[0].firstChild.data] = release
        
        # Websitedict is a dictionary with the download link coupled with the source website        
        websitedict[sub.getElementsByTagName('url')[0].firstChild.data] = website
        
    # Done comparing all the results, lets sort them and return the highest result
    # If there are results with the same score, the download links which comes first (alphabetically) will be returned
    # Also check if the result match the minimal score
    sortedscoredict = sorted(scoredict.items(), key=itemgetter(1), reverse=True)
    toDelete = []
    for index, item in enumerate(sortedscoredict):
        log.debug('getSubLink: checking minimal match score for %s. Minimal match score is: %s' %(item,autosub.MINMATCHSCORE))
        score = item[1]        
        link = item[0]
        if not score >= autosub.MINMATCHSCORE:
            log.debug('getSubLink: %s does not match the minimal match score' % link)
            toDelete.append(index)
    i = len(toDelete) - 1
    while i >= 0:
        log.debug("getSubLink: Removed item from the ScoreDict at index %s" % toDelete[i])
        sortedscoredict.pop(toDelete[i])
        i = i - 1
    if len(sortedscoredict) > 0:
        allResults = []
        j=0        
        while j < len(sortedscoredict):
            allResults.append(sortedscoredict[j] + (releasedict[sortedscoredict[j][0]], websitedict[sortedscoredict[j][0]]))
            j += 1
        return allResults
    
    return None
