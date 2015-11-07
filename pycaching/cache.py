#!/usr/bin/env python3

import logging
import datetime
import re
import enum
from pycaching import errors
from pycaching.geo import Point
from pycaching.trackable import Trackable
from pycaching.log import Log
from pycaching.util import parse_date, format_date, rot13, lazy_loaded

# prefix _type() function to avoid colisions with cache type
_type = type


class Cache(object):

    # generated by Util.get_possible_attributes()
    # TODO: smarter way of keeping attributes up to date
    _possible_attributes = {
        "abandonedbuilding": "Abandoned Structure",
        "available": "Available at All Times",
        "bicycles": "Bicycles",
        "boat": "Boat",
        "campfires": "Campfires",
        "camping": "Camping Available",
        "cliff": "Cliff / Falling Rocks",
        "climbing": "Difficult Climbing",
        "cow": "Watch for Livestock",
        "danger": "Dangerous Area",
        "dangerousanimals": "Dangerous Animals",
        "dogs": "Dogs",
        "fee": "Access or Parking Fee",
        "field_puzzle": "Field Puzzle",
        "firstaid": "Needs Maintenance",
        "flashlight": "Flashlight Required",
        "food": "Food Nearby",
        "frontyard": "Front Yard(Private Residence)",
        "fuel": "Fuel Nearby",
        "geotour": "GeoTour Cache",
        "hike_long": "Long Hike (+10km)",
        "hike_med": "Medium Hike (1km-10km)",
        "hike_short": "Short Hike (Less than 1km)",
        "hiking": "Significant Hike",
        "horses": "Horses",
        "hunting": "Hunting",
        "jeeps": "Off-Road Vehicles",
        "kids": "Recommended for Kids",
        "landf": "Lost And Found Tour",
        "mine": "Abandoned Mines",
        "motorcycles": "Motortcycles",
        "night": "Recommended at Night",
        "nightcache": "Night Cache",
        "onehour": "Takes Less Than an Hour",
        "parking": "Parking Available",
        "parkngrab": "Park and Grab",
        "partnership": "Partnership Cache",
        "phone": "Telephone Nearby",
        "picnic": "Picnic Tables Nearby",
        "poisonoak": "Poisonous Plants",
        "public": "Public Transportation",
        "quads": "Quads",
        "rappelling": "Climbing Gear",
        "restrooms": "Public Restrooms Nearby",
        "rv": "Truck Driver/RV",
        "s-tool": "Special Tool Required",
        "scenic": "Scenic View",
        "scuba": "Scuba Gear",
        "seasonal": "Seasonal Access",
        "skiis": "Cross Country Skis",
        "snowmobiles": "Snowmobiles",
        "snowshoes": "Snowshoes",
        "stealth": "Stealth Required",
        "stroller": "Stroller Accessible",
        "swimming": "May Require Swimming",
        "teamwork": "Teamwork Required",
        "thorn": "Thorns",
        "ticks": "Ticks",
        "touristok": "Tourist Friendly",
        "treeclimbing": "Tree Climbing",
        "uv": "UV Light Required",
        "wading": "May Require Wading",
        "water": "Drinking Water Nearby",
        "wheelchair": "Wheelchair Accessible",
        "winter": "Available During Winter",
        "wirelessbeacon": "Wireless Beacon"
    }

    def __init__(self, geocaching, wp, **kwargs):

        self.geocaching = geocaching
        if wp is not None:
            self.wp = wp

        known_kwargs = {"name", "type", "location", "state", "found", "size", "difficulty", "terrain",
                        "author", "hidden", "attributes", "summary", "description", "hint", "favorites",
                        "pm_only", "url", "trackable_page_url", "logbook_token", "log_page_url"}

        for name in known_kwargs:
            if name in kwargs:
                setattr(self, name, kwargs[name])

    def __str__(self):
        return self.wp

    def __eq__(self, other):
        return self.geocaching == other.geocaching and self.wp == other.wp

    @classmethod
    def from_trackable(cls, trackable):
        return cls(trackable.geocaching, None, url=trackable.location_url)

    @classmethod
    def from_block(cls, block):
        c = cls(block.tile.geocaching, block.cache_wp, name=block.cache_name)
        c.location = Point.from_block(block)
        return c

    @property
    def wp(self):
        return self._wp

    @wp.setter
    def wp(self, wp):
        wp = str(wp).upper().strip()
        if not wp.startswith("GC"):
            raise errors.ValueError("Waypoint '{}' doesn't start with 'GC'.".format(wp))
        self._wp = wp

    @property
    def geocaching(self):
        return self._geocaching

    @geocaching.setter
    def geocaching(self, geocaching):
        if not hasattr(geocaching, "_request"):
            raise errors.ValueError(
                "Passed object (type: '{}') doesn't contain '_request' method.".format(_type(geocaching)))
        self._geocaching = geocaching

    @property
    @lazy_loaded
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        name = str(name).strip()
        self._name = name

    @property
    @lazy_loaded
    def location(self):
        return self._location

    @location.setter
    def location(self, location):
        if _type(location) is str:
            location = Point.from_string(location)
        elif _type(location) is not Point:
            raise errors.ValueError(
                "Passed object is not Point instance nor string containing coordinates.")
        self._location = location

    @property
    @lazy_loaded
    def type(self):
        return self._type

    @type.setter
    def type(self, type):
        if _type(type) is not Type:
            type = Type.from_string(type)
        self._type = type

    @property
    @lazy_loaded
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = bool(state)

    @property
    @lazy_loaded
    def found(self):
        return self._found

    @found.setter
    def found(self, found):
        self._found = bool(found)

    @property
    @lazy_loaded
    def size(self):
        return self._size

    @size.setter
    def size(self, size):
        if _type(size) is not Size:
            size = Size.from_string(size)
        self._size = size

    @property
    @lazy_loaded
    def difficulty(self):
        return self._difficulty

    @difficulty.setter
    def difficulty(self, difficulty):
        difficulty = float(difficulty)
        if difficulty < 1 or difficulty > 5 or difficulty * 10 % 5 != 0:  # X.0 or X.5
            raise errors.ValueError("Difficulty must be from 1 to 5 and divisible by 0.5.")
        self._difficulty = difficulty

    @property
    @lazy_loaded
    def terrain(self):
        return self._terrain

    @terrain.setter
    def terrain(self, terrain):
        terrain = float(terrain)
        if terrain < 1 or terrain > 5 or terrain * 10 % 5 != 0:  # X.0 or X.5
            raise errors.ValueError("Terrain must be from 1 to 5 and divisible by 0.5.")
        self._terrain = terrain

    @property
    @lazy_loaded
    def author(self):
        return self._author

    @author.setter
    def author(self, author):
        author = str(author).strip()
        self._author = author

    @property
    @lazy_loaded
    def hidden(self):
        return self._hidden

    @hidden.setter
    def hidden(self, hidden):
        if _type(hidden) is str:
            hidden = parse_date(hidden)
        elif _type(hidden) is not datetime.date:
            raise errors.ValueError(
                "Passed object is not datetime.date instance nor string containing a date.")
        self._hidden = hidden

    @property
    @lazy_loaded
    def attributes(self):
        return self._attributes

    @attributes.setter
    def attributes(self, attributes):
        if _type(attributes) is not dict:
            raise errors.ValueError("Attribues is not dict.")

        self._attributes = {}
        for name, allowed in attributes.items():
            name = name.strip().lower()
            if name in self._possible_attributes:
                self._attributes[name] = allowed
            else:
                logging.warning("Unknown attribute '%s', ignoring.", name)

    @property
    @lazy_loaded
    def summary(self):
        return self._summary

    @summary.setter
    def summary(self, summary):
        summary = str(summary).strip()
        self._summary = summary

    @property
    @lazy_loaded
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        description = str(description).strip()
        self._description = description

    @property
    @lazy_loaded
    def hint(self):
        return self._hint

    @hint.setter
    def hint(self, hint):
        hint = str(hint).strip()
        self._hint = hint

    @property
    @lazy_loaded
    def favorites(self):
        return self._favorites

    @favorites.setter
    def favorites(self, favorites):
        self._favorites = int(favorites)

    @property
    def pm_only(self):
        return self._pm_only

    @pm_only.setter
    def pm_only(self, pm_only):
        self._pm_only = bool(pm_only)

    @property
    @lazy_loaded
    def logbook_token(self):
        return self._logbook_token

    @logbook_token.setter
    def logbook_token(self, logbook_token):
        self._logbook_token = logbook_token

    @property
    @lazy_loaded
    def trackable_page_url(self):
        return self._trackable_page_url

    @trackable_page_url.setter
    def trackable_page_url(self, trackable_page_url):
        self._trackable_page_url = trackable_page_url

    @logbook_token.setter
    def logbook_token(self, logbook_token):
        self._logbook_token = logbook_token

    @property
    @lazy_loaded
    def log_page_url(self):
        return self._log_page_url

    @log_page_url.setter
    def log_page_url(self, log_page_url):
        self._log_page_url = log_page_url

    def load(self):
        try:
            # pick url based on what info we have right now
            if hasattr(self, "url"):
                root = self.geocaching._request(self.url)
            elif hasattr(self, "_wp"):
                root = self.geocaching._request("seek/cache_details.aspx", params={"wp": self._wp})
            else:
                raise errors.LoadError("Cache lacks info for loading")

        except errors.Error as e:
            # probably 404 during cache loading - cache not exists
            raise errors.LoadError("Error in loading cache") from e

        # check for PM only caches if using free account
        if root.find("p", "PMOWarning") is not None:
            raise errors.PMOnlyException("Premium Members only.")

        cache_details = root.find(id="cacheDetails")
        attributes_widget, inventory_widget, * \
            bookmarks_widget = root.find_all("div", "CacheDetailNavigationWidget")

        # parse raw data
        wp = root.title.string.split(" ")[0]
        name = cache_details.find("h2")
        type = cache_details.find("img").get("src").split(
            "/")[-1].rsplit(".", 1)[0]  # filename w/o extension
        author = cache_details("a")[1]
        hidden = cache_details.find("div", "minorCacheDetails").find_all("div")[1]
        location = root.find(id="uxLatLon")
        state = root.find("ul", "OldWarning")
        found = root.find("div", "FoundStatus")
        D_T = root.find("div", "CacheStarLabels").find_all("img")
        size = root.find("div", "CacheSize").find("img")
        attributes_raw = attributes_widget.find_all("img")
        user_content = root.find_all("div", "UserSuppliedContent")
        hint = root.find(id="div_hint")
        favorites = root.find("span", "favorite-value")

        # load logbook_token
        js_content = "\n".join(map(lambda i: i.text, root.find_all("script")))
        logbook_token = re.findall("userToken\\s*=\\s*'([^']+)'", js_content)[0]

        # if there are some trackables
        if len(inventory_widget.find_all("a")) >= 3:
            trackable_page_url = inventory_widget.find(
                id="ctl00_ContentBody_uxTravelBugList_uxViewAllTrackableItems").get("href")[3:]  # has "../" on start
        else:
            trackable_page_url = None

        log_page_url = root.find(id="ctl00_ContentBody_GeoNav_logButton")["href"]
        # prettify data
        self.wp = wp
        self.name = name.text
        self.type = Type.from_filename(type)
        self.author = author.text
        self.hidden = parse_date(hidden.text.split(":")[-1])
        self.location = Point.from_string(location.text)
        self.state = state is None
        self.found = found and ("Found It!" or "Attended" in found.text) or False
        self.difficulty, self.terrain = [float(_.get("alt").split()[0]) for _ in D_T]
        self.size = Size.from_filename(size.get("src").split(
            "/")[-1].rsplit(".", 1)[0])  # filename w/o extension
        attributes_raw = [_.get("src").split("/")[-1].rsplit("-", 1) for _ in attributes_raw]
        self.attributes = {attribute_name: appendix.startswith("yes")
                           for attribute_name, appendix in attributes_raw if not appendix.startswith("blank")}
        self.summary = user_content[0].text
        self.description = str(user_content[1])
        self.hint = rot13(hint.text.strip())
        self.favorites = 0 if favorites is None else int(favorites.text)
        self.logbook_token = logbook_token
        self.trackable_page_url = trackable_page_url
        self.log_page_url = log_page_url

        logging.debug("Cache loaded: %r", self)

    def load_quick(self):
        """Loads details from map server.

        Loads just basic cache details, but very quickly."""

        res = self.geocaching._request("http://tiles01.geocaching.com/map.details", params={
            "i": self.wp
        }, expect="json")

        if res["status"] == "failed" or len(res["data"]) != 1:
            msg = res["msg"] if "msg" in res else "Unknown error (probably not existing cache)"
            raise errors.LoadError("Waypoint '{}' cannot be loaded: {}".format(self.wp, msg))

        data = res["data"][0]

        # prettify data
        self.name = data["name"]
        self.type = Type.from_string(data["type"]["text"])
        self.state = data["available"]
        self.size = Size.from_string(data["container"]["text"])
        self.difficulty = data["difficulty"]["text"]
        self.terrain = data["terrain"]["text"]
        self.hidden = parse_date(data["hidden"])
        self.author = data["owner"]["text"]
        self.favorites = int(data["fp"])
        self.pm_only = data["subrOnly"]

        logging.debug("Cache loaded: %r", self)

    def _logbook_get_page(self, page=0, per_page=25):
        """Loads one page from logbook."""

        res = self.geocaching._request("seek/geocache.logbook", params={
            "tkn": self.logbook_token,  # will trigger lazy_loading if needed
            "idx": int(page) + 1,  # Groundspeak indexes this from 1 (OMG..)
            "num": int(per_page),
            "decrypt": "true"
        }, expect="json")

        if res["status"] != "success":
            error_msg = res["msg"] if "msg" in res else "Unknown error"
            raise errors.LoadError("Logbook cannot be loaded: {}".format(error_msg))

        return res["data"]

    def load_logbook(self, limit=float("inf")):
        """Returns a generator of logs for this cache."""

        logging.info("Loading logbook for %s...", self.wp)
        self.logbook = []

        page = 0
        per_page = min(limit, 100)  # max number to fetch in one request is 100 items

        while True:
            # get one page
            logbook_page = self._logbook_get_page(page, per_page)
            page += 1

            if not logbook_page:
                # result is empty - no more logs
                raise StopIteration()

            for log_data in logbook_page:

                limit -= 1  # handle limit
                if limit < 0:
                    raise StopIteration()

                # create and fill log object
                l = Log()
                l.type = log_data["LogType"]
                l.text = log_data["LogText"]
                l.visited = log_data["Visited"]
                l.author = log_data["UserName"]
                self.logbook.append(l)
                yield l

    # TODO: trackable list can have multiple pages - handle it in similar way as _logbook_get_page
    # for example see: http://www.geocaching.com/geocache/GC26737_geocaching-jinak-tb-gc-hrbitov
    def load_trackables(self, limit=float("inf")):
        logging.info("Loading trackables for %s...", self.wp)
        self.trackables = []

        url = self.trackable_page_url  # will trigger lazy_loading if needed
        if not url:
            # no link to all trackables = no trackables in cache
            raise StopIteration()
        res = self.geocaching._request(url)

        trackable_table = res.find_all("table")[1]
        links = trackable_table.find_all("a")
        # filter out all urls for trackables
        urls = [link.get("href") for link in links if "track" in link.get("href")]
        # find the names matching the trackble urls
        names = [re.split("[\<\>]", str(link))[2] for link in links if "track" in link.get("href")]

        for name, url in zip(names, urls):

            limit -= 1  # handle limit
            if limit < 0:
                raise StopIteration()

            # create and fill trackable object
            t = Trackable(self.geocaching, None)
            t.name = name
            t.url = url
            self.trackables.append(t)
            yield t

    def _load_log_page(self):
        log_page = self.geocaching._request(self.log_page_url)

        # find all valid log types for the cache (-1 kicks out "- select type of log -")
        valid_types = {o.get_text().lower(): o["value"]
                       for o in log_page.find_all("option") if o["value"] != "-1"}

        # find all static data fields needed for log
        hidden_inputs = log_page.find_all("input", type=["hidden", "submit"])
        hidden_inputs = {i["name"]: i.get("value", "") for i in hidden_inputs}

        # get user date format
        date_format = log_page.find(
            id="ctl00_ContentBody_LogBookPanel1_uxDateFormatHint").text.strip("()")

        return valid_types, hidden_inputs, date_format

    def post_log(self, l):
        if not l.text:
            raise errors.ValueError("Log text is empty")

        valid_types, hidden_inputs, date_format = self._load_log_page()
        if l.type.value not in valid_types:
            raise errors.ValueError("The Cache does not accept this type of log")

        # assemble post data
        post = hidden_inputs
        post["ctl00$ContentBody$LogBookPanel1$btnSubmitLog"] = "Submit Log Entry"
        post["ctl00$ContentBody$LogBookPanel1$ddLogType"] = valid_types[l.type.value]
        post["ctl00$ContentBody$LogBookPanel1$uxDateVisited"] = format_date(l.visited, date_format)
        post["ctl00$ContentBody$LogBookPanel1$uxLogInfo"] = l.text

        self.geocaching._request(self.log_page_url, method="POST", data=post)


