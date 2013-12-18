#
# Autosub Tvdb.py - http://code.google.com/p/auto-sub/
#
# The Tvdb API module
#

import logging

import urllib
from xml.dom import minidom

import autosub
import autosub.Helpers

# Settings
log = logging.getLogger('thelogger')


def getShowidApi(showName):
    """
    Search for the IMDB ID by using the TvDB API and the name of the show.
    Keyword arguments:
    showName -- Name of the show to search the showid for
    """
    
    api = autosub.IMDBAPI
    
    getShowIdUrl = "%sGetSeries.php?seriesname=%s" % (api, urllib.quote(showName.encode('utf8')))
    log.debug("getShowid: TvDB API request for %s: %s" % (showName, getShowIdUrl))
    if autosub.Helpers.checkAPICallsTvdb(use=True):
        try:
            tvdbapi = autosub.Helpers.API(getShowIdUrl)
            dom = minidom.parse(tvdbapi.resp)
            tvdbapi.resp.close()
        except:
            log.error("getShowid: The server returned an error for request %s" % getShowIdUrl)
            return None
        
        if not dom or len(dom.getElementsByTagName('Series')) == 0:
            return None
        
        for sub in dom.getElementsByTagName('Series'):
            # Assume that first match is best, maybe adapt this in future
            try:
                showid = sub.getElementsByTagName('IMDB_ID')[0].firstChild.data
            except:
                log.error("getShowid: Error while retrieving the IMDB ID for %s." % showName)
                log.error("getShowid: Recommend to add the IMDB ID for %s manually for the time being." % showName)
                return None    
            # Remove trailing 'tt' from IMDB ID
            return showid[2:]
    else:
        log.error("API: out of api calls for TvDB API")


def getShowOffcialName(imdbID):
    pass