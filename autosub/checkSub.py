# Autosub checkSub.py - https://code.google.com/p/autosub-bootstrapbill/
#
# The Autosub checkSub module
#

import logging
import os

# Autosub specific modules
import autosub.getSubLinks
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

            
            #lets try to find a showid; no showid? skip this item
            showid = Helpers.getShowid(title)
            if not showid:
                continue
            
            for lang in languages[:]:
                downloadItem = wantedItem.copy()
                downloadItem['downlang'] = lang

                log.debug("checkSub: trying to get a downloadlink for %s, language is %s" % (originalfile, lang))
                # get all links higher than the minmatch as input for downloadSub
                allResults = autosub.getSubLinks.getSubLinks(showid, lang, wantedItem)
                
                if not allResults:
                    log.debug("checkSub: no suitable subtitles were found for %s based on your minmatchscore" % downloadItem['originalFileLocationOnDisk'])
                    continue                                 

                if lang == autosub.DUTCH:
                    downloadItem['destinationFileLocationOnDisk'] = nlsrtfile
                elif lang == autosub.ENGLISH:
                    downloadItem['destinationFileLocationOnDisk'] = engsrtfile
                    
                if allResults:                   
                    log.info("checkSub: The episode %s - Season %s Episode %s has 1 or more matching subtitles on SubtitleSeeker, downloading it!" % (title, season, episode))
                    log.debug("checkSub: destination filename %s" % downloadItem['destinationFileLocationOnDisk'])
                    
                if not DownloadSub(allResults, downloadItem):
                    continue
                
                #Remove downloaded language
                languages.remove(lang)
                
                if lang == autosub.DUTCH:
                    if (autosub.FALLBACKTOENG and not autosub.DOWNLOADENG) and autosub.ENGLISH in languages:
                        log.debug('checkSub: We found a Dutch subtitle and fallback is true. Removing the English subtitle from the wantedlist.')
                        languages.remove(autosub.ENGLISH)
                
                    if autosub.ENGLISHSUBDELETE:
                        log.info("checkSub: Clean up English enabled")
                        if os.path.exists(engsrtfile):
                            log.debug("checkSub: Trying to delete English subtitle: %s" % engsrtfile)
                            try:
                                os.unlink(engsrtfile)
                                log.info("checkSub: Removed English subtitle: %s" % engsrtfile)
                            except:
                                log.error("checkSub: Error while trying to remove subtitle %s." % engsrtfile)
                        else:
                            log.info("checkSub: English subtitle not found.")
                
                if len(languages) == 0:
                    toDelete_wantedQueue.append(index)
                    break
                                        
        i = len(toDelete_wantedQueue) - 1
        while i >= 0:
            log.debug("checkSub: Removed item from the wantedQueue at index %s" % toDelete_wantedQueue[i])
            autosub.WANTEDQUEUE.pop(toDelete_wantedQueue[i])
            i = i - 1

        log.debug("checkSub: Finished round of checkSub")
        autosub.WANTEDQUEUELOCK = False
        return True
