# Autosub downloadSubs.py - http://code.google.com/p/auto-sub/
#
# The Autosub downloadSubs module
# Scrapers are used for websites:
# Podnapisi.net, Subscene.com, Undertexter.se, Opensubtitles.org
#
import logging

from bs4 import BeautifulSoup, SoupStrainer, Doctype
from zipfile import ZipFile
from StringIO import StringIO
import re 
from urlparse import urljoin

import os
import time
import tempfile
import autosub

from autosub.Db import lastDown
import autosub.Addic7ed
import autosub.notify as notify
import autosub.Helpers
import autosub.Tvdb

log = logging.getLogger('thelogger')

#TODO: Remove DOWNLOADQUEUELOCK everywhere
#TODO: Remove DownloadSubs threath
# Think about: keep url hardcoded here or set __init__?

# Settings
log = logging.getLogger('thelogger')


def getHTMLTags(url, tagSearch):
    try:
        api = autosub.Helpers.API(url)
        html = api.resp.read()
        api.close()
    except:
        log.error("getHTMLTags: The server returned an error for request %s" % url)
        return False
    
    link_pat = SoupStrainer(tagSearch)
    tags = BeautifulSoup(html, parse_only=link_pat)
    
    if len(tags) == 0:
        log.error("downloadSubs.getHTMLTags: No suitable HTML Tags were found")
        return False    
    # Remove DOCTYPE header
    for tag in tags:
        if isinstance(tag, Doctype):
            tag.extract()
    return tags 

def getHTMLTagAttrib(url, tagToSearch, attrib):
    tags = getHTMLTags(url, tagToSearch)
    if not tags or len(tags) != 1:
        log.error("downloadSubs.getHTMLTagAttrib: More than one HTML tag %s was found for %s" % (tagToSearch, url))
        return None
    for tag in tags:
        url = tag[attrib].strip('/')
        return url    
        
def unzip(url):
    # returns a file-like StringIO object    
    try:
        api = autosub.Helpers.API(url)
        tmpfile = StringIO(api.resp.read())
    except:
        log.debug("downloadSubs.unzip: Zip file at %s couldn't be retrieved" % url)
        return None     
    try: 
        zipfile = ZipFile(tmpfile)
    except:
        log.debug("unzip: Expected a zip file but got error for link %s" % url)
        log.debug("unzip: %s is likely a dead link, this is known for opensubtitles.org" % url)
        return None

    nameList = zipfile.namelist()
    for name in nameList:
        # sometimes .nfo files are in the zip container
        tmpname = name.lower()
        if tmpname.endswith('srt'):
            subtitleFile = StringIO(zipfile.open(name).read())
            log.debug("downloadSubs.unzip: Retrieving zip file for %s was succesful" % url )
            return subtitleFile
        else: 
            log.debug("downloadSubs.unzip: No subtitle files was found in the zip archive for %s" % url)
            log.debug("downloadSubs.unzip: Subtitle with different extention than .srt?")
            return None  
    
# Add log info to the scrapers

def openSubtitles(subSeekerLink):
    openSubLink = 'http://www.opensubtitles.org/subtitleserve/sub/' 
    # link is http://www.opensubtitles.org//subtitles/5318376/revolution-everyone-says-i-love-you-en
    link = getHTMLTagAttrib(subSeekerLink, 'iframe', 'src')            
    if link:
        try:        
            openSubtitlesapi = autosub.Helpers.API(link)
            html = openSubtitlesapi.resp.read()
            openSubtitlesapi.close()
        except:
            log.error("downloadSubs.openSubtitles: The server returned an error for request %s" % link)
            return None     
         
        openID = None
        # capture dead links
        if not html.find("msg error") == -1:
            # get alternate link
            try:
                r = re.search('http://www.opensubtitles.org/en/subtitles/(\d*)/', html).group(1)
                if not r:
                    r = re.search('http://www.opensubtitles.org/nl/subtitles/(\d*)/', html).group(1)               
                if r:
                    openID = r
            except:
                return None
        else:
            openID = link.split('/')[4].encode('utf8')
        zipUrl = openSubLink + openID
        subtitleFile = unzip(zipUrl)
        return subtitleFile
    else:
        return None
    
def undertexter(subSeekerLink):
    # http://www.engsub.net/197187
    engSub = 'http://www.engsub.net/getsub.php?id='
    # link is http://www.engsub.net/197187
    link = getHTMLTagAttrib(subSeekerLink, 'iframe', 'src')        
    if link:    
        zipUrl = engSub + link.split('/')[3].encode('utf8')
        subtitleFile = unzip(zipUrl)
        return subtitleFile
    else:
        return None
    
