# Autosub Db.py - http://code.google.com/p/auto-sub/
#
# The Autosub downloadSubs module
# Scrapers are used for websites:
# Podnapisi.net, Subscene.com, Undertexter.se, Opensubtitles.org
#
import logging

import urllib
import urllib2
from library.beautifulsoup import BeautifulSoup, SoupStrainer
from zipfile import ZipFile
from StringIO import StringIO
import re 
from urlparse import urljoin

import autosub
import os
import time
import tempfile

from autosub.Db import lastDown
import autosub.notify as notify

log = logging.getLogger('thelogger')

#TODO: Remove DOWNLOADQUEUELOCK everywhere
#TODO: Remove DownloadSubs threath

# Think about: keep url hardcoded here or set __init__?
# INFO: 4 current website return zip files, but I keep the unzip command
# in the scraper for future website scrapers without zip
# TODO: add log. to self written part

# Settings
log = logging.getLogger('thelogger')

def printHTML(url):
    html = urllib2.urlopen(url).read()
    print html
    
def getHTMLTags(url, tagSearch):
    try:
         resp = urllib2.urlopen(url)
         errorcode = resp.getcode()
    except urllib2.HTTPError, e:
         errorcode = e.getcode()
    if errorcode == 200:
        log.debug("downloadSubs.getHTMLTags: HTTP Code: 200: OK!")
    
    html = resp.read()
    link_pat = SoupStrainer(tagSearch)
    tags = BeautifulSoup(html, parseOnlyThese=link_pat)
    if len(tags) == 0:
        log.error("downloadSubs.getHTMLTags: No suitable HTML Tags were found")
        return False
    return tags 

def getHTMLTagAttrib(url, tagToSearch, attrib):
    tags = getHTMLTags(url, tagToSearch)
    if len(tags) != 1:
        log.error("downloadSubs.getHTMLTagAttrib: More than one HTML tag %s was found for %s" % (tagToSearch, url))
        return False
    for tag in tags:
        url = tag[attrib].strip('/')
        return url
        
def unzip(url):
    # returns a file-like StringIO object
    req = urllib2.Request(url)
    req.add_header("User-agent", autosub.USERAGENT)
    try:
        tmpfile = StringIO(urllib2.urlopen(req).read())
    except:
        log.error("downloadSubs.unzip: Zip file at %s couldn't be retrieve" % url)    
    zipfile = ZipFile(tmpfile)
    nameList = zipfile.namelist()
    for name in nameList:
        # sometimes .nfo files are in the zip container
        if name.endswith('.srt'):
            file = StringIO(zipfile.open(name).read())
            log.debug("downloadSubs.unzip: Retrieving zip file for %s was succesful" % url )
            return file
        else: 
            log.error("downloadSubs.unzip: No subtitle files was found in the zip archive for %s" % url)
            log.error("downloadSubs.unzip: Subtitle with different extention than .srt?")
            return None  
    
# Add log info to the scrapers

def openSubtitles(subSeekerLink):
    openSubLink = 'http://www.opensubtitles.org/subtitleserve/sub/' 
    # link is http://www.opensubtitles.org/subtitles/5318376/revolution-everyone-says-i-love-you-en
    link = getHTMLTagAttrib(subSeekerLink, 'iframe', 'src')            
    zipUrl = openSubLink + link.split('/')[4].encode('utf8')
    subtitleFile = unzip(zipUrl)
    return subtitleFile
    
def undertexter(subSeekerLink):
    # http://www.engsub.net/197187
    engSub = 'http://www.engsub.net/getsub.php?id='
    # link is http://www.engsub.net/197187
    link = getHTMLTagAttrib(subSeekerLink, 'iframe', 'src')        
    zipUrl = engSub + link.split('/')[3].encode('utf8')
    subtitleFile = unzip(zipUrl)
    return subtitleFile
    
