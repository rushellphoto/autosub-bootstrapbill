#
# Autosub Addic7ed.py - http://code.google.com/p/auto-sub/
#
# The Addic7ed method specific module
#

import re
import requests
import bs4
import logging
import autosub

log = logging.getLogger('thelogger')

#Every part of the file_info got a list with regex. The first item in this list should be the standardnaming
#The second (and following) regex contains nonstandard naming (either typo's or other renaming tools (like sickbeard)) 
#Nonstandard naming should be renamed using the syn dictionary. 

source = [re.compile("(ahdtv|hdtv|web[. _-]*dl|bluray|dvdrip|webrip)", re.IGNORECASE),
          re.compile("(tv|dvd|bdrip|web)", re.IGNORECASE)]

#A dictionary containing as keys, the nonstandard naming. Followed by there standard naming.
#Very important!!! Should be unicode and all LOWERCASE!!!
source_syn = {u'tv' : u'hdtv',
              u'ahdtv' : u'hdtv',
              u'dvd' : u'dvdrip',
              u'bdrip': u'bluray',
              u'webdl' : u'web-dl',
              u'web' : u'web-dl'}


quality = [re.compile("(1080p|720p|480p)" , re.IGNORECASE), 
           re.compile("(1080[i]*|720|480|HD|SD)", re.IGNORECASE)]

quality_syn = {u'1080' : u'1080p',
               u'1080i' : u'1080p',
               u'720' : u'720p',
               u'480p' : u'sd',
               u'480' : u'sd', 
               u'hd': u'720p'}
               
codec = [re.compile("([xh]*264|xvid|dvix)" , re.IGNORECASE)]

#Note: x264 is the opensource implementation of h264.
codec_syn = {u'x264' : u'h264',
               u'264' : u'h264'}

#The following 2 variables create the regex used for guessing the releasegrp. Functions should not call them!
_releasegrps = ['0TV',
               '2HD',
               'ASAP',
               'aAF',
               'AFG',
               'AVS',
               'BAJSKORV',
               'BiA',
               'BS',
               'BTN',
               'BWB',
               'CLUE',
               'CP',
               'COMPULSiON',
               'CtrlHD',
               'CTU',
               'DEMAND',
               'DIMENSION',
               'DNR',
               'EbP',
               'ECI',
               'EVOLVE',
               'FEVER',
               'FOV',
               'FQM',
               'FUM',
               'GFY',
               'GreenBlade',
               'HoodBag',
               'HAGGiS',
               'hV',
               'HWD',
               'IMMERSE',
               'KiNGS',
               'KILLERS'
               'KYER',
               'LFF',
               'LOL',
               'LP',
               'MMI',
               'MOMENTUM',
               'mSD',
               'NBS',
               'NFHD',
               'NFT',
               'NIN',
               'nodlabs',
               'NoTV',
               'NTb',
               'OOO',
               'ORENJi',
               'ORPHEUS',
               'PCSYNDICATE',
               'P0W4',
               'P0W4HD',
               'playXD',
               'POD',
               'RANDi',
               'REWARD',
               'ROVERS',
               'RRH',
               'SAiNTS',
               'SAPHiRE',
               'SCT',
               'SiNNERS',
               'SkyM',
               'SLOMO',
               'sozin',
               'sundox',
               'TjHD',
               'TOPAZ', 
               'TLA',
               'TOKUS',
               'T00NG0D',
               'TVSMASH',
               'VASKITTU',
               'UP',
               'XOR',
               'XS',
               'YFN']


_releasegrp_pre = '(' + '|'.join(_releasegrps) + ')'

releasegrp = [re.compile(_releasegrp_pre, re.IGNORECASE)]

def _returnHit(regex, version_info):
    # Should have been filter out beforehand
    if not version_info:        
        return -1
    
    for reg in regex:
        results = re.findall(reg, version_info)
        if results:
            # Multiple hits in 1 group returns conflict
            # These releases are ignored
            if len(results) > 1:
                return -1 
            result = results[0].lower()
            result = re.sub("[. _-]", "-", result)
            return result
        else:
            return None
    
                    
