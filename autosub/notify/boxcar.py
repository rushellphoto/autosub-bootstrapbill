import logging
import autosub
import urllib, urllib2
import time

log = logging.getLogger('thelogger')

API_URL = "https://boxcar.io/devices/providers/WhZ9h994f6Xx3rJInP4R/notifications"

def test_notify(boxcaruser):
    if not boxcaruser:
        boxcaruser = autosub.BOXCARUSER
    
    log.debug("Boxcar: Trying to send a notification.")
    title = 'Auto-Sub Bootstrap Bill'
    message = 'Testing Boxcar settings from Auto-Sub.'
    return _send_notify(message, title, boxcaruser)

def send_notify(lang, subtitlefile, videofile, website):
    log.debug("Pushalot: Trying to send a notification.")
    title = 'Auto-Sub Bootstrap Bill'
    message = "Auto-Sub just downloaded the following subtitle: \n%s from %s" %(subtitlefile, website)
    boxcaruser = autosub.BOXCARUSER
    return _send_notify(message, title, boxcaruser)

def _send_notify(message, title, boxcaruser, subscribe=False):
    # build up the URL and parameters
    message = message.strip()
    curUrl = API_URL

    # if this is a subscription notification then act accordingly
    if subscribe:
        data = urllib.urlencode({'email': boxcaruser})
        curUrl = curUrl + "/subscribe"
        
    # for normal requests we need all these parameters
    else:
        data = urllib.urlencode({
            'email': boxcaruser,
            'notification[from_screen_name]': title,
            'notification[message]': message.encode('utf-8'),
            'notification[from_remote_service_id]': int(time.time())
            })

    # send the request to boxcar
    try:
        req = urllib2.Request(curUrl)
        handle = urllib2.urlopen(req, data)
        handle.close()
            
    except urllib2.URLError, e:
        # if we get an error back that doesn't have an error code then who knows what's really happening
        if not hasattr(e, 'code'):
            log.error("Boxcar: Notification failed.")
            return False
        else:
            log.error("Boxcar: Notification failed. Error code: " + str(e.code))

        # HTTP status 404 if the provided email address isn't a Boxcar user.
        if e.code == 404:
            log.info("Boxcar: Username is wrong/not a boxcar email. Boxcar will send an email to it")
            return False
            
        # For HTTP status code 401's, it is because you are passing in either an invalid token, or the user has not added your service.
        elif e.code == 401:
            # If the user has already added your service, we'll return an HTTP status code of 401.
            if subscribe:
                log.info("Boxcar: Already subscribed to service")
                return False
                
            #HTTP status 401 if the user doesn't have the service added
            else:
                subscribeNote = _send_notify(message, title, boxcaruser, True)
                if subscribeNote:
                    log.debug("Boxcar: Subscription sent")
                    return True
                else:
                    log.error("Boxcar: Subscription could not be send")
                    return False
            
        # If you receive an HTTP status code of 400, it is because you failed to send the proper parameters
        elif e.code == 400:
            log.error("Boxcar: Wrong data send to boxcar")
            return False

    log.info("Boxcar: Notification successful.")
    return True