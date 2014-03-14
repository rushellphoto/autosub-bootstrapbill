#
# Autosub getSubLinks.py - https://code.google.com/p/autosub-bootstrapbill/
#
# The getSubLinks module
#

import logging

from xml.dom import minidom
from operator import itemgetter

import autosub.Helpers
from autosub.ProcessFilename import ProcessFilename

# Settings
log = logging.getLogger('thelogger')


def SubtitleSeeker(showid, lang, releaseDetails, sourceWebsites):
    # Get the scored list for all SubtitleSeeker hits
    api = autosub.API

    if showid == -1:
        return None
    quality = None
    releasegrp = None
    source = None
    season = releaseDetails['season']
    episode = releaseDetails['episode']

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
        return None

    if 'quality' in releaseDetails.keys(): quality = releaseDetails['quality']
    if 'releasegrp' in releaseDetails.keys(): releasegrp = releaseDetails['releasegrp']
    if 'source' in releaseDetails.keys(): source = releaseDetails['source']
    if 'codec' in releaseDetails.keys(): codec = releaseDetails['codec']
    
    if not len(dom.getElementsByTagName('error')) == 0:
        for error in dom.getElementsByTagName('error'):
            try:
                errormsg = error.getElementsByTagName('msg')[0].firstChild.data
                log.error("getSubLink: Error found in API response: %s" % errormsg)
            except AttributeError:
                log.debug("getSubLink: Invalid msg tag in API response, unable to read error message.")
        return None

    if not dom or len(dom.getElementsByTagName('item')) == 0:
        return None

    scoreList = []

    for sub in dom.getElementsByTagName('item'):
        try:
            release = sub.getElementsByTagName('release')[0].firstChild.data
            release = release.lower()
            # Remove the .srt extension some of the uploaders leave on the file
            if release.endswith(".srt"):
                release = release[:-4]
        except AttributeError:
            log.debug("getSubLink: Invalid release tag in API response, skipping this item.")
            continue
        
        try:
            website = sub.getElementsByTagName('site')[0].firstChild.data
            website = website.lower()
        except AttributeError:
            log.debug("getSubLink: Invalid website tag in API response, skipping this item.")
            continue
        
        try:
            url = sub.getElementsByTagName('url')[0].firstChild.data
        except AttributeError:
            log.debug("getSubLink: Invalid url tag in API response, skipping this item.")
            continue
        
        tmpDict = ProcessFilename(release, '')
        
        if not website in sourceWebsites or not tmpDict:
            continue

        # ReleaseDict is a dictionary with the score, releasename and source website for the subtitle release
        releaseDict = {'score':None , 'releasename':release , 'url':url , 'website':website}
        releaseDict['score'] = autosub.Helpers.scoreMatch(tmpDict, release, quality, releasegrp, source, codec)

        scoreList.append(releaseDict)

    return scoreList

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

    sourceWebsites, scoreListSubSeeker  = [],[]
    if autosub.PODNAPISILANG == lang or autosub.PODNAPISILANG == 'Both':
        sourceWebsites.append('podnapisi.net')
    if autosub.SUBSCENELANG == lang or autosub.SUBSCENELANG == 'Both':
        sourceWebsites.append('subscene.com')
    if autosub.UNDERTEXTERLANG == lang or autosub.UNDERTEXTERLANG == 'Both':
        sourceWebsites.append('undertexter.se')
    if len(sourceWebsites) > 0:
        scoreListSubSeeker = SubtitleSeeker(showid, lang, releaseDetails, sourceWebsites)

    # Done comparing all the results, lets sort them and return the highest result
    # If there are results with the same score, the download links which comes last (anti-alphabetically) will be returned
    # Also check if the result match the minimal score
    try:
        sortedscorelist = sorted(scoreListSubSeeker, key=itemgetter('score', 'website'), reverse=True)
    except:
        return None

    toDelete = []
    for index, item in enumerate(sortedscorelist):
        name = item['releasename']
        log.debug('getSubLink: checking minimal match score for %s. Minimal match score is: %s' % (name, autosub.MINMATCHSCORE))
        score = item['score']
        if not score >= autosub.MINMATCHSCORE:
            log.debug('getSubLink: %s does not match the minimal match score' % name)
            toDelete.append(index)
    i = len(toDelete) - 1
    while i >= 0:
        log.debug("getSubLink: Removed item from the ScoreDict at index %s" % toDelete[i])
        sortedscorelist.pop(toDelete[i])
        i -= 1

    if len(sortedscorelist) > 0:
        return sortedscorelist

    return None