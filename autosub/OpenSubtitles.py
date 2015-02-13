#
# Autosub OpenSubtitles.py - https://code.google.com/p/autosub-bootstrapbill/
#
# The OpenSubtitles method specific module
#

import autosub
import re
import library.requests as requests
from bs4 import BeautifulSoup
import time
import sys
import os
import shutil

import xml.etree.cElementTree as ET
import library.requests as requests

import logging

log = logging.getLogger('thelogger')

def OpenSubtitlesLogin(opensubtitlesusername=None,opensubtitlespasswd=None):
    log.debug('OpenSubtitlesLogin: Start of routine')
    data = {'user': autosub.OPENSUBTITLESUSER, 'password':autosub.OPENSUBTITLESPASSWD,'a':'login','remember':'on' }
        # Expose to test login
        # When fields are empty it will check the config file
    if opensubtitlesusername and opensubtitlespasswd:
        data['user'] = opensubtitlesusername
        data['password'] = opensubtitlespasswd
        log.debug('OpenSubtitlesLogin: Test login with user: %s'% data['user'])
    else:
        data['user'] = autosub.OPENSUBTITLESUSER
        data['password'] = autosub.OPENSUBTITLESPASSWD
        log.debug('OpenSubtitlesLogin: Normal Login with User %s' % data['user'] )
        if autosub.OPENSUBTITLESLOGGED_IN :
            log.debug('OpenSubtitlesLogin: Already Logged in with user %s'  % data['user'] )
            return True
             
    if data['user'] and data['password']:
        pass
    else:
        log.debug('OpenSubtitlesLogin: Username or password empty')
        autosub.OPENSUBTITLESRANK = 'anonymous'
        return False
    autosub.OPENSUBTTITLESSESSION = requests.Session()
    autosub.OPENSUBTTITLESSESSION.headers = {'User-Agent': 'Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0;  rv:11.0) like Gecko', 'Pragma': 'no-cache','weblang':'nl'}
    try:
        RequestResult = autosub.OPENSUBTTITLESSESSION.post(autosub.OPENSUBTITLESURL + '/nl/login', data, timeout=10, allow_redirects=False)
    except:
        log.debug('OpenSubtitlesLogin: Login post exception.')
        return False
    if RequestResult.status_code == 301:
        autosub.OPENSUBTITLESLOGGED_IN = True
        log.debug('OpenSubtitlesLogin: Logged in as User: %s' % data['user'])
    else:
        log.error('OpenSubtitlesLogin: Login failed with code %s' % RequestResult.status_code)
        return False
    try:
        RequestResult = autosub.OPENSUBTTITLESSESSION.get(autosub.OPENSUBTITLESURL + '/nl/xml',timeout=10)         
    except:
        log.debug('OpenSubtitlesLogin: Get first page exception.')
        return True
    root = ET.fromstring(RequestResult.content)
    try:
        ProfilePage = root.find('.//links/profile').get('Link')
    except:
        log.error('OpenSubtitlesLogin: "Could not retrieve profilepage of user %s' % data['user'])
        return True
    log.debug('OpenSubtitlesLogin: ProfilePage = %s' % ProfilePage)
    try:
        RequestResult = autosub.OPENSUBTTITLESSESSION.get(autosub.OPENSUBTITLESURL + ProfilePage + '/xml',timeout=10)
    except:
        log.debug('OpenSubtitlesLogin: Get Userprofile exception.')
        return True 
    root = ET.fromstring(RequestResult.content)
    try:
        autosub.OPENSUBTITLESRANK= root.find('.//profile/UserProfile/UserRank').text
    except:
        log.debug('OpenSubtitlesLogin: Could not retrieve the userrank.')
        return True       
    Message = data['user'] + " as " + autosub.OPENSUBTITLESRANK
    log.info('OpenSubtitlesLogin: logged is as User %s' % Message)
    return True

def OpenSubtitlesLogout():
    log.debug("OpenSubtitlesLogout: Start of routine")
    if autosub.OPENSUBTITLESLOGGED_IN:
        try:
            RequestResult = autosub.OPENSUBTTITLESSESSION.get(autosub.OPENSUBTITLESURL + '/en/login/redirect-%7Cen%7Clogin%7Csearch%7Ca-logout/a-logout', timeout=10)
        except requests.exceptions.RequestException as e:
            log.debug('OpenSubtitlesLogout: Logout failed exception is: %s' %e)
            return False
        if RequestResult.status_code == 200 :
            autosub.OPENSUBTITLESRANK = 'anonymous'
            autosub.OPENSUBTITLESLOGGED_IN = False
            autosub.OPENSUBTTITLESSESSION.close()
            log.info('OpenSubtitlesLogout: Logged out.')
        else:
            log.debug('OpenSubtitlesLogout: Logout failed')
            return False
    else:
        log.debug("OpenSubtitlesLogout: Not logged in")
    return True