def podnapisi(subSeekerLink):
    baseLink = 'http://www.podnapisi.net/'
    tags_first = getHTMLTags(subSeekerLink, 'a')
    if not tags_first or len(tags_first) == 0:
        return None
    for tag in tags_first:
        url = tag['href'].strip('/')
        # first link: to the episode subtitle page
        if re.match(urljoin(baseLink, 'ppodnapisi/podnapis/i'), url):
            linkToPodnapisi = url
            tags_second = getHTMLTags(linkToPodnapisi, 'a')
            if not tags_second or len(tags_second) == 0:
                return None
            for tag in tags_second:
                if tag.has_attr('href'):
                    url = tag['href'].strip('/')
                    # second link: download link
                    if re.search('ppodnapisi/download', url):
                        zipUrl = urljoin(baseLink,url)
                        subtitleFile = unzip(zipUrl)
                        return subtitleFile

            log.error("downloadSubs.Podnapisi: Something went wrong while retrieving download link")
            log.debug("downloadSubs.Podnapisi: No hrefs were found in the Podnapisi HTML page for %s" % subSeekerLink)
            return None
    log.error("downloadSubs.Podnapisi: Something went wrong while retrieving download link")
    log.debug("downloadSubs.Podnapisi: Couldnt find the Subseeker link to the Podnapisi page for %s" % subSeekerLink)
    return None
    
def subscene(subSeekerLink):
    baseLink = 'http://subscene.com/'
    tags_first = getHTMLTags(subSeekerLink, 'a')
    if not tags_first or len(tags_first) == 0:
        return None
    for tag in tags_first:
        if tag.has_attr('href'):
            url = tag['href'].strip('/')
            # first link: to the episode subtitle page
            if re.match(urljoin(baseLink, 'subtitles'), url):
                linkToSubscene = url
                tags_second = getHTMLTags(linkToSubscene, 'a')
                if not tags_second or len(tags_second) == 0:
                    return None
                for tag in tags_second:
                    if tag.has_attr('href'):
                        url = tag['href'].strip('/')
                        # second link: download link
                        if re.match('subtitle/download', url):
                            zipUrl = urljoin(baseLink, url)
                            subtitleFile = unzip(zipUrl)
                            return subtitleFile

                log.error("downloadSubs.Subscene: Something went wrong while retrieving download link")
                log.debug("downloadSubs.Subscene: No hrefs were found in the Subscene HTML page for %s" % subSeekerLink)
                return None
    log.error("downloadSubs.Subscene: Something went wrong while retrieving download link")
    log.debug("downloadSubs.Subscene: Couldnt find the Subseeker link to the Subscene page for %s" % subSeekerLink)
    return None
    
def bierdopje(subSeekerLink):
    '''
    The href embedded in the subSeekerLink automatically gives the srt file
    Convert this in FileIO object for compatibility
    '''
    baseLink = 'http://www.subtitleseeker.com/classes/'
    tags = getHTMLTags(subSeekerLink, 'a')
    if not tags or len(tags) == 0:
        return None
    for tag in tags:
        url = tag['href'].strip('/')
        if re.match(baseLink, url):            
            try:
                bierdopjeapi = autosub.Helpers.API(url)
                subtitleFile = StringIO(bierdopjeapi.resp.read())            
            except:
                log.debug("downloadSubs.bierdopje: Subtitle file at %s couldn't be retrieved" % url)
                return None   
            return subtitleFile
                
    log.error("downloadSubs.bierdopje: Something went wrong while retrieving download link")
    log.debug("downloadSubs.bierdopje: Couldnt find the Subseeker link to the Subscene page for %s" % subSeekerLink)
    return None            


