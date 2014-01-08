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
import autosub.Addic7ed

# Settings
log = logging.getLogger('thelogger')


def SubtitleSeeker(showid, lang, releaseDetails, sourceWebsites):
    # Get the scored list for all SubtitleSeeker hits
    api = autosub.API

    if int(showid) == -1:
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

    if 'quality' in releaseDetails.keys(): quality = releaseDetails['quality']
    if 'releasegrp' in releaseDetails.keys(): releasegrp = releaseDetails['releasegrp']
    if 'source' in releaseDetails.keys(): source = releaseDetails['source']
    if 'codec' in releaseDetails.keys(): codec = releaseDetails['codec']

    if not dom or len(dom.getElementsByTagName('item')) == 0:
        return None

    scoreList = []

    for sub in dom.getElementsByTagName('item'):
        release = sub.getElementsByTagName('release')[0].firstChild.data
        release = release.lower()
        # Remove the .srt extension some of the uploaders leave on the file
        if release.endswith(".srt"):
            release = release[:-4]
        website = sub.getElementsByTagName('site')[0].firstChild.data
        website = website.lower()
        url = sub.getElementsByTagName('url')[0].firstChild.data
        tmpDict = ProcessFilename(release, '')
        if not website in sourceWebsites or not tmpDict:
            continue

        # ReleaseDict is a dictionary with the score, releasename and source website for the subtitle release
        releaseDict = {'score':None , 'releasename':release , 'url':url , 'website':website}
        releaseDict['score'] = autosub.Helpers.scoreMatch(tmpDict, release, quality, releasegrp, source, codec)

        scoreList.append(releaseDict)

    return scoreList

def Addic7ed(imdb_id, language, releaseDetails):

    # Info about episode file
    if int(imdb_id) == -1:
        return None

    title = releaseDetails['title']
    season = releaseDetails['season']
    episode = releaseDetails['episode']
    if 'quality' in releaseDetails.keys(): quality = releaseDetails['quality']
    if 'releasegrp' in releaseDetails.keys(): releasegrp = releaseDetails['releasegrp']
    if 'source' in releaseDetails.keys(): source = releaseDetails['source']
    if 'codec' in releaseDetails.keys(): codec = releaseDetails['codec']
    #rlsgrp = downloadDict['releasegrp']

    a7ID = autosub.Helpers.geta7id(title, imdb_id)
    if not a7ID:
        return None

    params = {'show_id': a7ID, 'season': season}
    soup = autosub.ADDIC7EDAPI.get('/show/{show_id}&season={season}'.format(**params))
    if not soup:
        return None

    scoreList = []

    for row in soup('tr', class_='epeven completed'):
        cells = row('td')
        #Check if line is intact
        if not len(cells) == 11:
            continue
        # filter on Completed, wanted language and episode
        if cells[5].string != 'Completed':
            continue
        if not unicode(cells[3].string) == language:
            continue
        if not unicode(cells[1].string) == episode and not unicode(cells[1].string) == unicode(int(episode)):
            continue

        # use ASCII codec and put in lower case
        details = unicode(cells[4].string).encode('utf-8')
        details = details.lower()
        HD = True if bool(cells[8].string) != None else False
        downloadUrl = cells[9].a['href'].encode('utf-8')
        hearingImpaired = True if bool(cells[6].string) else False
        if hearingImpaired:
            releasename = autosub.Addic7ed.makeReleaseName(details, title, season, episode, HI=True)
        else:
            releasename = autosub.Addic7ed.makeReleaseName(details, title, season, episode)

        # Retun is a list of possible releases that match
        versionDicts = autosub.Addic7ed.ReconstructRelease(details, HD)
        if not versionDicts:
            continue

        for version in versionDicts:
            releaseDict = {'score':None , 'releasename':releasename, 'website':'addic7ed.com' , 'url':downloadUrl , 'HI':hearingImpaired}
            releaseDict['score'] = autosub.Helpers.scoreMatch(version, details, quality, releasegrp, source, codec)
            scoreList.append(releaseDict)

    return scoreList


def getSubLinks(showid, lang, releaseDetails, a7Response):
    """
    Return all the hits that reach minmatchscore, sorted with the best at the top of the list
    Each element had the downloadlink, score, releasename, and source website)
    Matching is based on the provided release details.

    Keyword arguments:
    showid -- The IMDB id of the show
    lang -- Language of the wanted subtitle, Dutch or English
    releaseDetails -- Dict containing the quality, releasegrp, source season and episode.
    """

    sourceWebsites, scoreListSubSeeker, scoreListAddic7ed, fullScoreList  = [],[],[],[]
    if autosub.PODNAPISILANG == lang or autosub.PODNAPISILANG == 'Both':
        sourceWebsites.append('podnapisi.net')
    if autosub.SUBSCENELANG == lang or autosub.SUBSCENELANG == 'Both':
        sourceWebsites.append('subscene.com')
    if autosub.BIERDOPJEMIRRORLANG == lang or autosub.BIERDOPJEMIRRORLANG == 'Both':
        sourceWebsites.append('bierdopje.eu')
    if autosub.UNDERTEXTERLANG == lang or autosub.UNDERTEXTERLANG == 'Both':
        sourceWebsites.append('undertexter.se')
    if len(sourceWebsites) > 0:
        scoreListSubSeeker = SubtitleSeeker(showid, lang, releaseDetails, sourceWebsites)

    if (autosub.ADDIC7EDLANG == lang or autosub.ADDIC7EDLANG == 'Both') and a7Response:
        scoreListAddic7ed = Addic7ed(showid, lang, releaseDetails)
        pass

    for list in [scoreListSubSeeker, scoreListAddic7ed]:
        if list: fullScoreList.extend(list)

    # Done comparing all the results, lets sort them and return the highest result
    # If there are results with the same score, the download links which comes last (anti-alphabetically) will be returned
    # Also check if the result match the minimal score
    sortedscorelist = sorted(fullScoreList, key=itemgetter('score', 'website'), reverse=True)

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