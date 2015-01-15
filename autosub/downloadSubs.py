# Autosub downloadSubs.py - https://code.google.com/p/autosub-bootstrapbill/
#
# The Autosub downloadSubs module
# Scrapers are used for websites:
# Podnapisi.net, Subscene.com, Undertexter.se, OpenSubtitles
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
    log.debug("openSubtitles: Subseekerlink =  %s" % subSeekerLink)
    try:
        soup = getSoup(subSeekerLink)
        linkToOpensubtitles = soup.select('p > a[href]')[0]['href'].strip('/')
        log.debug("openSubtitles: SubSeek link to opensubtitles =  %s" % linkToOpensubtitles )
        soup = getSoup(linkToOpensubtitles)
    except:
        log.error("openSubtitles: Failed to extract download link using SubtitleSeeker's link")        
        return None
    try:
        soup = getSoup(linkToOpensubtitles)
        for link in soup.find_all('a','none'):
            downloadLink = link.get('href')
            if '/download/file/' in downloadLink :
                log.debug("openSubtitles: OpenSubtitles sub downloadlink = %s" % downloadLink )
                opensubtitlesapi = autosub.Helpers.API(downloadLink)
                subtitleFile = StringIO(opensubtitlesapi.resp.read())            
                return subtitleFile
        log.error("OpenSubtitles: Failed to find the download link on OpenSubtitles.org")
        return None
    except:
        log.error("OpenSubtitles: Failed to find the download link on OpenSubtitles.org")        
        return None
    return None
    
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
        log.error("Undertexter: Something went wrong with parsing the downloadlink")        
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

def addic7ed(url):
    subtitleFile = autosub.ADDIC7EDAPI.download(url)
    if subtitleFile:
        autosub.DOWNLOADS_A7 += 1
        log.debug("addic7ed: Your current Addic7ed download count is: %s" % autosub.DOWNLOADS_A7)
        return StringIO(subtitleFile)
    return None

def DownloadSub(allResults, a7Response, downloadItem):    
    
    log.debug("downloadSubs: Starting DownloadSub function")    
    
    if not 'destinationFileLocationOnDisk' in downloadItem.keys():
        log.error("downloadSub: No locationOnDisk found at downloadItem, skipping")
        return False
    
    log.debug("downloadSubs: Download dict seems ook. Dumping it for debug: %r" % downloadItem) 
    destsrt = downloadItem['destinationFileLocationOnDisk']
    destdir = os.path.split(destsrt)[0]
    if not os.path.exists(destdir):
        log.debug("checkSubs: no destination directory %s" %destdir)
        return False
    elif not os.path.lexists(destdir):
        log.debug("checkSubs: no destination directory %s" %destdir)
        return False        
    
    HIfallback = {}
    fileStringIO = None
        
    for result in allResults:   
        url = result['url']
        release = result['releasename']
        website = result['website']             
       
        log.debug("downloadSubs: Trying to download subtitle from %s using this link %s" % (website,url))      

        if website == 'undertexter.se':
            log.debug("downloadSubs: Scraper for Undertexter.se is chosen for subtitle %s" % destsrt)
            fileStringIO = undertexter(url) 
        elif website == 'subscene.com':    
            log.debug("downloadSubs: Scraper for Subscene.com is chosen for subtitle %s" % destsrt)
            fileStringIO = subscene(url)
        elif website == 'podnapisi.net':
            log.debug("downloadSubs: Scraper for Podnapisi.net is chosen for subtitle %s" % destsrt)
            fileStringIO = podnapisi(url)
        elif website == 'opensubtitles.org':
            log.debug("downloadSubs: Scraper for opensubtitles.org is chosen for subtitle %s" % destsrt)
            fileStringIO = openSubtitles(url)
            time.sleep(6)
        elif website == 'addic7ed.com' and a7Response:
            log.debug("downloadSubs: Scraper for Addic7ed.com is chosen for subtitle %s" % destsrt)
            if result['HI']:
                if not HIfallback:
                    log.debug("downloadSubs: Addic7ed HI version: store as fallback")
                    HIfallback = result            
                continue
            fileStringIO = addic7ed(url)   
        else:
            log.error("downloadSubs: %s is not recognized. Something went wrong!" % website)

        if fileStringIO:
            log.debug("downloadSubs: Subtitle is downloading from %s" % website)      
            break
   
        log.debug("downloadSubs: Trying to download another subtitle for this episode")
    
    
    if not fileStringIO:
        if HIfallback:
            log.debug("downloadSubs: Downloading HI subtitle as fallback")
            fileStringIO = addic7ed(url)
            release = HIfallback['releasename']
            website = HIfallback['website']
        else: return False
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

        
    downloadItem['subtitle'] = "%s downloaded from %s" % (release,website)
    downloadItem['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
    
    lastDown().setlastDown(dict = downloadItem)
    
    # Send notification        
    notify.notify(downloadItem['downlang'], destsrt, downloadItem["originalFileLocationOnDisk"], website)

    if autosub.POSTPROCESSCMD:
        postprocesscmdconstructed = autosub.POSTPROCESSCMD + ' "' + downloadItem["destinationFileLocationOnDisk"] + '" "' + downloadItem["originalFileLocationOnDisk"] + '" "' + downloadItem["downlang"] + '" "' + downloadItem["title"] + '" "' + downloadItem["season"] + '" "' + downloadItem["episode"] + '" '
        log.debug("downloadSubs: Postprocess: running %s" % postprocesscmdconstructed)
        log.info("downloadSubs: Running PostProcess")
        postprocessoutput, postprocesserr = autosub.Helpers.RunCmd(postprocesscmdconstructed)
        log.debug("downloadSubs: PostProcess Output:% s" % postprocessoutput)
        if postprocesserr:
            log.error("downloadSubs: PostProcess: %s" % postprocesserr)
            #log.debug("downloadSubs: PostProcess Output:% s" % postprocessoutput)
    
    log.debug('downloadSubs: Finished for %s' % downloadItem["originalFileLocationOnDisk"])
    return True