# Autosub notify library - http://code.google.com/p/auto-sub/
# Every function should have 2 calls, send_notify and test_notify
# Send notify should get 3 argument: videofile, subtitlefile (both without path) and lang (which should be the language)
# test_notify doesn't require any argument
# every module should return True if success, and False when failed

import logging
import os

import autosub

from autosub.notify import twitter
from autosub.notify import mail
from autosub.notify import nma
from autosub.notify import growl
from autosub.notify import prowl
from autosub.notify import pushalot
from autosub.notify import pushover
from autosub.notify import boxcar
from autosub.notify import plexmediaserver

log = logging.getLogger('thelogger')  

def notify(lang, subtitlefile, videofile):
    log.debug("Notification: Trying to send notification. Language: %s Srt: %s Video: %s" %(lang, subtitlefile, videofile))
    #Lets strip video file and subtitle file of its path!
    subtitlefile = os.path.basename(subtitlefile)
    videofile = os.path.basename(videofile)
    
    if lang == 'English' and autosub.NOTIFYEN:
        notifySend(lang, subtitlefile, videofile)
    if lang == 'Dutch' and autosub.NOTIFYNL:
        notifySend(lang, subtitlefile, videofile)

def notifySend(lang, subtitlefile, videofile):
    if autosub.NOTIFYTWITTER:
        log.debug("Notification: Twitter is enabled")
        twitter.send_notify(lang, subtitlefile, videofile)
    
    if autosub.NOTIFYMAIL:
        log.debug("Notification: Mail is enabled")
        mail.send_notify(lang, subtitlefile, videofile)
    
    if autosub.NOTIFYNMA:
        log.debug("Notification: Notify My Android is enabled")
        nma.send_notify(lang, subtitlefile, videofile)
    
    if autosub.NOTIFYGROWL:
        log.debug("Notification: Growl is enabled")
        growl.send_notify(lang, subtitlefile, videofile)

    if autosub.NOTIFYPROWL:
        log.debug("Notification: Prowl is enabled")
        prowl.send_notify(lang, subtitlefile, videofile)
    
    if autosub.NOTIFYPUSHALOT:
        log.debug("Notification: Pushalot is enabled")
        pushalot.send_notify(lang, subtitlefile, videofile)
    
    if autosub.NOTIFYPUSHOVER:
        log.debug("Notification: Pushover is enabled")
        pushover.send_notify(lang, subtitlefile, videofile)
    
    if autosub.NOTIFYBOXCAR:
        log.debug("Notification: Boxcar is enabled")
        boxcar.send_notify(lang, subtitlefile, videofile)
    
    if autosub.NOTIFYPLEX:
        log.debug("Notification: Plex Media Server is enabled")
        plexmediaserver.send_update_library()