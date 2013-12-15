# Autosub Db.py - http://code.google.com/p/auto-sub/
#
# The Autosub downloadSubs module
# Scrapers are used for websites:
# Podnapisi.net, Subscene.com, Undertexter.se, Opensubtitles.org
#
import logging

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

# Settings
log = logging.getLogger('thelogger')

def getHTML(url):
    html = urllib2.urlopen(url).read()
    return html
    
def getHTMLTags(url, tagSearch):
    try:
        resp = urllib2.urlopen(url)
        errorcode = resp.getcode()
    except urllib2.HTTPError, e:
        errorcode = e.getcode()
        log.error("downloadSubs.getHTMLTags: The server returned the error %s for request %s" % (errorcode, url))  
        return False       
    if errorcode == 200:
        log.debug("downloadSubs.downloadSubs.getHTMLTags: HTTP Code: 200: OK!")
            
    html = resp.read()
    link_pat = SoupStrainer(tagSearch)
    tags = BeautifulSoup(html, parseOnlyThese=link_pat)
    if len(tags) == 0:
        log.error("downloadSubs.getHTMLTags: No suitable HTML Tags were found")
        return False
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
    req = urllib2.Request(url)
    req.add_header("User-agent", autosub.USERAGENT)
    try:
        tmpfile = StringIO(urllib2.urlopen(req).read())
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
    # link is http://www.opensubtitles.org/subtitles/5318376/revolution-everyone-says-i-love-you-en
    link = getHTMLTagAttrib(subSeekerLink, 'iframe', 'src')            
    if link:
        html = getHTML(link)
        openID = None
        # capture dead links
        if not html.find("msg error") == -1:
            # get alternate link
            #log.debug("HTML: %s" % html)
            try:
                r = re.search('http://www.opensubtitles.org/en/subtitles/(\d*)/', html).group(1)
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
                if tag.has_key('href'):
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
        url = tag['href'].strip('/')
        # first link: to the episode subtitle page
        if re.match(urljoin(baseLink, 'subtitles'), url):
            linkToSubscene = url
            tags_second = getHTMLTags(linkToSubscene, 'a')
            if not tags_second or len(tags_second) == 0:
                return None
            for tag in tags_second:
                if tag.has_key('href'):
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
            
        for hit in allResults:            
            website = hit[3]
            subSeekerLink = hit[0]
            
            log.debug("downloadSubs: Trying to download the following subtitle %s" % subSeekerLink)            
        
            # Decide which scraper to use
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
                log.debug("downloadSubs: Trying to download another subtitle for this episode")
                continue
            
        
            #Lets first download the subtitle to a tempfile and then write it to the destination
            tmpfile = tempfile.TemporaryFile('w+b')
        
            if fileStringIO:
                try:
                    tmpfile.write(fileStringIO.getvalue())
                    tmpfile.write('\n') #If subtitle has some footer which doesn't have a line feed >.>
                    tmpfile.seek(0) #Return to the start of the file
                except:
                    log.error("downloadSubs: Error while downloading subtitle %s. Subtitle might be corrupt %s." % (destsrt, website))
                    log.debug("downloadSubs: Trying to download another subtitle for this episode")
                    continue
            else:
                log.debug("downloadSubs: Trying to download another subtitle for this episode")
                continue

            try:
                log.debug("downloadSubs: Trying to save the subtitle to the filesystem")
                open(destsrt, 'wb').write(tmpfile.read())
                tmpfile.close()
            except IOError:
                log.error("downloadSubs: Could not write subtitle file. Permission denied? Enough diskspace?")
                tmpfile.close()
                return False
        
            log.info("downloadSubs: DOWNLOADED: %s" % destsrt)
            
            downloadDict['subtitle'] = hit[2]
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
        
        log.debug("downloadSubs: There are no remaining hits to look at. Wait for next run to get a subtitle for this episode")
        
    else:
        log.error("downloadSub: No locationOnDisk found at downloadItem, skipping")
        return False
