#
# Autosub OpenSubtitles.py - https://code.google.com/p/autosub-bootstrapbill/
#
# The OpenSubtitles method specific module
#

import autosub
import time
import library.requests as requests
import xml.etree.cElementTree as ET
from autosub.Db import EpisodeIdCache
import logging

log = logging.getLogger('thelogger')

def TimeOut():
    TimeOut = time.time() - autosub.OPENSUBTITLESTIME
    TimeOut = 7 - TimeOut
    if TimeOut > 0 :
        time.sleep(TimeOut)
    autosub.OPENSUBTITLESTIME = time.time()

def OpenSubtitlesLogin(opensubtitlesusername=None,opensubtitlespasswd=None):
    data = {'user': autosub.OPENSUBTITLESUSER, 'password':autosub.OPENSUBTITLESPASSWD,'a':'login','redirect':'/nl' ,'remember':'on' }
        # Expose to test login
        # When fields are empty it will check the config file
    if opensubtitlesusername and opensubtitlespasswd:
        data['user'] = opensubtitlesusername
        data['password'] = opensubtitlespasswd
        log.debug('OpenSubtitlesLogin: Test login with User: %s'% data['user'])
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
        return False

    autosub.OPENSUBTTITLESSESSION = requests.Session()
    autosub.OPENSUBTTITLESSESSION.headers = {'User-Agent': 'Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0;  rv:11.0) like Gecko'}
    autosub.OPENSUBTTITLESSESSION.headers.update({'referer': autosub.OPENSUBTITLESURL})

    try:
        TimeOut()
        RequestResult = autosub.OPENSUBTTITLESSESSION.post(autosub.OPENSUBTITLESURL + '/login', data, timeout=10)
    except:
        log.debug('OpenSubtitlesLogin: Login post request exception.')
        autosub.OPENSUBTITLESLOGGED_IN = False
        return False
    try:
        TimeOut()
        RequestResult = autosub.OPENSUBTTITLESSESSION.get(autosub.OPENSUBTITLESURL + '/xml',timeout=10)         
    except:
        log.debug('OpenSubtitlesLogin: Could not get a page from Opensubtitles.')
        return False
    root = ET.fromstring(RequestResult.content)
    try:
        if root.find('.//logged_as').text == data['user']:
            autosub.OPENSUBTITLESLOGGED_IN = True
            return True
    except:
        pass
    log.error('OpenSubtitlesLogin: Login of |User %s failed' % data['user'])
    autosub.OPENSUBTITLESLOGGED_IN = False
    return False

def OpenSubtitlesLogout():
    if autosub.OPENSUBTITLESLOGGED_IN:
        autosub.OPENSUBTTITLESSESSION.headers.update({'referer': autosub.OPENSUBTITLESURL})
        try:
            TimeOut()
            RequestResult = autosub.OPENSUBTTITLESSESSION.get(autosub.OPENSUBTITLESURL + '/login/redirect-|nl|search/a-logout', timeout=10)
        except requests.exceptions.RequestException as e:
            log.debug('OpenSubtitlesLogout: Logout failed exception is: %s' %e)
            return False
        try:
            autosub.OPENSUBTTITLESSESSION.headers.update({'referer': autosub.OPENSUBTITLESURL})
            TimeOut()
            RequestResult = autosub.OPENSUBTTITLESSESSION.get(autosub.OPENSUBTITLESURL + '/xml', timeout=10)
            root = ET.fromstring(RequestResult.content)
        except:
            return False
        try:
            if root.find('.//logged_as').text == 'not-logged-in':
                autosub.OPENSUBTITLESLOGGED_IN = False
                autosub.OPENSUBTTITLESSESSION.close()
                log.info('OpenSubtitlesLogout: Logged out.')
                return True
            else:
                log.debug('OpenSubtitlesLogout: Logout failed')
                return False
        except:
            log.debug("OpenSubtitlesLogout: Not logged in")
            return False

