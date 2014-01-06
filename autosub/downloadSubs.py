# Autosub downloadSubs.py - https://code.google.com/p/autosub-bootstrapbill/
#
# The Autosub downloadSubs module
# Scrapers are used for websites:
# Podnapisi.net, Subscene.com, Undertexter.se, SubSeeker's Mirror of BD
# and addic7ed.com
#
import logging

from bs4 import BeautifulSoup
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

log = logging.getLogger('thelogger')


# Settings
log = logging.getLogger('thelogger')


def getSoup(url):
    try:
        api = autosub.Helpers.API(url)
        soup = BeautifulSoup(api.resp.read())
        api.close()
        return soup
    except:
        log.error("getSoup: The server returned an error for request %s" % url)
        return False   

def unzip(url):
    # returns a file-like StringIO object    
    try:
        api = autosub.Helpers.API(url)
        tmpfile = StringIO(api.resp.read())
    except:
        log.debug("unzip: Zip file at %s couldn't be retrieved" % url)
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
            log.debug("unzip: Retrieving zip file for %s was succesful" % url )
            return subtitleFile
        else: 
            log.debug("unzip: No subtitle files was found in the zip archive for %s" % url)
            log.debug("unzip: Subtitle with different extention than .srt?")
            return None  
    

def openSubtitles(subSeekerLink):
    openSubLink = 'http://www.opensubtitles.org/subtitleserve/sub/' 
   
    try:
        soup = getSoup(subSeekerLink)
        tag = soup.find('iframe', src=True)
    except:
        log.error("openSubtitles: Failed to extract download link using SubtitleSeeker's link")        
        return None
    
    try:
        link = tag['src'].strip('/')    
        soup = getSoup(link)
        msgError = soup.find('div', class_='msg error')
    except:
        return None
    
    if not msgError:  
        try:      
            openID = link.split('/')[4].encode('utf8')
        except:
            log.error("openSubtitles: Something went with parsing the downloadlink")        
            return None
            
    else:   
        log.debug("openSubtitles: Original link %s is dead. Trying to find alternative in error message" % link)        
        pattern = re.compile('http://www.opensubtitles.org/.*/subtitles/(\d*)/', re.IGNORECASE)
        match = re.search(pattern, msgError.text)
        if match:
            openID = match.group(1)
            log.debug("openSubtitles: Alternative link found: %s" % link)  
        else:
            return None
    
    zipUrl = urljoin(openSubLink, openID.encode('utf8'))
    subtitleFile = unzip(zipUrl)
    return subtitleFile

    
def undertexter(subSeekerLink):
    engSub = 'http://www.engsub.net/getsub.php?id='    

    try:
        soup = getSoup(subSeekerLink)
        tag = soup.find('iframe', src=True)
        link = tag['src'].strip('/')     
    except:
        log.error("Undertexter: Failed to extract download link using SubtitleSeekers's link")        
        return None       
       
    try:
        zipUrl = engSub + link.split('/')[3].encode('utf8')
    except:
        log.error("Undertexter: Something went with parsing the downloadlink")        
        return None    

    subtitleFile = unzip(zipUrl)
    return subtitleFile
    

def podnapisi(subSeekerLink):
    baseLink = 'http://www.podnapisi.net/'    
    
    try:
        soup = getSoup(subSeekerLink)    
        linkToPodnapisi = soup.select('p > a[href]')[0]['href'].strip('/')
    except:
        log.error("Podnapisi: Failed to find the redirect link using SubtitleSeekers's link")        
        return None
    
    try:
        soup = getSoup(linkToPodnapisi)
        downloadTag = soup.select('a.button.big.download')[0]
    except:
        log.error("Podnapisi: Failed to find the download link on Podnapisi.net")        
        return None
    
    downloadLink = downloadTag['href'].strip('/')
    zipUrl = urljoin(baseLink,downloadLink.encode('utf8'))
    subtitleFile = unzip(zipUrl)
    return subtitleFile


def subscene(subSeekerLink):
    baseLink = 'http://subscene.com/'
    
    try:
        soup = getSoup(subSeekerLink)
        linkToSubscene = soup.select('p > a[href]')[0]['href'].strip('/')
    except:
        log.error("Subscene: Failed to find the redirect link using SubtitleSeekers's link")        
        return None
    
    try:
        soup = getSoup(linkToSubscene)
        downloadLink = soup.select('div.download > a[href]')[0]['href'].strip('/')
    except:
        log.error("Subscene: Failed to find the download link on Subscene.com")        
        return None
    
    zipUrl = urljoin(baseLink,downloadLink.encode('utf8'))
    subtitleFile = unzip(zipUrl)
    return subtitleFile

    
def bierdopje(subSeekerLink):    
    
    try:
        soup = getSoup(subSeekerLink)
        downloadLink = soup.select('p > a[href]')[0]['href'].strip('/')
    except:
        log.error("Mirror Bierdopje: Something went wrong while retrieving download link")
        return None    
    try:
        bierdopjeapi = autosub.Helpers.API(downloadLink)
        subtitleFile = StringIO(bierdopjeapi.resp.read())            
    except:
        log.debug("Mirror Bierdopje: Subtitle file at %s couldn't be retrieved" % downloadLink)
        return None   
    return subtitleFile
                

