import base64
import datetime
import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import string
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv

from onshape_api.utilities import LOG_LEVEL, LOGGER

__all__ = ["Client"]

"""
client
======

Convenience functions for working with the Onshape API
"""

# TODO: Add asyncio support for async requests


def load_env_variables(env):
    """
    Load environment variables from the specified .env file.

    Args:
        env (str): Path to the .env file.

    Returns:
        tuple: A tuple containing the URL, ACCESS_KEY, and SECRET_KEY.

    Raises:
        FileNotFoundError: If the .env file does not exist.
        ValueError: If any of the required environment variables are missing.
    """
    if not os.path.isfile(env):
        raise FileNotFoundError(f"{env} file not found")

    load_dotenv(env)

    url = os.getenv("URL")
    access_key = os.getenv("ACCESS_KEY")
    secret_key = os.getenv("SECRET_KEY")

    if not url or not access_key or not secret_key:
        missing_vars = [var for var in ["URL", "ACCESS_KEY", "SECRET_KEY"] if not os.getenv(var)]
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    return url, access_key, secret_key


def make_nonce():
    """
    Generate a unique ID for the request, 25 chars in length

    Returns:
        - str: Cryptographic nonce
    """

    chars = string.digits + string.ascii_letters
    nonce = "".join(secrets.choice(chars) for i in range(25))
    LOGGER.debug(f"nonce created: {nonce}")

    return nonce


