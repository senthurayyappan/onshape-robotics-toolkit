"""
onshape
======

Provides access to the Onshape REST API
"""

import base64
import datetime
import hashlib
import hmac
import json
import os
import secrets
import string
from urllib.parse import parse_qs, urlencode, urlparse

import requests

import onshape_api.utils as utils

__all__ = ["Onshape"]


class Onshape:
    """
    Provides access to the Onshape REST API.

    Attributes:
        - stack (str): Base URL
        - keys (str, default='./keys.json'): Credentials location
        - logging (bool, default=True): Turn logging on or off
    """

    def __init__(self, stack, keys="./keys.json", logging=True):
        """
        Instantiates an instance of the Onshape class. Reads credentials from a JSON file
        of this format:

            {
                "http://cad.onshape.com": {
                    "access_key": "YOUR KEY HERE",
                    "secret_key": "YOUR KEY HERE"
                },
                etc... add new object for each stack to test on
            }

        The keys.json file should be stored in the root project folder; optionally,
        you can specify the location of a different file.

        Args:
            - stack (str): Base URL
            - keys (str, default='./keys.json'): Credentials location
        """

        if not os.path.isfile(keys):
            raise OSError(f"{keys} is not a file")

        with open(keys) as f:
            try:
                stacks = json.load(f)
                if stack in stacks:
                    self._url = stack
                    self._access_key = stacks[stack]["access_key"]
                    self._secret_key = stacks[stack]["secret_key"]
                    self._logging = logging
                else:
                    raise ValueError("specified stack not in file")
            except TypeError as err:
                raise ValueError(f"{keys} is not valid json") from err

        if self._logging:
            utils.log(f"onshape instance created: url = {self._url}, access key = {self._access_key}")

    def _make_nonce(self):
        """
        Generate a unique ID for the request, 25 chars in length

        Returns:
            - str: Cryptographic nonce
        """

        chars = string.digits + string.ascii_letters
        nonce = "".join(secrets.choice(chars) for i in range(25))

        if self._logging:
            utils.log(f"nonce created: {nonce}")

        return nonce

    def _make_auth(self, method, date, nonce, path, query=None, ctype="application/json"):
        """
        Create the request signature to authenticate

        Args:
            - method (str): HTTP method
            - date (str): HTTP date header string
            - nonce (str): Cryptographic nonce
            - path (str): URL pathname
            - query (dict, default={}): URL query string in key-value pairs
            - ctype (str, default='application/json'): HTTP Content-Type
        """

        if query is None:
            query = {}
        query = urlencode(query)

        hmac_str = (
            (method + "\n" + nonce + "\n" + date + "\n" + ctype + "\n" + path + "\n" + query + "\n")
            .lower()
            .encode("utf-8")
        )

        signature = base64.b64encode(
            hmac.new(self._secret_key.encode("utf-8"), hmac_str, digestmod=hashlib.sha256).digest()
        )
        auth = "On " + self._access_key + ":HmacSHA256:" + signature.decode("utf-8")

        if self._logging:
            utils.log({
                "query": query,
                "hmac_str": hmac_str,
                "signature": signature,
                "auth": auth,
            })

        return auth

    def _make_headers(self, method, path, query=None, headers=None):
        """
        Creates a headers object to sign the request

        Args:
            - method (str): HTTP method
            - path (str): Request path, e.g. /api/documents. No query string
            - query (dict, default={}): Query string in key-value format
            - headers (dict, default={}): Other headers to pass in

        Returns:
            - dict: Dictionary containing all headers
        """

        if headers is None:
            headers = {}
        if query is None:
            query = {}
        date = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        nonce = self._make_nonce()
        ctype = headers.get("Content-Type") if headers.get("Content-Type") else "application/json"

        auth = self._make_auth(method, date, nonce, path, query=query, ctype=ctype)

        req_headers = {
            "Content-Type": "application/json",
            "Date": date,
            "On-Nonce": nonce,
            "Authorization": auth,
            "User-Agent": "Onshape Python Sample App",
            "Accept": "application/json",
        }

        # add in user-defined headers
        for h in headers:
            req_headers[h] = headers[h]

        return req_headers

    def request(self, method, path, query=None, headers=None, body=None, base_url=None):
        """
        Issues a request to Onshape

        Args:
            - method (str): HTTP method
            - path (str): Path  e.g. /api/documents/:id
            - query (dict, default={}): Query params in key-value pairs
            - headers (dict, default={}): Key-value pairs of headers
            - body (dict, default={}): Body for POST request
            - base_url (str, default=None): Host, including scheme and port (if different from keys file)

        Returns:
            - requests.Response: Object containing the response from Onshape
        """
        body = body or {}
        headers = headers or {}
        query = query or {}
        base_url = base_url or self._url

        req_headers = self._make_headers(method, path, query, headers)
        url = self._build_url(base_url, path, query)

        if self._logging:
            self._log_request_details(body, req_headers, url)

        body = json.dumps(body) if isinstance(body, dict) else body

        res = self._send_request(method, url, req_headers, body)

        if res.status_code == 307:
            return self._handle_redirect(res, method, headers)
        else:
            self._log_response(res)

        return res

    def _build_url(self, base_url, path, query):
        return base_url + path + "?" + urlencode(query)

    def _log_request_details(self, body, req_headers, url):
        utils.log(body)
        utils.log(req_headers)
        utils.log("request url: " + url)

    def _send_request(self, method, url, headers, body):
        return requests.request(
            method,
            url,
            headers=headers,
            data=body,
            allow_redirects=False,
            stream=True,
            timeout=10,  # Specify an appropriate timeout value in seconds
        )

    def _handle_redirect(self, res, method, headers):
        location = urlparse(res.headers["Location"])
        querystring = parse_qs(location.query)

        if self._logging:
            utils.log("request redirected to: " + location.geturl())

        new_query = {key: querystring[key][0] for key in querystring}
        new_base_url = location.scheme + "://" + location.netloc

        return self.request(
            method,
            location.path,
            query=new_query,
            headers=headers,
            base_url=new_base_url,
        )

    def _log_response(self, res):
        if not 200 <= res.status_code <= 206:
            if self._logging:
                utils.log("request failed, details: " + res.text, level=1)
        else:
            if self._logging:
                utils.log("request succeeded, details: " + res.text)