def _checkSynonyms(synonyms, result):
    if result in synonyms.keys():
        if synonyms[result]:
            return synonyms[result].lower()
    else:
        return result


def _getSource(file_info):
    result = _checkSynonyms(source_syn,
                            _returnHit(source, file_info))
    return result

def _getQuality(file_info, HD):
    result = _checkSynonyms(quality_syn,
                            _returnHit(quality, file_info))
    
    if not result:
        # CheckBOX HD on a7
        if HD:
            result = u'720p'
    
    return result

def _getCodec(file_info):
    result = _checkSynonyms(codec_syn,
                            _returnHit(codec, file_info))
    
    return result

def _getReleasegrp(file_info):
    result = _returnHit(releasegrp, file_info)
    
    return result


def ReconstructRelease(version_info, HD):
    # This method tries to reconstruct the original releasename
    # based on the information in the version column
    # in the a7 show-season overview page
    
    source = _getSource(version_info)
    quality = _getQuality(version_info, HD)
    codec = _getCodec(version_info)
    releasegroup = _getReleasegrp(version_info)
    release_dict = {}
    
    # Version info gave error (eg multiple releasegroups)
    # Ignore these releases
    if any(x==-1 for x in (source, quality, codec, releasegroup)):
        return False
    
    # assume missing codec is x264, error prone!
    
    # Add info based on source
    if any(source == x for x in (u'web-dl', u'hdtv', u'bluray')):
        if not codec:
            codec = u'h264'
    if source == u'web-dl':
        # default quality for WEB-DLs is 720p
        if not quality:
            quality = '720p'

    # Add info based on specific Releasegroups  
    if releasegroup:  
        rlsgroupsHD = re.compile("(DIMENSION|IMMERSE|ORENJi|EVOLVE|CTU|KILLERS|2HD)" , re.IGNORECASE)
        rlsgroupsSD = re.compile("(LOL|ASAP|FQM|XOR|NoTV|FoV|FEVER|AVS|COMPULSiON)" , re.IGNORECASE)
        rlsgroupsSD_xvid = re.compile("(AFG)" , re.IGNORECASE)
        rlsgroupsWebdl = re.compile("(YFN|FUM|BS|ECI|NTb|CtrlHD|NFHD|KiNGS)" , re.IGNORECASE)
        
        if re.match(rlsgroupsHD, releasegroup) or \
            re.match(rlsgroupsSD, releasegroup) or \
            re.match(rlsgroupsWebdl, releasegroup):
            if not codec:
                codec = u'h264'
        if re.match(rlsgroupsSD_xvid, releasegroup):
            if not codec:
                codec = u'xvid'
        if re.match(rlsgroupsHD, releasegroup) or \
            re.match(rlsgroupsSD, releasegroup) or \
            re.match(rlsgroupsSD_xvid, releasegroup):
            if not source:
                source = u'hdtv'  
        if re.match(rlsgroupsWebdl, releasegroup):
            if not source:
                source = u'web-dl'
        if re.match(rlsgroupsHD, releasegroup):
            if not quality:
                quality = u'720p'
        if re.match(rlsgroupsSD, releasegroup):
            if not quality:
                quality = u'sd'
    
    release_dict['source'] = source
    release_dict['quality'] = quality
    release_dict['codec'] = codec
    release_dict['releasegrp'] = releasegroup
    
    return release_dict
    