class Client:
    """
    Provides access to the Onshape REST API.

    Attributes:
        - env (str, default='./.env'): Location of the environment file
        - logging (bool, default=True): Turn logging on or off
    """

    def __init__(self, env="./.env", log_file="./onshape.log", log_level=1):
        """
        Instantiates an instance of the Onshape class. Reads credentials from a .env file.

        The .env file should be stored in the root project folder; optionally,
        you can specify the location of a different file.

        Args:
            - env (str, default='./.env'): Environment file location
        """

        self._url, self._access_key, self._secret_key = load_env_variables(env)
        LOGGER.set_file_name(log_file)
        LOGGER.set_stream_level(LOG_LEVEL[log_level])
        LOGGER.info(f"Onshape API initialized with env file: {env}")

    def new_document(self, name="Test Document", owner_type=0, public=False):
        """
        Create a new document.

        Args:
            - name (str, default='Test Document'): The doc name
            - owner_type (int, default=0): 0 for user, 1 for company, 2 for team
            - public (bool, default=False): Whether or not to make doc public

        Returns:
            - requests.Response: Onshape response data
        """

        payload = {"name": name, "ownerType": owner_type, "isPublic": public}

        return self.request("post", "/api/documents", body=payload)

    def rename_document(self, did, name):
        """
        Renames the specified document.

        Args:
            - did (str): Document ID
            - name (str): New document name

        Returns:
            - requests.Response: Onshape response data
        """

        payload = {"name": name}

        return self.request("post", "/api/documents/" + did, body=payload)

    def del_document(self, did):
        """
        Delete the specified document.

        Args:
            - did (str): Document ID

        Returns:
            - requests.Response: Onshape response data
        """

        return self.request("delete", "/api/documents/" + did)

    def get_document(self, did):
        """
        Get details for a specified document.

        Args:
            - did (str): Document ID

        Returns:
            - requests.Response: Onshape response data
        """

        return self.request("get", "/api/documents/" + did)

    def list_documents(self):
        """
        Get list of documents for current user.

        Returns:
            - requests.Response: Onshape response data
        """

        return self.request("get", "/api/documents")

    def create_assembly(self, did, wid, name="My Assembly"):
        """
        Creates a new assembly element in the specified document / workspace.

        Args:
            - did (str): Document ID
            - wid (str): Workspace ID
            - name (str, default='My Assembly')

        Returns:
            - requests.Response: Onshape response data
        """

        payload = {"name": name}

        return self.request("post", "/api/assemblies/d/" + did + "/w/" + wid, body=payload)

    def get_features(self, did, wid, eid):
        """
        Gets the feature list for specified document / workspace / part studio.

        Args:
            - did (str): Document ID
            - wid (str): Workspace ID
            - eid (str): Element ID

        Returns:
            - requests.Response: Onshape response data
        """

        return self.request("get", "/api/partstudios/d/" + did + "/w/" + wid + "/e/" + eid + "/features")

    def get_partstudio_tessellatededges(self, did, wid, eid):
        """
        Gets the tessellation of the edges of all parts in a part studio.

        Args:
            - did (str): Document ID
            - wid (str): Workspace ID
            - eid (str): Element ID

        Returns:
            - requests.Response: Onshape response data
        """

        return self.request(
            "get",
            "/api/partstudios/d/" + did + "/w/" + wid + "/e/" + eid + "/tessellatededges",
        )

    def upload_blob(self, did, wid, filepath="./blob.json"):
        """
        Uploads a file to a new blob element in the specified doc.

        Args:
            - did (str): Document ID
            - wid (str): Workspace ID
            - filepath (str, default='./blob.json'): Blob element location

        Returns:
            - requests.Response: Onshape response data
        """

        chars = string.ascii_letters + string.digits
        boundary_key = "".join(secrets.choice(chars) for i in range(8))

        mimetype = mimetypes.guess_type(filepath)[0]
        encoded_filename = os.path.basename(filepath)
        file_content_length = str(os.path.getsize(filepath))
        blob = open(filepath)

        req_headers = {"Content-Type": f'multipart/form-data; boundary="{boundary_key}"'}

        # build request body
        payload = (
            "--"
            + boundary_key
            + '\r\nContent-Disposition: form-data; name="encodedFilename"\r\n\r\n'
            + encoded_filename
            + "\r\n"
        )
        payload += (
            "--"
            + boundary_key
            + '\r\nContent-Disposition: form-data; name="fileContentLength"\r\n\r\n'
            + file_content_length
            + "\r\n"
        )
        payload += (
            "--"
            + boundary_key
            + '\r\nContent-Disposition: form-data; name="file"; filename="'
            + encoded_filename
            + '"\r\n'
        )
        payload += "Content-Type: " + mimetype + "\r\n\r\n"
        payload += blob.read()
        payload += "\r\n--" + boundary_key + "--"

        return self.request(
            "post",
            "/api/blobelements/d/" + did + "/w/" + wid,
            headers=req_headers,
            body=payload,
        )

    def part_studio_stl(self, did, wid, eid):
        """
        Exports STL export from a part studio

        Args:
            - did (str): Document ID
            - wid (str): Workspace ID
            - eid (str): Element ID

        Returns:
            - requests.Response: Onshape response data
        """

        req_headers = {"Accept": "application/vnd.onshape.v1+octet-stream"}
        return self.request(
            "get",
            "/api/partstudios/d/" + did + "/w/" + wid + "/e/" + eid + "/stl",
            headers=req_headers,
        )

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

        LOGGER.debug(f"query: {query}, hmac_str: {hmac_str}, signature: {signature}, auth: {auth}")

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
        nonce = make_nonce()
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

        LOGGER.debug(f"{body}")
        LOGGER.debug(f"{req_headers}")
        LOGGER.debug(f"request url: {url}")

        body = json.dumps(body) if isinstance(body, dict) else body

        res = self._send_request(method, url, req_headers, body)

        if res.status_code == 307:
            return self._handle_redirect(res, method, headers)
        else:
            self._log_response(res)

        return res

    def _build_url(self, base_url, path, query):
        return base_url + path + "?" + urlencode(query)

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

        LOGGER.debug(f"Request redirected to: {location.geturl()}")

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
            LOGGER.debug(f"Request failed, details: {res.text}")
        else:
            LOGGER.debug(f"Request succeeded, details: {res.text}")
