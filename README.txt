README 

Thank you for choosing AutoSub! The automated python subtitle downloader for SubtitleSeeker.com
Unlike the original AutoSub (until version 0.5.8), which used Bierdopje.com, the current and next versions
use SubtitleSeeker.com as its primary source for subtitles.

Many thanks for the administrators of SubtitleSeeker.com to expose and facilitate the API's feeds 
so that we lazy users can enjoy automated scripts like this.

Via SubtitleSeeker.com AutoSub indexes other subtitle
websites: these are:
- Opensubtitles.org  
- Podnapisi.net
- Undertexter.se 
- Subscene.com
- a mirror of Bierdopjes database, hosted on SubtitleSeeker.com itself

An addition, it scrapes the full Addic7ed.com webpage directly (ie not using the SubtitleSeeker API).
To use this scraper, however, a login for Addic7ed.com is required!
Also, the website sets a daily 15 download limit per user.



AutoSub is an easy and straightforward script that scans your TV contents. 
If no SRT found it will attempt to download one from SubtitleSeeker.com. 
Where the script will attempt to match the correct version of the subtitle with the file located on the disk. 
Once every day it will do a full rescan of your local content versus the SubtitleSeeker API.

If no dutch version can be found it can (based on a setting) download the english version instead.

To use:

Ubuntu
Make sure you have python installed. Also you need the python-cheetah package:
 * sudo apt-get install python-cheetah
 * Download the zip file from our download section
 * Unzip the file, change to the directory where AutoSub.py is located
 * Start the script: " python AutoSub.py "
 * A webbrowser should now open
 * Go to the config page, check the settings, make sure you set atleast: path 
(Should point to the location where AutoSub.py is located. Rootpath (Should point to the root of your series folder)
 * Shutdown AutoSub and start it again
Enjoy your subtitles!


The current version of auto-sub (0.5.9) is an adaptation of the original auto-sub (last version 0.5.8). 


