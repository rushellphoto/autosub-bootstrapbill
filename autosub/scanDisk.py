# Autosub Db.py - https://code.google.com/p/autosub-bootstrapbill/
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
                log.debug("scanDisk: found a Synology indexing directory, skipping this folder and all subfolders.")
                tmpdirs = dirnames[:]
                for dir in tmpdirs:
                    dirnames.remove(dir)
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
                    
                    lang=[]
                    
                    #Check what the Dutch subtitle would be.
                    if autosub.SUBNL != "":
                        srtfilenl = os.path.splitext(filename)[0] + u"." + autosub.SUBNL + u".srt"
                    else:
                        srtfilenl = os.path.splitext(filename)[0] + u".srt"
                    
                    #Check what the English subtitle would be.
                    if autosub.SUBENG == "":
                        # Check for overlapping names
                        if autosub.SUBNL != "" or not autosub.DOWNLOADDUTCH:
                            srtfileeng = os.path.splitext(filename)[0] + u".srt"
                        # Hardcoded fallback
                        else:
                            srtfileeng = os.path.splitext(filename)[0] + u".en.srt"
                    else:
                        srtfileeng = os.path.splitext(filename)[0] + u"." + autosub.SUBENG + u".srt"
                    
                    # Check which languages we want to download based on user settings.
                    if autosub.DOWNLOADDUTCH:
                        # If the Dutch subtitle doesn't exist, then add it to the wanted list.
                        if not os.path.exists(os.path.join(dirname, srtfilenl)):
                            lang.append(autosub.DUTCH)

                    if autosub.DOWNLOADENG:
                        # If the English subtitle doesn't exist, then add it to the wanted list.
                        if not os.path.exists(os.path.join(dirname, srtfileeng)):
                            lang.append(autosub.ENGLISH)
                    
                    if (autosub.FALLBACKTOENG and autosub.DOWNLOADDUTCH) and not autosub.DOWNLOADENG:
                        # If the Dutch and English subtitles do not exist, then add English to the wanted list.
                        if not os.path.exists(os.path.join(dirname, srtfilenl)) and not os.path.exists(os.path.join(dirname, srtfileeng)):
                            lang.append(autosub.ENGLISH)

                    if not lang:
                        # autosub.WANTEDQUEUE empty
                        continue

                    log.debug("scanDir: File %s is missing subtitle(s): %s" % (filename, ', '.join(map(str,lang))))
                    filenameResults = ProcessFilename(os.path.splitext(filename)[0], os.path.splitext(filename)[1])
                    if 'title' in filenameResults.keys():
                        if 'season' in filenameResults.keys():
                            if 'episode' in filenameResults.keys():
                                title = filenameResults['title']
                                season = filenameResults['season']
                                episode = filenameResults['episode']

                                if not filenameResults['releasegrp'] and not filenameResults['source'] and not filenameResults['quality'] and not filenameResults['source']:
                                    continue

                                if autosub.Helpers.SkipShow(title, season, episode) == True:
                                    log.debug("scanDir: SkipShow returned True")
                                    log.info("scanDir: Skipping %s - Season %s Episode %s" % (title, season, episode))
                                    continue
                                if len(lang) == 1:
                                    log.info("scanDir: %s subtitle wanted for %s and added to wantedQueue" % (lang[0], filename))
                                else:
                                    log.info("scanDir: %s subtitles wanted for %s and added to wantedQueue" % (' and '.join(map(str,lang)), filename))                                       
                                filenameResults['originalFileLocationOnDisk'] = os.path.join(dirname, filename)
                                filenameResults['timestamp'] = unicode(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getctime(filenameResults['originalFileLocationOnDisk']))))                                
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