class Type(enum.Enum):

    # value is cache image filename (http://www.geocaching.com/images/WptTypes/[VALUE].gif)
    traditional = "2"
    multicache = "3"
    mystery = unknown = "8"
    letterbox = "5"
    event = "6"
    mega_event = "mega"
    giga_event = "giga"
    earthcache = "137"
    cito = cache_in_trash_out_event = "13"
    webcam = "11"
    virtual = "4"
    wherigo = "1858"
    lost_and_found_event = "10Years_32"
    project_ape = "ape_32"
    groundspeak_hq = "HQ_32"
    gps_adventures_exhibit = "1304"
    groundspeak_block_party = "4738"
    locationless = reverse = "12"

    @classmethod
    def from_filename(cls, filename):
        """Returns cache type from its image filename"""

        if filename == "earthcache":
            filename = "137"  # fuck Groundspeak, they use 2 exactly same icons with 2 different names

        return cls(filename)

    @classmethod
    def from_string(cls, name):
        """Returns cache type from its human readable name"""

        name = name.replace(" Geocache", "")  # with space!
        name = name.replace(" Cache", "")  # with space!
        name = name.lower().strip()

        name_mapping = {
            "traditional": cls.traditional,
            "multi-cache": cls.multicache,
            "mystery": cls.mystery,
            "unknown": cls.unknown,
            "letterbox hybrid": cls.letterbox,
            "event": cls.event,
            "mega-event": cls.mega_event,
            "giga-event": cls.giga_event,
            "earthcache": cls.earthcache,
            "cito": cls.cito,
            "cache in trash out event": cls.cache_in_trash_out_event,
            "webcam": cls.webcam,
            "virtual": cls.virtual,
            "wherigo": cls.wherigo,
            "lost and found event": cls.lost_and_found_event,
            "project ape": cls.project_ape,
            "groundspeak hq": cls.groundspeak_hq,
            "gps adventures exhibit": cls.gps_adventures_exhibit,
            "groundspeak block party": cls.groundspeak_block_party,
            "locationless (reverse)": cls.locationless,
        }

        try:
            return name_mapping[name]
        except KeyError as e:
            raise errors.ValueError("Unknown cache type '{}'.".format(name)) from e


class Size(enum.Enum):
    micro = "micro"
    small = "small"
    regular = "regular"
    large = "large"
    not_chosen = "not chosen"
    virtual = "virtual"
    other = "other"

    @classmethod
    def from_filename(cls, filename):
        """Returns cache size from its image filename"""
        return cls[filename]

    @classmethod
    def from_string(cls, name):
        """Returns cache size from its human readable name"""
        name = name.strip().lower()

        try:
            return cls(name)
        except ValueError as e:
            raise errors.ValueError("Unknown cache type '{}'.".format(name)) from e