def addic7ed(downloadDict):    

    # Info about episode file
    title = downloadDict['title']
    season = downloadDict['season']
    episode = downloadDict['episode']    
    source = downloadDict['source']
    quality = downloadDict['quality']
    codec = downloadDict['codec']
    language = downloadDict['downlang']
    rlsgrp = downloadDict['releasegrp']
    
    
    # Initiate the a7 API
    try:
        addic7edapi = autosub.Addic7ed.Addic7edAPI()
        apiresponse = addic7edapi.login(autosub.ADDIC7EDUSER, autosub.ADDIC7EDPASSWD)
    except:
        return (None,None)
    
    # Fetch a7 ID for show
    a7ID = autosub.Addic7ed.geta7ID(title)
    
    if not a7ID:     
        return (None, None)
    
    params = {'show_id': a7ID, 'season': season}
    soup = addic7edapi.get('/show/{show_id}&season={season}'.format(**params))
    if not soup:
        return (None,None)
     
    versions = []
    for row in soup('tr', class_='epeven completed'):
        releaseInfo = {}
        cells = row('td')
        # filter out HI versions        
        if bool(cells[6].string) == True:
            continue
        # filter on Completed, wanted language and episode
        if cells[5].string != 'Completed':
            continue       
        if not unicode(cells[3].string) == language:        
            continue
        if not unicode(cells[1].string) == episode and not unicode(cells[1].string) == unicode(int(episode)):
            continue
        
        # use ASCII codec
        # put in lower case
        details = unicode(cells[4].string).encode('utf-8')
        details = details.lower()
        HD = True if bool(cells[8].string) != None else False        
        versionDict = autosub.Addic7ed.ReconstructRelease(details, HD)
        if not versionDict:
            continue
        versionDict['url'] = cells[9].a['href'].encode('utf-8')
        versionDict['a7'] = details
        versions.append(versionDict)
        twinDict = autosub.Addic7ed.MakeTwinRelease(versionDict)
        if twinDict:
            versions.append(twinDict)

    if not versions:
        return (None, None)        
    
    scoreList = []        
    for releaseDict in versions: 
        score = autosub.Helpers.scoreMatch(releaseDict, releaseDict['a7'], quality, rlsgrp, source, codec)
        scoreList.append((releaseDict['a7'], score, releaseDict['url']))
            
    sortedScoreList = sorted(scoreList, key=lambda tup:tup[1], reverse=True)    
    for hit in sortedScoreList:
        originalVersion = hit[0]
        score = hit[1]
        downloadLink = hit[2]
        if score >= autosub.MINMATCHSCORE:
            try:
                subtitleFile = StringIO(addic7edapi.download(downloadLink))
                addic7edapi.logout()
                releaseInfo = autosub.Addic7ed.makeReleaseName(originalVersion, title, season, episode)
                return subtitleFile, releaseInfo
            except:
                log.error("downloadSubs.addic7ed: Subtitle file at %s couldn't be retrieved" % downloadLink)
                addic7edapi.logout()
                return (None, None)
        log.debug("downloadSubs.addic7ed: No suitable subtitle was found on Addic7ed.com")
        log.debug("downloadSubs.addic7ed: Try to find one on the other websites") 
        addic7edapi.logout()
        return (None, None)  
          