def GetEpisodeId(OsShowId, Season, Episode):
    """
    Get the Episode Opensubtitles Id for this Serie, Season and Episode
    Update the Cache for this Serie by putting the Episodes info into the episode cache
    Keyword argument:
    ShowId of the show
    Season number of the Episoe
    Episode number of the Episode
    Return Value:
    Episode Imdb Id of the Episode 
    """
    #First we try the cache
    
    FoundEpisodeId = EpisodeIdCache().getId(OsShowId, Season, Episode)
    if FoundEpisodeId:
        return FoundEpisodeId

    # Episode is not in cache now we try the Opensubtitles website
    # We fetch the show overview page and search voor the Id's of the epiode we want
    SearchUrl = autosub.OPENSUBTITLESURL + '/xml/ssearch/sublanguageid-all/idmovie-' + str(OsShowId)
    try:
        TimeOut()
        RequestResult = autosub.OPENSUBTTITLESSESSION.get(SearchUrl, timeout=10)
        Referer = SearchUrl.replace('/xml','')
        autosub.OPENSUBTTITLESSESSION.headers.update({'referer': Referer})
    except:
        log.debug('GetEpisodeImdb: Could not connect to Opensubtitles.')
        return None
    if 'text/xml' not in RequestResult.headers['Content-Type']:
        log.error('GetEpisodeImdb: Opensubtitle responded with an error')
        return None
    try:
        root = ET.fromstring(RequestResult.content)
    except:
        log.debug('GetEpisodeImdb: Serie with Opensubtitles Id  %s could not be found on Opensubtitles.' %OsShowId)
        return None
    try:
        SubTitles = root.find('.//search/results')
    except:
        return None
    # Because as we have this whole page, we put the other Episode Id's in the cache
    Commit = False
    for Sub in SubTitles:
        try:
            if Sub.tag != 'subtitle':
                continue
            Link       = Sub.find('EpisodeName').attrib['Link'].split('/imdbid-')
            EpisodeId  = unicode(Link[1]) if Link[1] else u''
            SeasonNum  = unicode(Sub.find('SeriesSeason').text.zfill(2))
            EpisodeNum = unicode(Sub.find('SeriesEpisode').text.zfill(2))
            if int(SeasonNum) > 0 and int(EpisodeNum) > 0 and EpisodeId:
                Commit = True
                EpisodeIdCache().setId(EpisodeId, OsShowId, SeasonNum, EpisodeNum)
                if Season == SeasonNum and Episode == EpisodeNum:
                    FoundEpisodeId = EpisodeId
        except:
            continue
    if Commit : EpisodeIdCache().commit()
    return FoundEpisodeId

def GetOpensubtitlesId(ImdbId, ShowName):
    #http://www.opensubtitles.org/nl/search2/sublanguageid-dut/searchonlytvseries-on/moviename-dark+matter
    # First we try to find the Opensubtitles Id via the Imdb Id
    SearchUrls=[]
    SearchUrls.append(autosub.OPENSUBTITLESURL + '/xml/search/sublanguageid-all/searchonlytvseries-on/imdbid-tt' + str(ImdbId))
    SearchUrls.append(autosub.OPENSUBTITLESURL + '/xml/search2/sublanguageid-dut/searchonlytvseries-on/moviename-' + str(ShowName))
    OpenSubTitlesId = ImdbIdFound = None
    # first we try the direct serie with the Imdb Id
    # if this fails we try it via a name search
    autosub.OPENSUBTTITLESSESSION.headers.update({'referer': autosub.OPENSUBTITLESURL})
    for SearchUrl in SearchUrls:
        try:
            TimeOut()
            RequestResult = autosub.OPENSUBTTITLESSESSION.get(SearchUrl, timeout=10)
            Referer = SearchUrl.replace('/xml','')
        except:
            log.error('GetEpisodeImdb: Could not connect to Opensubtitles.')
            return None
        if 'text/xml' not in RequestResult.headers['Content-Type']:
            log.error('GetEpisodeImdb: Opensubtitle responded with an error')
            contine
        try:
            root = ET.fromstring(RequestResult.content)
            SubTitles = root.find('.//search/results')
        except:
            continu
        for Sub in SubTitles:
            if Sub.tag != 'subtitle':
                continue
            try:
                ImdbIdFound = unicode(Sub.find('MovieImdbID').text)
                if ImdbIdFound == ImdbId.lstrip('0'):
                    try:
                        OpenSubTitlesId = unicode(Sub.find('MovieID').text)
                        break
                    except:
                        continue
            except:
                continue
        if OpenSubTitlesId:
            break
    autosub.OPENSUBTTITLESSESSION.headers.update({'referer': Referer})
    if not OpenSubTitlesId:
        log.debug('GetEpisodeImdb: Serie %s Imdb Id = %s could not be found on Opensubtitles.' %(ShowName,ImdbId))
        return None
    else:
        return OpenSubTitlesId

