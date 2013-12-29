# Autosub Db.py - http://code.google.com/p/auto-sub/
#
# The Autosub scanDisk module
#

import logging
import os
import platform
import re
import time
import unicodedata

# Autosub specific modules
import autosub
import autosub.Helpers
from autosub.ProcessFilename import ProcessFilename
# Settings
log = logging.getLogger('thelogger')

def walkDir(path):
    for dirname, dirnames, filenames in os.walk(os.path.join(path)):
            log.debug("scanDisk: directory name: %s" %dirname)
            if re.search('_unpack_', dirname, re.IGNORECASE): 
                log.debug("scanDisk: found a unpack directory, skipping")
                continue
            
            if autosub.SKIPHIDDENDIRS and os.path.split(dirname)[1].startswith(u'.'):
                continue
            
            if re.search('_failed_', dirname, re.IGNORECASE): 
                log.debug("scanDisk: found a failed directory, skipping")
                continue
            
            if re.search('@eaDir', dirname, re.IGNORECASE): 
                log.debug("scanDisk: found a Synology indexing/thumbnail directory, skipping")
                continue

            for filename in filenames:
                splitname = filename.split(".")
                ext = splitname[len(splitname) - 1]

                if ext in ('avi', 'mkv', 'wmv', 'ts', 'mp4'):
                    if re.search('sample', filename): continue

                    if not platform.system() == 'Windows':
                        # First transform to unicode
                        decodedFilename = unicode(filename.decode('utf-8'))
                        # Then translate it into best matching ascii char 
                        correctedFilename = ''.join((c for c in unicodedata.normalize('NFD', decodedFilename) if unicodedata.category(c) != 'Mn'))
                        if decodedFilename != correctedFilename:
                            os.rename(os.path.join(dirname, filename), os.path.join(dirname, correctedFilename))
                            log.info("scanDir: Renamed file %s" % correctedFilename)
                        filename = correctedFilename

                    # What subtitle files should we expect?
            
                    if autosub.SUBNL != "":
                        srtfile = os.path.splitext(filename)[0] + u"." + autosub.SUBNL + u".srt"
                    else:
                        srtfile = os.path.splitext(filename)[0] + u".srt"
        
                    srtfileeng = os.path.splitext(filename)[0] + u"." + autosub.SUBENG + u".srt"

                    if not os.path.exists(os.path.join(dirname, srtfile)) or (not os.path.exists(os.path.join(dirname, srtfileeng)) and autosub.DOWNLOADENG):
                        log.debug("scanDir: File %s is missing a subtitle" % filename)
                        lang = []
                        filenameResults = ProcessFilename(os.path.splitext(filename)[0], os.path.splitext(filename)[1])
                        if 'title' in filenameResults.keys():
                            if 'season' in filenameResults.keys():
                                if 'episode' in filenameResults.keys():
                                    title = filenameResults['title']
                                    season = filenameResults['season']
                                    episode = filenameResults['episode']

                                    if autosub.Helpers.SkipShow(title, season, episode) == True:
                                        log.debug("scanDir: SkipShow returned True")
                                        log.info("scanDir: Skipping %s - Season %s Episode %s" % (title, season, episode))
                                        continue
                                    log.info("scanDir: Dutch subtitle wanted for %s and added to wantedQueue" % filename)
                                    filenameResults['originalFileLocationOnDisk'] = os.path.join(dirname, filename)
                                    filenameResults['timestamp'] = unicode(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getctime(filenameResults['originalFileLocationOnDisk']))))
                                    if not os.path.exists(os.path.join(dirname, srtfile)):
                                        lang.append(autosub.DUTCH)
                                    if not os.path.exists(os.path.join(dirname, srtfileeng)) and (autosub.FALLBACKTOENG or autosub.DOWNLOADENG):
                                        lang.append(autosub.ENGLISH)
                                    
                                    filenameResults['lang'] = lang
                                    autosub.WANTEDQUEUE.append(filenameResults)
                                    
                                else:
                                    log.error("scanDir: Could not process the filename properly filename: %s" % filename)
                                    continue
                            else:
                                log.error("scanDir: Could not process the filename properly filename: %s" % filename)
                                continue
                        else:
                            log.error("scanDir: Could not process the filename properly filename: %s" % filename)
                            continue

class scanDisk():
    """
    Scan the specified path for episodes without Dutch or (if wanted) English subtitles.
    If found add these Dutch or English subtitles to the WANTEDQUEUE.
    """
    def run(self):
        log.debug("scanDir: Starting round of local disk checking at %s" % autosub.ROOTPATH)
        if autosub.WANTEDQUEUELOCK == True:
            log.debug("scanDir: Exiting, another threat is using the queues")
            return False
        else:
            autosub.WANTEDQUEUELOCK = True
        
        autosub.WANTEDQUEUE = []

        seriespaths = [x.strip() for x in autosub.ROOTPATH.split(',')]
        for seriespath in seriespaths:
            if not os.path.exists(seriespath):
                log.error("scanDir: Root path %s does not exist, aborting..." % seriespath)
                continue
            
            try:
                walkDir(seriespath)
            except:
                walkDir(str(seriespath))
                                    
        log.debug("scanDir: Finished round of local disk checking")
        autosub.WANTEDQUEUELOCK = False
 
        return True