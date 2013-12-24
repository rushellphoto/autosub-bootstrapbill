#
# Autosub Subtitleseeker.py - http://code.google.com/p/auto-sub/
#
# The Subtitleseeker API module
#

#import urllib
#import urllib2
import logging
import time

from xml.dom import minidom
from operator import itemgetter

import autosub.Helpers
from autosub.ProcessFilename import ProcessFilename
# Settings
log = logging.getLogger('thelogger')


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

    SOURCEWEBSITES = []
    
    # Addic7ed release are found and scored in downloadSubs itself
    # To get maximal sensitivity for this site        
    if autosub.PODNAPISILANG == lang or autosub.PODNAPISILANG == 'Both':
        SOURCEWEBSITES.append('podnapisi.net')
        
    if autosub.SUBSCENELANG == lang or autosub.SUBSCENELANG == 'Both':
        SOURCEWEBSITES.append('subscene.com')
        
    if autosub.BIERDOPJEMIRRORLANG == lang or autosub.BIERDOPJEMIRRORLANG == 'Both':
        SOURCEWEBSITES.append('bierdopje.eu')
        
    if autosub.UNDERTEXTERLANG == lang or autosub.UNDERTEXTERLANG == 'Both':
        SOURCEWEBSITES.append('undertexter.se')
    
    if autosub.OPENSUBTITLESLANG == lang or autosub.OPENSUBTITLESLANG == 'Both':
        SOURCEWEBSITES.append('opensubtitles.org')

    if len(SOURCEWEBSITES) == 0:
        return None
    
    api = autosub.API
    
    if showid == -1:
        return None    
    quality = None
    releasegrp = None
    source = None
    season = releaseDetails['season']
    episode = releaseDetails['episode']
    showName = releaseDetails['title']
    
    
    
    # this is the API search 
    getSubLinkUrl = "%s&imdb=%s&season=%s&episode=%s&language=%s" % (api, showid, season, episode, lang)
    log.info('Subtitleseeker: This is the subseeker API request %s' % getSubLinkUrl)
    if autosub.Helpers.checkAPICallsSubSeeker(use=True):
        try:
            subseekerapi = autosub.Helpers.API(getSubLinkUrl)
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
