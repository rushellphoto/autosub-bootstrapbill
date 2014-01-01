# Autosub Db.py - http://code.google.com/p/auto-sub/
#
# The Autosub checkSub module
#

import logging
import os

# Autosub specific modules
import autosub.Subtitleseeker
import autosub.Helpers as Helpers
from autosub.downloadSubs import DownloadSub

# Settings
log = logging.getLogger('thelogger')


class checkSub():
    """
    Check the SubtitleSeeker API for subtitles of episodes that are in the WANTEDQUEUE.
    If the subtitles are found, call DownloadSub
    """
    def run(self):
        log.debug("checkSub: Starting round of checkSub")
        toDelete_wantedQueue = []
        if not Helpers.checkAPICallsTvdb() or not Helpers.checkAPICallsSubSeeker():            
            log.warning("checkSub: out of api calls")
            return True
        
        if autosub.WANTEDQUEUELOCK:
            log.debug("checkSub: Exiting, another threat is using the queues")
            return False
        else:
            autosub.WANTEDQUEUELOCK = True
        
        #     # Initiate the Addic7ed API
        if autosub.ADDIC7EDUSER and autosub.ADDIC7EDPASSWD:
            try:
                autosub.ADDIC7EDAPI = autosub.Addic7ed.Addic7edAPI()
                a7Response= autosub.ADDIC7EDAPI.login()
            except:
                log.debug("checkSub: Couldn't connect with Addic7ed.com")
                
        
        for index, wantedItem in enumerate(autosub.WANTEDQUEUE):
            title = wantedItem['title']
            season = wantedItem['season']
            episode = wantedItem['episode']
            originalfile = wantedItem['originalFileLocationOnDisk']
            languages = wantedItem['lang']
            
            if not Helpers.checkAPICallsTvdb() or not Helpers.checkAPICallsSubSeeker():
                #Make sure that we are allow to connect to SubtitleSeeker and TvDB
                log.warning("checkSub: out of api calls")
                break
            
            if autosub.SUBNL != "":
                nlsrtfile = os.path.splitext(originalfile)[0] + u"." + autosub.SUBNL + u".srt"
            else:
                nlsrtfile = os.path.splitext(originalfile)[0] + u".srt"
                        
            if autosub.SUBENG == "":
                # Check for overlapping names
                if autosub.SUBNL != "" or not autosub.DOWNLOADDUTCH:
                    engsrtfile = os.path.splitext(originalfile)[0] + u".srt"
                # Hardcoded fallback
                else:
                    engsrtfile = os.path.splitext(originalfile)[0] + u".en.srt"
            else:
                engsrtfile = os.path.splitext(originalfile)[0] + u"." + autosub.SUBENG + u".srt"

            
            #lets try to find a showid
            showid = Helpers.getShowid(title)
            #no showid? skip this item
            if not showid:
                continue
            
            langtmp = languages[:]
            for lang in langtmp:
                log.debug("checkSub: trying to get a downloadlink for %s, language is %s" % (originalfile, lang))
                # get all links higher than the minmatch as input for downloadSub
                
                # Returns a list of 4-element tuples
                allResults = autosub.Subtitleseeker.getSubLinks(showid, lang, wantedItem)                

                if lang == autosub.DUTCH:
                    wantedItem['destinationFileLocationOnDisk'] = nlsrtfile
                elif lang == autosub.ENGLISH:
                    wantedItem['destinationFileLocationOnDisk'] = engsrtfile
                    
                if allResults:                   
                    log.info("checkSub: The episode %s - Season %s Episode %s has 1 or more matching subtitles on SubtitleSeeker, downloading it!" % (title, season, episode))
                    log.debug("checkSub: destination filename %s" % wantedItem['destinationFileLocationOnDisk'])
                
                downloadItem = wantedItem.copy()
                downloadItem['downlang'] = lang
                    
                if not DownloadSub(downloadItem, allResults, a7Response):
                    continue

                #Remove downloaded language
                languages.remove(lang)
                
                if lang == autosub.DUTCH:
                    if (autosub.FALLBACKTOENG and not autosub.DOWNLOADENG) and autosub.ENGLISH in languages:
                        log.debug('checkSub: We found a dutch subtitle and fallback is true. Removing the english subtitle from the wantedlist.')
                        languages.remove(autosub.ENGLISH)
                
                    if autosub.ENGLISHSUBDELETE == True:
                        if os.path.exists(nlsrtfile) and os.path.exists(engsrtfile):
                            log.debug("checkSub: Trying to delete English subtitle.")
                            try:
                                os.unlink(engsrtfile)
                                log.info("checkSub: Removed English subtitle: %s" % engsrtfile)
                            except:
                                log.error("checkSub: Error while trying to remove subtitle %s." % engsrtfile)
                        else:
                            log.debug("checkSub: English subtitle not found.")
                
                if len(languages) == 0:
                    toDelete_wantedQueue.append(index)
                break
         
        if autosub.ADDIC7EDAPI:
            autosub.ADDIC7EDAPI.logout()
        
         
                                        
        i = len(toDelete_wantedQueue) - 1
        while i >= 0:
            log.debug("checkSub: Removed item from the wantedQueue at index %s" % toDelete_wantedQueue[i])
            autosub.WANTEDQUEUE.pop(toDelete_wantedQueue[i])
            i = i - 1

        log.debug("checkSub: Finished round of checkSub")
        autosub.WANTEDQUEUELOCK = False
        return True
