'''
    YouTube plugin for XBMC
    Copyright (C) 2010-2012 Tobias Ussing And Henrik Mosgaard Jensen

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import re
import sys
import time
try: import simplejson as json
except ImportError: import json

# ERRORCODES:
# 0 = Ignore
# 200 = OK
# 303 = See other (returned an error message)
# 500 = uncaught error


class YouTubeLogin():
    APIKEY = "AI39si6hWF7uOkKh4B9OEAX-gK337xbwR9Vax-cdeF9CF9iNAcQftT8NVhEXaORRLHAmHxj6GjM-Prw04odK4FxACFfKkiH9lg"
    CLIENT_ID = "208795275779.apps.googleusercontent.com"
    CLIENT_SECRET = "sZn1pllhAfyonULAWfoGKCfp"
    SCOPE = "https://www.googleapis.com/auth/youtube"

    urls = {}
    urls["oauth_api_login"] = u"https://accounts.google.com/o/oauth2/device/code"
    urls["oauth_api_token"] = u"https://accounts.google.com/o/oauth2/token"

    def __init__(self):
        self.xbmc = sys.modules["__main__"].xbmc
        self.xbmcgui = sys.modules["__main__"].xbmcgui

        self.pluginsettings = sys.modules["__main__"].pluginsettings
        self.settings = sys.modules["__main__"].settings
        self.language = sys.modules["__main__"].language
        self.plugin = sys.modules["__main__"].plugin
        self.dbg = sys.modules["__main__"].dbg

        self.utils = sys.modules["__main__"].utils
        self.core = sys.modules["__main__"].core
        self.common = sys.modules["__main__"].common

    def linkAccount(self, params={}):
        ret = self.core._fetchPage({
                "link": self.urls["oauth_api_login"],
                "url_data": { "client_id": self.CLIENT_ID,
                              "scope": self.SCOPE }
                })
        deviceCode = json.loads(ret["content"])
        dialog = self.xbmcgui.Dialog()
        dialog.ok("hi", "Go to {0}".format(deviceCode["verification_url"]),
                  "and enter this code:", deviceCode["user_code"])
        print repr(deviceCode)

        progress = self.xbmcgui.DialogProgress()
        progress.create("Waiting", "doot doot")
        progress.update(0)
        while True:
            ret = self.core._fetchPage({
                    "link": self.urls["oauth_api_token"],
                    "url_data": {
                        "client_id": self.CLIENT_ID,
                        "client_secret": self.CLIENT_SECRET,
                        "code": deviceCode["device_code"],
                        "grant_type": "http://oauth.net/grant_type/device/1.0",
                        }})

            poll = json.loads(ret["content"])
            if "error" not in poll or poll["error"] != u"authorization_pending":
                break

            # Check every 500ms if the user canceled
            for _ in range(0, 2 * deviceCode["interval"]):
                self.xbmc.sleep(500)
                if progress.iscanceled():
                    return
        progress.close()

        self.settings.setSetting("oauth2_expires_at", str(int(poll["expires_in"]) + time.time()))
        self.settings.setSetting("oauth2_access_token", poll["access_token"])
        self.settings.setSetting("oauth2_refresh_token", poll["refresh_token"])
        dialog.ok("hi", "you did it!", poll["access_token"], poll["refresh_token"])
        print repr(poll)

        return "", 200

    def unlinkAccount(self, params={}):
        self.settings.setSetting("oauth2_expires_at", "")
        self.settings.setSetting("oauth2_access_token", "")
        self.settings.setSetting("oauth2_refresh_token", "")

        return "", 200


    def refreshToken(self):
        self.common.log("")

        refresh_token = self.settings.getSetting("oauth2_refresh_token")
        if refresh_token:
            self.settings.setSetting("oauth2_access_token", "")
            ret = self._fetchPage({
                    "link": self.urls["oauth_api_token"],
                    "no-language-cookie": "true",
                    "url_data": {
                        "client_id": self.CLIENT_ID,
                        "client_secret": self.CLIENT_SECRET,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                        }})

            if ret["status"] == 200:
                try:
                    oauth = json.loads(ret["content"])
                except:
                    self.common.log("Except: " + repr(ret))
                    return False

                self.common.log("- returning, got result a: " + repr(oauth))

                self.settings.setSetting("oauth2_access_token", oauth["access_token"])
                self.settings.setSetting("oauth2_expires_at", str(int(oauth["expires_in"]) + time.time()) )
                self.common.log("Success")
                return True
            else:
                self.common.log("Failure, Trying a clean login")
                self.login.linkAccount()
                return False

        self.common.log("didn't even try")
        return False
