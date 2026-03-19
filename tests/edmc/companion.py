"""
companion.py - Handle use of Frontier's Companion API (CAPI) service.

Copyright (c) EDCD, All Rights Reserved
Licensed under the GNU General Public License v2 or later.
See LICENSE file.

Deals with initiating authentication for, and use of, CAPI.
Some associated code is in protocol.py which creates and handles the edmc://
protocol used for the callback.
"""
from __future__ import annotations

import base64
import collections
import csv
import datetime
import hashlib
import json
import numbers
import os
import random
import threading
import time
import tkinter as tk
import urllib.parse
import webbrowser
import requests
from email.utils import parsedate
from enum import StrEnum
from pathlib import Path
from queue import Queue
from typing import TYPE_CHECKING, Any, TypeVar, Union, Iterator
from collections.abc import Mapping
from dataclasses import dataclass
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import config as conf_module

if TYPE_CHECKING:
    UserDict = collections.UserDict[str, Any]  # indicate to our type checkers what this generic class holds normally
else:
    UserDict = collections.UserDict  # Otherwise simply use the actual class


capi_query_cooldown = 60  # Minimum time between (sets of) CAPI queries
capi_fleetcarrier_query_cooldown = 60 * 15  # Minimum time between CAPI fleetcarrier queries
capi_default_requests_timeout = 10
capi_fleetcarrier_requests_timeout = 60
auth_timeout = 30  # timeout for initial auth

# Used by both class Auth and Session
FRONTIER_AUTH_SERVER = 'https://auth.frontierstore.net'

SERVER_LIVE = 'https://companion.orerve.net'
SERVER_LEGACY = 'https://legacy-companion.orerve.net'
SERVER_BETA = 'https://pts-companion.orerve.net'

commodity_map: dict = {}


class CAPIData:
    """Encapsulates a Companion API (CAPI) response."""

    def __init__(
        self,
        data: Union[str, dict[str, Any], 'CAPIData', None] = None,
        source_host: str | None = None,
        source_endpoint: str | None = None,
        request_cmdr: str | None = None
    ) -> None:
        pass

class CAPIDataEncoder(json.JSONEncoder):
    """Allow for json dumping via specified encoder."""

    def default(self, o):
        """Tell JSON encoder that we're actually just a dict."""
        return o.__dict__


@dataclass
class CAPIDataRawEndpoint:
    """Represents the last received CAPI response for a specific endpoint."""

    raw_data: str
    query_time: datetime.datetime
    # TODO: Maybe requests.response status ?


class CAPIDataRaw:
    """Stores the last obtained raw CAPI response for each endpoint."""

    def __init__(self) -> None:
        self.raw_data: dict[str, CAPIDataRawEndpoint] = {}

    def record_endpoint(self, endpoint: str, raw_data: str, query_time: datetime.datetime) -> None:
        """Record the latest raw data for the given endpoint."""
        self.raw_data[endpoint] = CAPIDataRawEndpoint(raw_data, query_time)

    def __str__(self) -> str:
        """Return a readable string representation of the stored data."""
        entries = []
        for k, v in self.raw_data.items():
            entries.append(
                f'"{k}": {{\n\t"query_time": "{v.query_time}",\n\t"raw_data": {v.raw_data}\n}}'
            )
        return '{\n' + ',\n\n'.join(entries) + '\n}'

    def __iter__(self) -> Iterator[str]:
        """Iterate over stored endpoint keys."""
        return iter(self.raw_data)

    def __getitem__(self, item: str) -> CAPIDataRawEndpoint:
        """Access the stored CAPIDataRawEndpoint by endpoint name."""
        return self.raw_data[item]


def listify(thing: list | dict | None) -> list[Any]:
    """
    Convert a JSON array or int-indexed dict into a Python list.

    Companion API sometimes returns arrays as JSON arrays, sometimes as
    JSON objects indexed by integers. Sparse arrays are converted to
    lists with gaps filled with None.
    """
    if thing is None:
        return []

    if isinstance(thing, list):
        return list(thing)

    if isinstance(thing, dict):
        # Find maximum index to preallocate list
        indices = [int(k) for k in thing.keys()]
        max_idx = max(indices, default=-1)
        retval: list[Any] = [None] * (max_idx + 1)

        for k, v in thing.items():
            retval[int(k)] = v

        return retval
    raise ValueError(f"expected an array or sparse array, got {thing!r}")


class BaseCAPIException(Exception):
    """
    Base class for all Companion API (CAPI) exceptions.

    Subclasses should define a class variable `DEFAULT_MSG` for the
    default error message. If an instance is created without args,
    the default message will be used.
    """

    DEFAULT_MSG: str = "Unknown CAPI error"

    def __init__(self, *args: Any) -> None:
        if not args:
            args = (self.DEFAULT_MSG,)
        super().__init__(*args)