def MakeTwinRelease(originalDict):
    # This modules creates the SD/HD counterpart for releases with specific releasegroups
    rlsgroup = originalDict['releasegrp']
    qual = originalDict['quality']
    source = originalDict['source']
    
    rlsSwitchDict = {u'dimension' : u'lol', u'lol': u'dimension',
                     u'immerse': u'asap', u'asap' : u'immerse',
                     u'2hd' : u'2hd', u'bia' : u'bia', u'fov' : u'fov'}
    qualSwitchDict_hdtv = {u'sd' : u'720p', u'720p' : u'sd'}
    qualSwitchDict_webdl =  {u'1080p' : u'720p', u'720p' : u'1080p'}
    
    # DIMENSION <> LOL
    # IMMERSE <> ASAP
    # 2HD <> 2HD 720p
    # BiA <> BiA 720p
    # FoV <> FoV 720p
    twinDict = originalDict.copy()
    if rlsgroup in rlsSwitchDict.keys():
        twinDict['releasegrp'] = rlsSwitchDict[rlsgroup]
        twinDict['quality'] = qualSwitchDict_hdtv[qual]
    
    # WEB-DLs 720p and 1080p are always synced
    if source == 'web-dl' and qual in qualSwitchDict_webdl.keys():
        twinDict['quality'] = qualSwitchDict_webdl[qual]
    
    
    diff = set(originalDict.iteritems())-set(twinDict.iteritems())
    
    if len(diff):
        return twinDict
    else:
        return None


def makeRelease(versionInfo, title, season, episode):
    version = versionInfo.replace(' ','.')
    se = 'S' + season + 'E' + episode
    release = '.'.join([title,se,version])
    return release

        
class Addic7edAPI():
    def __init__(self):
        self.session = requests.Session()
        self.server = 'http://www.addic7ed.com/'
        self.session.headers = {'User-Agent': autosub.USERAGENT}        
       
        self.logged_in = False
        
    def login(self, addic7eduser, addic7edpasswd):        
        log.debug('Addic7edAPI: Logging in')
        
        
        if addic7eduser == u'None' or addic7edpasswd == u'None':
            log.error('Addic7edAPI: Username and password must be specified')
            return 'Username and password must be specified'

        data = {'username': addic7eduser, 'password': addic7edpasswd, 'Submit': 'Log in'}
        try:
            r = self.session.post(self.server + '/dologin.php', data, timeout=10, allow_redirects=False)
        except requests.Timeout:
            log.debug('Addic7edAPI: Timeout after 10 seconds')
        if r.status_code == 302:
            log.info('Addic7edAPI: Logged in')
            self.logged_in = True
            return 'Logged in to Addic7ed.com'
        else:
            log.error('Addic7edAPI: Failed to login')
            return 'Failed to log in to Addic7ed.com: check your login information'

    def logout(self):
        if self.logged_in:
            try:
                r = self.session.get(self.server + '/logout.php', timeout=10)
                log.info('Addic7edAPI: Logged out')
            except requests.Timeout:
                log.debug('Addic7edAPI: Timeout after 10 seconds')
            if r.status_code != 200:
                log.error('Addic7edAPI: Request failed with status code %d' % r.status_code)
        self.session.close()

    def get(self, url):
        """
        Make a GET request on `url`
        :param string url: part of the URL to reach with the leading slash
        :rtype: :class:`bs4.BeautifulSoup`
        """
        
        if not self.logged_in:
            log.error("Addic7edAPI: You are not properly logged in. Check your credentials!")
            return None
        try:
            r = self.session.get(self.server + url, timeout=10)
        except requests.Timeout:
            log.debug('Addic7edAPI: Timeout after 10 seconds')
        if r.status_code != 200:
            log.error('Addic7edAPI: Request failed with status code %d' % r.status_code)
        return bs4.BeautifulSoup(r.content)

    def download(self, downloadlink):

        if not self.logged_in:
            log.error("Addic7edAPI: You are not properly logged in. Check your credentials!")
            return None
        try:
            r = self.session.get(self.server + downloadlink, timeout=10, headers={'Referer': autosub.USERAGENT})
        except requests.Timeout:
            log.error('Addic7edAPI: Timeout after 10 seconds')
        if r.status_code != 200:
            log.error('Addic7edAPI: Request failed with status code %d' % r.status_code)
        else:
            log.debug('Addic7edAPI: Request succesful with status code %d' % r.status_code)
        if r.headers['Content-Type'] == 'text/html':
            log.error('Addic7edAPI: Download limit exceeded')
        return r.content

        