def podnapisi(subSeekerLink):
    baseLink = 'http://www.podnapisi.net/'
    tags_first = getHTMLTags(subSeekerLink, 'a')
    for tag in tags_first:
        url = tag['href'].strip('/')
        # first link: to the episode subtitle page
        if re.match(urljoin(baseLink, 'ppodnapisi/podnapis/i'), url):
            linkToPodnapisi = url
            tags_second = getHTMLTags(linkToPodnapisi, 'a')
            for tag in tags_second:
                if tag.has_key('href'):
                    url = tag['href'].strip('/')
                    # second link: download link
                    if re.search('ppodnapisi/download', url):
                        zipUrl = urljoin(baseLink,url)
                        subtitleFile = unzip(zipUrl)
                        return subtitleFile 
    
def subscene(subSeekerLink):
    baseLink = 'http://subscene.com/'
    tags_first = getHTMLTags(subSeekerLink, 'a')
    for tag in tags_first:
        url = tag['href'].strip('/')
        # first link: to the episode subtitle page
        if re.match(urljoin(baseLink, 'subtitles'), url):
            linkToSubscene = url
            tags_second = getHTMLTags(linkToSubscene, 'a')
            for tag in tags_second:
                if tag.has_key('href'):
                    url = tag['href'].strip('/')
                    # second link: download link
                    if re.match('subtitle/download', url):
                        zipUrl = urljoin(baseLink, url)
                        subtitleFile = unzip(zipUrl)
                        return subtitleFile

def DownloadSub(downloadDict):
    
    log.debug("downloadSubs: Starting DownloadSub function")
    
    if 'destinationFileLocationOnDisk' in downloadDict.keys() and 'downloadLink' in downloadDict.keys():
        log.debug("downloadSubs: Download dict seems ook. Dumping it for debug: %r" % downloadDict) 
        destsrt = downloadDict['destinationFileLocationOnDisk']
        website = downloadDict['website']
        subSeekerLink = downloadDict['downloadLink']        
        
        log.debug("downloadSubs: Trying to download the following subtitle %s" % subSeekerLink)
        
        destdir = os.path.split(destsrt)[0] #make sure the download dest is there
        if not os.path.exists(destdir):
            log.debug("checkSubs: no destination directory %s" %destdir)
            return False
        elif not os.path.lexists(destdir):
            log.debug("checkSubs: no destination directory %s" %destdir)
            return False        
        
        #Decide which scraper to use
        # Return a fileStringIO object 
        log.info('website is %s' % website) 
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
        else:
            log.error("downloadSubs: No scraper could be selected")
            log.debug("downloadSubs: check the SubtitleSeeker XML file. Have the website names changed?")
            return False
            
        
        #Lets first download the subtitle to a tempfile and then write it to the destination
        tmpfile = tempfile.TemporaryFile('w+b')
        
        try:
            tmpfile.write(fileStringIO.getvalue())
            tmpfile.write('\n') #If subtitle has some footer which doesn't have a line feed >.>
        except:
            log.error("downloadSubs: Error while downloading subtitle %s. Subtitle might be corrupt %s." % (destsrt, website))
            return False
        
       
        tmpfile.seek(0) #Return to the start of the file
        
        try:
            log.debug("downloadSubs: Trying to save the subtitle to the filesystem")
            open(destsrt, 'wb').write(tmpfile.read())
            tmpfile.close()
        except IOError:
            log.error("downloadSubs: Could not write subtitle file. Permission denied? Enough diskspace?")
            tmpfile.close()
            return False
        
        log.info("downloadSubs: DOWNLOADED: %s" % destsrt)
        
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
            postprocesscmdconstructed = autosub.POSTPROCESSCMD + ' "' + downloadDict["destinationFileLocationOnDisk"] + '" "' + downloadDict["originalFileLocationOnDisk"] + '"'
            log.debug("downloadSubs: Postprocess: running %s" % postprocesscmdconstructed)
            log.info("downloadSubs: Running PostProcess")
            postprocessoutput, postprocesserr = autosub.Helpers.RunCmd(postprocesscmdconstructed)
            if postprocesserr:
                log.error("downloadSubs: PostProcess: %s" % postprocesserr)
            log.debug("downloadSubs: PostProcess Output:% s" % postprocessoutput)
        
        log.debug('downloadSubs: ')
        return True
        
    else:
        log.error("downloadSub: No downloadLink or locationOnDisk found at downloadItem, skipping")
        return False