def addic7ed(downloadDict, imdb_id):    

    # Info about episode file
    title = downloadDict['title']
    season = downloadDict['season']
    episode = downloadDict['episode']    
    source = downloadDict['source']
    quality = downloadDict['quality']
    codec = downloadDict['codec']
    language = downloadDict['downlang']
    rlsgrp = downloadDict['releasegrp']
    
        
    a7ID = autosub.Helpers.geta7id(title, imdb_id)
    
    if not a7ID:     
        return (None, None)
    
    params = {'show_id': a7ID, 'season': season}
    soup = autosub.ADDIC7EDAPI.get('/show/{show_id}&season={season}'.format(**params))
    if not soup:
        return (None,None)
    
    versions = []
    for row in soup('tr', class_='epeven completed'):
        releaseInfo = {}
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
        
        # Retun is a list of possible releases that match
        versionDicts = autosub.Addic7ed.ReconstructRelease(details, HD, downloadUrl, hearingImpaired)
        if not versionDicts:
            continue

        versions.extend(versionDicts)
        
    if not versions:
        return (None, None)        
    
    scoreList = []        
    for releaseDict in versions: 
        score = autosub.Helpers.scoreMatch(releaseDict, releaseDict['a7'], quality, rlsgrp, source, codec)
        scoreList.append([releaseDict['a7'], score, releaseDict['url'], releaseDict['HI'] ])
            
    sortedScoreList = sorted(scoreList, key=lambda ind:ind[1], reverse=True)   

    FallBackDownload = None    
    for hit in sortedScoreList:
        originalVersion = hit[0]
        score = hit[1]
        downloadLink = hit[2]
        HI = hit[3]
        if score < autosub.MINMATCHSCORE:
            break
        if HI:
            if not FallBackDownload:
                FallBackDownload = hit[:]
            continue                
        #First try to get non-HI version

        try:
            subtitleFile = autosub.ADDIC7EDAPI.download(downloadLink)            
            releaseInfo = autosub.Addic7ed.makeReleaseName(originalVersion, title, season, episode)
            if subtitleFile:
                autosub.DOWNLOADS_A7 += 1
                return StringIO(subtitleFile), releaseInfo
            return subtitleFile, releaseInfo
        except:
            log.debug("downloadSubs.addic7ed: Trying to download next hit")
            continue
    
    # If only HI version is present, download this one instead
    if FallBackDownload:
        originalVersion = FallBackDownload[0]
        downloadLink = FallBackDownload[2]
        log.debug("downloadSubs.addic7ed: Trying to download HI subtitle as fall back")      

        try:            
            subtitleFile = autosub.ADDIC7EDAPI.download(downloadLink)            
            releaseInfo = autosub.Addic7ed.makeReleaseName(originalVersion, title, season, episode, HI=True)
            if subtitleFile:
                autosub.DOWNLOADS_A7 += 1
                return StringIO(subtitleFile), releaseInfo
            return subtitleFile, releaseInfo
        except:
            log.debug("downloadSubs.addic7ed: Subtitle file at %s couldn't be retrieved" % downloadLink)
    
    
    log.debug("downloadSubs.addic7ed: No suitable subtitle was found on Addic7ed.com")
    log.debug("downloadSubs.addic7ed: Try to find one on the other websites") 
    return (None, None)  
          

def DownloadSub(downloadDict, allResults, a7Response, imdb_id):    
    
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
        
        a7Hit = False # When a7 hit is found

        language = downloadDict['downlang']   
        fileStringIO = None
        website = None
        release = None
 
        # First look in Addic7ed for a hit            
        if (autosub.ADDIC7EDLANG == language or autosub.ADDIC7EDLANG == 'Both') and a7Response:
            log.debug("downloadSubs: Going to Addic7ed.com to find subtitle %s" % destsrt)
            fileStringIO, release = addic7ed(downloadDict, imdb_id)
            if fileStringIO:
                website = 'addic7ed.com'
                log.debug("downloadSubs: Found subtitle on addic7ed.com")
                a7Hit = True
        
        if allResults:
            for result in allResults:   
                if a7Hit:
                    log.debug("downloadSubs: Skipping other results...")
                    break                           
                
                subSeekerLink = result[0]
                release = result[2]
                website = result[3]             
                
                log.debug("downloadSubs: Trying to download the following subtitle %s" % subSeekerLink)      

                #if website == 'opensubtitles.org':
                #    log.debug("downloadSubs: Scraper for Opensubtitles.org is chosen for subtitle %s" % destsrt)
                #    fileStringIO = openSubtitles(subSeekerLink)
                
                if website == 'undertexter.se':
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
                    log.debug("downloadSubs: Subtitle is downloading from %s" % website)      
                    break
            
                log.debug("downloadSubs: Trying to download another subtitle for this episode")
        
            
        if not fileStringIO:            
            log.debug("downloadSubs: No suitable subtitle was found")
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
        
                
        notify.notify(downloadDict['downlang'], destsrt, downloadDict["originalFileLocationOnDisk"])

        if autosub.POSTPROCESSCMD:
            postprocesscmdconstructed = autosub.POSTPROCESSCMD + ' "' + downloadDict["destinationFileLocationOnDisk"] + '" "' + downloadDict["originalFileLocationOnDisk"] + '" "' + downloadDict["downlang"] + '"'
            log.debug("downloadSubs: Postprocess: running %s" % postprocesscmdconstructed)
            log.info("downloadSubs: Running PostProcess")
            postprocessoutput, postprocesserr = autosub.Helpers.RunCmd(postprocesscmdconstructed)
            if postprocesserr:
                log.error("downloadSubs: PostProcess: %s" % postprocesserr)
                log.debug("downloadSubs: PostProcess Output:% s" % postprocessoutput)
        
        log.debug('downloadSubs: Finished for %s' % downloadDict["originalFileLocationOnDisk"])
        return True
    
    else:
        log.error("downloadSub: No locationOnDisk found at downloadItem, skipping")
        return False