def DownloadSub(downloadDict, allResults):    

    log.debug("downloadSubs: Starting DownloadSub function")    

    if 'destinationFileLocationOnDisk' in downloadDict.keys():
        log.debug("downloadSubs: Download dict seems ook. Dumping it for debug: %r" % downloadDict) 
        destsrt = downloadDict['destinationFileLocationOnDisk']
        destdir = os.path.split(destsrt)[0] #make sure the download dest is there
        if not os.path.exists(destdir):
            log.debug("checkSubs: no destination directory %s" %destdir)
            return False
        elif not os.path.lexists(destdir):
            log.debug("checkSubs: no destination directory %s" %destdir)
            return False        
        
        skipOtherResults = False # When a7 hit is found

        language = downloadDict['downlang']        
        fileStringIO = None
        website = None
        release = None
 
        # First look in Addic7ed for a hit            
        if autosub.ADDIC7EDLANG == language or autosub.ADDIC7EDLANG == 'Both':
            # To avoid unnecessary a7 searching
            #if autosub.ADDIC7EDUSER and autosub.ADDIC7EDPASSWD:
                log.debug("downloadSubs: Going to Addic7ed.com to find subtitle %s" % destsrt)
                fileStringIO, release = addic7ed(downloadDict)
                if fileStringIO:
                    website = 'addic7ed.com'
                    log.debug("downloadSubs: Found subtitle on addic7ed.com")
                    skipOtherResults = True
        
        if allResults:
            for result in allResults:   
                if skipOtherResults:
                    log.debug("downloadSubs: Skipping other results...")
                    break                           
                
                subSeekerLink = result[0]
                release = result[2]
                website = result[3]             
                
                log.debug("downloadSubs: Trying to download the following subtitle %s" % subSeekerLink)      

                if website == 'opensubtitles.org':
                    log.debug("downloadSubs: Scraper for Opensubtitles.org is chosen for subtitle %s" % destsrt)
                    fileStringIO = openSubtitles(subSeekerLink)
                elif website == 'undertexter.se':
                    log.debug("downloadSubs: Scraper for Undertexter.se is chosen for subtitle %s" % destsrt)
                    fileStringIO = undertexter(subSeekerLink) 
                elif website == 'subscene.com':    
                    log.debug("downloadSubs: Scraper for Subscene.com is chosen for subtitle %s" % destsrt)
                    fileStringIO = subscene(subSeekerLink)
                elif website == 'podnapisi.net':
                    log.debug("downloadSubs: Scraper for Podnapisi.net is chosen for subtitle %s" % destsrt)
                    fileStringIO = podnapisi(subSeekerLink)
                elif website == 'bierdopje.eu':
                    log.debug("downloadSubs: Scraper for Bierdopjes Mirror is chosen for subtitle %s" % destsrt)
                    fileStringIO = bierdopje(subSeekerLink)
                else:
                    log.error("downloadSubs: check the SubtitleSeeker XML file. Have the website name changed for %s?" % website)
 
                if fileStringIO:
                    break
            
                log.debug("downloadSubs: Trying to download another subtitle for this episode")
                  
        
        else:
            log.debug("downloadSubs: No suitable results were found on the 5 sites using the SubSeeker API")
            log.debug("downloadSubs: Or only addic7ed.com is used for %s subtitles" % language)
            return False

            
        
        if not fileStringIO:            
            return False
        
        #Lets first download the subtitle to a tempfile and then write it to the destination
        tmpfile = tempfile.TemporaryFile('w+b')
            
        try:
            tmpfile.write(fileStringIO.getvalue())
            tmpfile.write('\n') #If subtitle has some footer which doesn't have a line feed >.>
            tmpfile.seek(0) #Return to the start of the file
        except:
            log.error("downloadSubs: Error while downloading subtitle %s. Subtitle might be corrupt %s." % (destsrt, website))

        try:
            log.debug("downloadSubs: Trying to save the subtitle to the filesystem")
            open(destsrt, 'wb').write(tmpfile.read())
            tmpfile.close()
        except IOError:
            log.error("downloadSubs: Could not write subtitle file. Permission denied? Enough diskspace?")
            tmpfile.close()
            return False
            
        log.info("downloadSubs: DOWNLOADED: %s" % destsrt)
            
        if website == 'bierdopje.eu':
            website = 'subtitleseekers mirror of bierdopje'

            
        downloadDict['subtitle'] = "%s downloaded from %s" % (release,website)
        downloadDict['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        lastDown().setlastDown(dict = downloadDict)
        
        
        if downloadDict['downlang'] == 'Dutch' and autosub.ENGLISHSUBDELETE == True:
            log.info("downloadsubs: Trying to delete English subtitle.")
            engfileremove = os.path.splitext(destsrt)[0] + u"." + autosub.SUBENG + u".srt"
            if os.path.exists(engfileremove):
                try:
                    os.remove(engfileremove)
                    log.info("downloadsubs: Removed English subtitle: %s" % engfileremove)
                except:
                    log.error("downloadsubs: Error while trying to remove the file.")
            else:
                log.info("downloadsubs: English subtitle not found.")
        
        notify.notify(downloadDict['downlang'], destsrt, downloadDict["originalFileLocationOnDisk"])

        if autosub.POSTPROCESSCMD:
            postprocesscmdconstructed = autosub.POSTPROCESSCMD + ' "' + downloadDict["destinationFileLocationOnDisk"] + '" "' + downloadDict["originalFileLocationOnDisk"] + '" "' + downloadDict["downlang"] + '"'
            log.debug("downloadSubs: Postprocess: running %s" % postprocesscmdconstructed)
            log.info("downloadSubs: Running PostProcess")
            postprocessoutput, postprocesserr = autosub.Helpers.RunCmd(postprocesscmdconstructed)
            if postprocesserr:
                log.error("downloadSubs: PostProcess: %s" % postprocesserr)
                log.debug("downloadSubs: PostProcess Output:% s" % postprocessoutput)
        
        log.debug('downloadSubs: ')
        return True
        
        
    else:
        log.error("downloadSub: No locationOnDisk found at downloadItem, skipping")
        return False
