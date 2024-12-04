"""
This module provides a client class and other utilities to interact with the Onshape API.

Class:
    - **Client**: Provides access to the Onshape REST API.
    - **Part**: Represents a part within an assembly, including its properties and configuration.
    - **PartInstance**: Represents an instance of a part within an assembly.

Enum:
    - **HTTP**: Enumerates the possible HTTP methods (GET, POST, DELETE).

"""

import base64
import datetime
import hashlib
import hmac
import os
import secrets
import string
import time
from enum import Enum
from typing import Any, BinaryIO, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv

from onshape_api.log import LOG_LEVEL, LOGGER
from onshape_api.models.assembly import Assembly
from onshape_api.models.document import BASE_URL, Document, DocumentMetaData, WorkspaceType, generate_url
from onshape_api.models.element import Element
from onshape_api.models.mass import MassProperties
from onshape_api.models.variable import Variable
from onshape_api.utilities.helpers import get_sanitized_name

__all__ = ["Client", "HTTP"]

# TODO: Add asyncio support for async requests


class HTTP(str, Enum):
    """
    Enumerates the possible HTTP methods.

    Attributes:
        GET (str): HTTP GET method
        POST (str): HTTP POST method
        DELETE (str): HTTP DELETE method

    Examples:
        >>> HTTP.GET
        'get'
        >>> HTTP.POST
        'post'
    """

    GET = "get"
    POST = "post"
    DELETE = "delete"


def load_env_variables(env: str) -> tuple[str, str]:
    """
    Load access and secret keys required for Onshape API requests from a .env file.

    Args:
        env: Path to the environment file containing the access and secret keys

    Returns:
        tuple[str, str]: Access and secret keys

    Raises:
        FileNotFoundError: If the environment file is not found
        ValueError: If the required environment variables are missing

    Examples:
        >>> load_env_variables(".env")
        ('asdagflkdfjsdlfkdfjlsdf', 'asdkkjdnknsdgkjsdguoiuosdg')
    """

    if not os.path.isfile(env):
        raise FileNotFoundError(f"{env} file not found")

    load_dotenv(env)

    access_key = os.getenv("ACCESS_KEY")
    secret_key = os.getenv("SECRET_KEY")

    if not access_key or not secret_key:
        missing_vars = [var for var in ["ACCESS_KEY", "SECRET_KEY"] if not os.getenv(var)]
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    return access_key, secret_key


def make_nonce() -> str:
    """
    Generate a unique ID for the request, 25 chars in length

    Returns:
        Cryptographic nonce string for the API request

    Examples:
        >>> make_nonce()
        'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p'
    """

    chars = string.digits + string.ascii_letters
    nonce = "".join(secrets.choice(chars) for i in range(25))
    LOGGER.debug(f"nonce created: {nonce}")

    return nonce


class Client:
    """
    Represents a client for the Onshape REST API with methods to interact with the API.

    Args:
        env (str, default='./.env'): Path to the environment file containing the access and secret keys
        log_file (str, default='./onshape_api'): Path to save the log file
        log_level (int, default=1): Log level (0-4) for the logger (0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR, 4=CRITICAL)

    Methods:
        get_document_metadata: Get details for a specified document.
        get_elements: Get list of elements in a document.
        get_variables: Get list of variables in a variable studio.
        set_variables: Set variables in a variable studio.
        get_assembly: Get assembly data for a specified document / workspace / assembly.
        download_part_stl: Download an STL file from a part studio.
        get_mass_property: Get mass properties for a part in a part studio.
        request: Issue a request to the Onshape API.

    Examples:
        >>> client = Client(
        ...     env=".env",
        ...     log_file="./onshape_api",
        ...     log_level=1
        ... )
        >>> document_meta_data = client.get_document_metadata("document_id")
    """

    def __init__(
        self, env: str = "./.env", base_url: str = BASE_URL, log_file: str = "./onshape_api", log_level: int = 1
    ):
        """
        Initialize the Onshape API client.

        Args:
            env: Path to the environment file containing the access and secret keys
            log_file: Path to save the log file
            log_level: Log level (0-4) for the logger (0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR, 4=CRITICAL)

        Examples:
            >>> client = Client(
            ...     env=".env",
            ...     log_file="./onshape_api",
            ...     log_level=1
            ... )
        """

        self._url = base_url
        self._access_key, self._secret_key = load_env_variables(env)
        LOGGER.set_file_name(log_file)
        LOGGER.set_stream_level(LOG_LEVEL[log_level])
        LOGGER.info(f"Onshape API initialized with env file: {env}")

    def get_document_metadata(self, did: str) -> DocumentMetaData:
        """
        Get meta data for a specified document.

        Args:
            did: The unique identifier of the document.

        Returns:
            Meta data for the specified document as a DocumentMetaData object or None if the document is not found

        Examples:
            >>> document_meta_data = client.get_document_metadata("document_id
            >>> print(document_meta_data)
            DocumentMetaData(
                defaultWorkspace=DefaultWorkspace(id="739221fb10c88c2bebb456e8", type="workspace"),
                name="Document Name",
                id="a1c1addf75444f54b504f25c"
            )
        """
        if len(did) != 24:
            raise ValueError(f"Invalid document ID: {did}")

        res = self.request(HTTP.GET, "/api/documents/" + did)

        if res.status_code == 404:
            """
            404: Document not found
                {
                    "message": "Not found.",
                    "code": 0,
                    "status": 404,
                    "moreInfoUrl": ""
                }
            """
            raise ValueError(f"Document does not exist: {did}")
        elif res.status_code == 403:
            """
            403: Forbidden
                {
                    "message": "Forbidden",
                    "code": 0,
                    "status": 403,
                    "moreInfoUrl": ""
                }
            """
            raise ValueError(f"Access forbidden for document: {did}")

        _document = DocumentMetaData.model_validate(res.json())
        _document.name = get_sanitized_name(_document.name)

        return _document

    def get_elements(self, did: str, wtype: str, wid: str) -> dict[str, Element]:
        """
        Get a list of all elements in a document.

        Args:
            did: The unique identifier of the document.
            wtype: The type of workspace.
            wid: The unique identifier of the workspace.

        Returns:
            A dictionary of element name and Element object pairs.

        Examples:
            >>> elements = client.get_elements(
            ...     did="a1c1addf75444f54b504f25c",
            ...     wtype="w",
            ...     wid="0d17b8ebb2a4c76be9fff3c7"
            ... )
            >>> print(elements)
            {
                "wheelAndFork": Element(id='0b0c209535554345432581fe', name='wheelAndFork', elementType='PARTSTUDIO',
                                         microversionId='9b3be6165c7a2b1f6dd61305'),
                "frame": Element(id='0b0c209535554345432581fe', name='frame', elementType='PARTSTUDIO',
                                 microversionId='9b3be6165c7a2b1f6dd61305')
            }
        """

        # /documents/d/{did}/{wvm}/{wvmid}/elements
        _request_path = "/api/documents/d/" + did + "/" + wtype + "/" + wid + "/elements"
        _elements_json = self.request(
            HTTP.GET,
            _request_path,
        ).json()

        return {element["name"]: Element.model_validate(element) for element in _elements_json}

    def get_variables(self, did: str, wid: str, eid: str) -> dict[str, Variable]:
        """
        Get a list of variables in a variable studio within a document.

        Args:
            did: The unique identifier of the document.
            wid: The unique identifier of the workspace.
            eid: The unique identifier of the variable studio.

        Returns:
            A dictionary of variable name and Variable object pairs.

        Examples:
            >>> variables = client.get_variables(
            ...     did="a1c1addf75444f54b504f25c",
            ...     wid="0d17b8ebb2a4c76be9fff3c7",
            ...     eid="cba5e3ca026547f34f8d9f0f"
            ... )
            >>> print(variables)
            {
                "forkAngle": Variable(
                    type='ANGLE',
                    name='forkAngle',
                    value=None,
                    description='Fork angle for front wheel assembly in deg',
                    expression='15 deg'
                )
            }
        """
        _request_path = "/api/variables/d/" + did + "/w/" + wid + "/e/" + eid + "/variables"

        _variables_json = self.request(
            HTTP.GET,
            _request_path,
        ).json()

        return {variable["name"]: Variable.model_validate(variable) for variable in _variables_json[0]["variables"]}

    def set_variables(self, did: str, wid: str, eid: str, variables: dict[str, str]) -> requests.Response:
        """
        Set values for variables of a variable studio in a document.

        Args:
            did: The unique identifier of the document.
            wid: The unique identifier of the workspace.
            eid: The unique identifier of the variable studio.
            variables: A dictionary of variable name and expression pairs.

        Returns:
            requests.Response: Response from Onshape API after setting the variables.

        Examples:
            >>> variables = {
            ...     "forkAngle": "15 deg",
            ...     "wheelRadius": "0.5 m"
            ... }
            >>> client.set_variables(
            ...     did="a1c1addf75444f54b504f25c",
            ...     wid="0d17b8ebb2a4c76be9fff3c7",
            ...     eid="cba5e3ca026547f34f8d9f0f",
            ...     variables=variables
            ... )
            <Response [200]>
        """

        payload = [variable.model_dump() for variable in variables.values()]

        # api/v9/variables/d/a1c1addf75444f54b504f25c/w/0d17b8ebb2a4c76be9fff3c7/e/cba5e3ca026547f34f8d9f0f/variables
        _request_path = "/api/variables/d/" + did + "/w/" + wid + "/e/" + eid + "/variables"

        return self.request(
            HTTP.POST,
            _request_path,
            body=payload,
        )

    def get_assembly_name(
        self,
        did: str,
        wtype: str,
        wid: str,
        eid: str,
        configuration: str = "default",
    ) -> str:
        """
        Get assembly name for a specified document / workspace / assembly.

        Args:
            did: The unique identifier of the document.
            wtype: The type of workspace.
            wid: The unique identifier of the workspace.
            eid: The unique identifier of the assembly.

        Returns:
            str: Assembly name

        Examples:
            >>> assembly_name = client.get_assembly_name(
            ...     did="a1c1addf75444f54b504f25c",
            ...     wtype="w",
            ...     wid="0d17b8ebb2a4c76be9fff3c7",
            ...     eid="a86aaf34d2f4353288df8812"
            ... )
            >>> print(assembly_name)
            "Assembly Name"
        """
        _request_path = "/api/metadata/d/" + did + "/" + wtype + "/" + wid + "/e/" + eid
        result_json = self.request(
            HTTP.GET,
            _request_path,
            query={
                "inferMetadataOwner": "false",
                "includeComputedProperties": "false",
                "includeComputedAssemblyProperties": "false",
                "thumbnail": "false",
                "configuration": configuration,
            },
            log_response=False,
        ).json()

        name = None
        try:
            name = result_json["properties"][0]["value"]
            name = get_sanitized_name(name)

        except KeyError:
            LOGGER.warning(f"Assembly name not found for document: {did}")

        return name

    def get_assembly(
        self,
        did: str,
        wtype: str,
        wid: str,
        eid: str,
        configuration: str = "default",
        log_response: bool = True,
        with_meta_data: bool = False,
    ) -> tuple[Assembly, dict]:
        """
        Get assembly data for a specified document / workspace / assembly.

        Args:
            did: The unique identifier of the document.
            wtype: The type of workspace.
            wid: The unique identifier of the workspace.
            eid: The unique identifier of the assembly.
            configuration: The configuration of the assembly.
            log_response: Log the response from the API request.
            with_meta_data: Include meta data in the assembly data.

        Returns:
            Assembly: Assembly object containing the assembly data
            dict: Assembly data in JSON format

        Examples:
            >>> assembly, _ = client.get_assembly(
            ...     did="a1c1addf75444f54b504f25c",
            ...     wtype="w",
            ...     wid="0d17b8ebb2a4c76be9fff3c7",
            ...     eid="a86aaf34d2f4353288df8812"
            ... )
            >>> print(assembly)
            Assembly(
                rootAssembly=RootAssembly(
                    instances=[...],
                    patterns=[...],
                    features=[...],
                    occurrences=[...],
                    fullConfiguration="default",
                    configuration="default",
                    documentId="a1c1addf75444f54b504f25c",
                    elementId="0b0c209535554345432581fe",
                    documentMicroversion="349f6413cafefe8fb4ab3b07",
                ),
                subAssemblies=[...],
                parts=[...],
                partStudioFeatures=[...],
                document=Document(
                    url="https://cad.onshape.com/documents/a1c1addf75444f54b504f25c/w/0d17b8ebb2a4c76be9fff3c7/e/a86aaf34d2f4353288df8812",
                    did="a1c1addf75444f54b504f25c",
                    wtype="w",
                    wid="0d17b8ebb2a4c76be9fff3c7",
                    eid="a86aaf34d2f4353288df8812"
                )
            )
        """
        _request_path = "/api/assemblies/d/" + did + "/" + wtype + "/" + wid + "/e/" + eid
        _res = self.request(
            HTTP.GET,
            _request_path,
            query={
                "includeMateFeatures": "true",
                "includeMateConnectors": "true",
                "includeNonSolids": "false",
                "configuration": configuration,
            },
            log_response=log_response,
        )

        if _res.status_code == 401:
            LOGGER.warning(f"Unauthorized access to document: {did}")
            LOGGER.warning("Please check the API keys in your env file.")
            exit(1)

        _assembly_json = _res.json()

        _assembly = Assembly.model_validate(_assembly_json)
        _document = Document(did=did, wtype=wtype, wid=wid, eid=eid)
        _assembly.document = _document

        if with_meta_data:
            _assembly.name = self.get_assembly_name(did, wtype, wid, eid, configuration)
            _document_meta_data = self.get_document_metadata(did)
            _assembly.document.name = _document_meta_data.name

        return _assembly, _assembly_json

    def download_assembly_stl(
        self,
        did: str,
        wid: str,
        eid: str,
        buffer: BinaryIO,
        wtype: str = WorkspaceType.W.value,
        vid: Optional[str] = None,
        configuration: str = "default",
    ):
        """
        Download an STL file from an assembly. The file is written to the buffer.

        Args:
            did: The unique identifier of the document.
            wtype: The type of workspace.
            wid: The unique identifier of the workspace.
            eid: The unique identifier of the element.
            vid: The unique identifier of the version workspace.
            configuration: The configuration of the assembly.

        """
        req_headers = {"Accept": "application/vnd.onshape.v1+octet-stream"}
        _request_path = (
            f"/api/assemblies/d/{did}/{wtype}/" f"{wid if wtype == WorkspaceType.W else vid}/e/{eid}/translations"
        )

        # Initiate the translation
        payload = {
            "formatName": "STL",
            "storeInDocument": "false",
        }
        response = self.request(
            HTTP.POST,
            path=_request_path,
            body=payload,
        )

        if response.status_code == 200:
            job_info = response.json()
            translation_id = job_info.get("id")
            if not translation_id:
                LOGGER.error("Translation job ID not found in response.")
                return None

            status_path = f"/api/translations/{translation_id}"
            while True:
                status_response = self.request(HTTP.GET, path=status_path)
                if status_response.status_code != 200:
                    LOGGER.error(f"Failed to get translation status: {status_response.text}")
                    return None

                status_info = status_response.json()
                request_state = status_info.get("requestState")
                LOGGER.info(f"Current status: {request_state}")
                if request_state == "DONE":
                    LOGGER.info("Translation job completed.")
                    break
                elif request_state == "FAILED":
                    LOGGER.error("Translation job failed.")
                    return None
                time.sleep(1)

            fid = status_info.get("resultExternalDataIds")[0]
            data_path = f"/api/documents/d/{did}/externaldata/{fid}"

            download_response = self.request(
                HTTP.GET,
                path=data_path,
                headers=req_headers,
            )
            if download_response.status_code == 200:
                buffer.write(download_response.content)
                LOGGER.info("STL file downloaded successfully.")
                return buffer
            else:
                LOGGER.error(f"Failed to download STL file: {download_response.text}")
                return None

        elif response.status_code in (404, 400):
            if vid and wtype == WorkspaceType.W:
                return self.download_assembly_stl(did, WorkspaceType.V.value, wid, eid, vid)
            else:
                LOGGER.info(f"Failed to download assembly: {response.status_code} - {response.text}")
                LOGGER.info(
                    generate_url(
                        base_url=self._url,
                        did=did,
                        wtype="w",
                        wid=wid,
                        eid=eid,
                    )
                )
        else:
            LOGGER.error(f"Unexpected error: {response.status_code} - {response.text}")

        return buffer

    def download_part_stl(
        self,
        did: str,
        wid: str,
        eid: str,
        partID: str,
        buffer: BinaryIO,
        wtype: str = WorkspaceType.W.value,
        vid: Optional[str] = None,
    ) -> BinaryIO:
        """
        Download an STL file from a part studio. The file is written to the buffer.

        Args:
            did: The unique identifier of the document.
            wid: The unique identifier of the workspace.
            eid: The unique identifier of the element.
            partID: The unique identifier of the part.
            buffer: BinaryIO object to write the STL file to.
            wtype: The type of workspace.
            vid: The unique identifier of the version workspace.

        Returns:
            BinaryIO: BinaryIO object containing the STL file

        Examples:
            >>> with io.BytesIO() as buffer:
            ...     client.download_part_stl(
            ...         "a1c1addf75444f54b504f25c",
            ...         "0d17b8ebb2a4c76be9fff3c7",
            ...         "a86aaf34d2f4353288df8812",
            ...         "0b0c209535554345432581fe",
            ...         buffer,
            ...         "w",
            ...         "0d17b8ebb2a4c76be9fff3c7"
            ...     )
            >>> buffer.seek(0)
            >>> raw_mesh = stl.mesh.Mesh.from_file(None, fh=buffer)
            >>> raw_mesh.save("mesh.stl")
        """
        # TODO: version id seems to always work, should this default behavior be changed?

        req_headers = {"Accept": "application/vnd.onshape.v1+octet-stream"}
        _request_path = (
            f"/api/parts/d/{did}/{wtype}/" f"{wid if wtype == WorkspaceType.W else vid}/e/{eid}/partid/{partID}/stl"
        )
        _query = {
            "mode": "binary",
            "grouping": True,
            "units": "meter",
        }
        response = self.request(
            HTTP.GET,
            path=_request_path,
            headers=req_headers,
            query=_query,
            log_response=False,
        )
        if response.status_code == 200:
            buffer.write(response.content)
        elif response.status_code == 404 or response.status_code == 400:
            if vid and wtype == WorkspaceType.W:
                return self.download_part_stl(did, wid, eid, partID, buffer, WorkspaceType.V.value, vid)
            else:
                LOGGER.info(f"{
                    generate_url(
                        base_url=self._url,
                        did=did,
                        wtype="w",
                        wid=wid,
                        eid=eid,
                    )
                }")
                LOGGER.info(
                    f"No version ID provided, failed to download STL file: {response.status_code} - {response.text}"
                )

        else:
            LOGGER.info(f"{
                generate_url(
                    base_url=self._url,
                    did=did,
                    wtype="w",
                    wid=wid,
                    eid=eid,
                )
            }")
            LOGGER.info(f"Failed to download STL file: {response.status_code} - {response.text}")

        return buffer

    def get_assembly_mass_properties(
        self, did: str, wid: str, eid: str, vid: Optional[str] = None, wtype: str = WorkspaceType.W.value
    ) -> MassProperties:
        """
        Get mass properties of a rigid assembly in a document.

        Args:
            did: The unique identifier of the document.
            wid: The unique identifier of the workspace.
            eid: The unique identifier of the rigid assembly.
            vid: The unique identifier of the document version.
            wtype: The type of workspace.

        Returns:
            MassProperties object containing the mass properties of the assembly.

        Examples:
            >>> mass_properties = client.get_assembly_mass_properties(
            ...     did="a1c1addf75444f54b504f25c",
            ...     wid="0d17b8ebb2a4c76be9fff3c7",
            ...     eid="a86aaf34d2f4353288df8812",
            ...     vid="0d17bae7b2a4c76be9fff3c7",
            ...     wtype="w"
            ... )
            >>> print(mass_properties)
            MassProperties(
                volume=[0.003411385108378978, 0.003410724395374695, 0.0034120458213832646],
                mass=[9.585992154544929, 9.584199206938452, 9.587785102151415],
                centroid=[...],
                inertia=[...],
                principalInertia=[0.09944605933465941, 0.09944605954654827, 0.19238058837442526],
                principalAxes=[...]
            )
        """
        _request_path = (
            f"/api/assemblies/d/{did}/{wtype}/" f"{wid if wtype == WorkspaceType.W else vid}/e/{eid}/massproperties"
        )
        res = self.request(HTTP.GET, _request_path, log_response=False)

        if res.status_code == 404:
            if vid and wtype == WorkspaceType.W:
                return self.get_assembly_mass_properties(did, wid, eid, vid, WorkspaceType.V.value)

            url = generate_url(
                base_url=self._url,
                did=did,
                wtype="w",
                wid=wid,
                eid=eid,
            )
            raise ValueError(f"Assembly: {url} does not have a mass property")

        return MassProperties.model_validate(res.json())

    def get_mass_property(
        self, did: str, wid: str, eid: str, partID: str, vid: Optional[str], wtype: str = WorkspaceType.W.value
    ) -> MassProperties:
        """
        Get mass properties of a part in a part studio.

        Args:
            did: The unique identifier of the document.
            wid: The unique identifier of the workspace.
            eid: The unique identifier of the element.
            partID: The identifier of the part.
            vid: The unique identifier of the document version.
            wtype: The type of workspace.

        Returns:
            MassProperties object containing the mass properties of the part.

        Examples:
            >>> mass_properties = client.get_mass_property(
            ...     did="a1c1addf75444f54b504f25c",
            ...     wid="0d17b8ebb2a4c76be9fff3c7",
            ...     eid="a86aaf34d2f4353288df8812",
            ...     partID="0b0c209535554345432581fe"
            ...     vid="0d17bae7b2a4c76be9fff3c7",
            ...     wtype="w"
            ... )
            >>> print(mass_properties)
            MassProperties(
                volume=[0.003411385108378978, 0.003410724395374695, 0.0034120458213832646],
                mass=[9.585992154544929, 9.584199206938452, 9.587785102151415],
                centroid=[...],
                inertia=[...],
                principalInertia=[0.09944605933465941, 0.09944605954654827, 0.19238058837442526],
                principalAxes=[...]
            )
        """
        # TODO: version id seems to always work, should this default behavior be changed?
        _request_path = (
            f"/api/parts/d/{did}/{wtype}/"
            f"{wid if wtype == WorkspaceType.W else vid}/e/{eid}/partid/{partID}/massproperties"
        )
        res = self.request(HTTP.GET, _request_path, {"useMassPropertiesOverrides": True}, log_response=False)

        if res.status_code == 404:
            # TODO: There doesn't seem to be a way to assign material to a part currently
            # It is possible that the workspace got deleted
            if vid and wtype == WorkspaceType.W:
                return self.get_mass_property(did, wid, eid, partID, vid, WorkspaceType.V.value)

            raise ValueError(f"Part: {
                generate_url(
                    base_url=self._url,
                    did=did,
                    wtype="w",
                    wid=wid,
                    eid=eid,
                )
            } does not have a material assigned or the part is not found")

        _resonse_json = res.json()

        if "bodies" not in _resonse_json:
            raise KeyError(f"Bodies not found in response, broken part? {partID}")

        return MassProperties.model_validate(_resonse_json["bodies"][partID])

    def request(
        self,
        method: HTTP,
        path: str,
        query: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
        body: Optional[dict[str, Any]] = None,
        base_url: Optional[str] = None,
        log_response: bool = True,
        timeout: int = 20,
    ) -> requests.Response:
        """
        Send a request to the Onshape API.

        Args:
            method: HTTP method (GET, POST, DELETE)
            path: URL path for the request
            query: Query string in key-value pairs
            headers: Additional headers for the request
            body: Body of the request
            base_url: Base URL for the request
            log_response: Log the response from the API request

        Returns:
            requests.Response: Response from the Onshape API request
        """
        if query is None:
            query = {}
        if headers is None:
            headers = {}
        if base_url is None:
            base_url = self._url

        req_headers = self._make_headers(method, path, query, headers)
        url = self._build_url(base_url, path, query)

        LOGGER.debug(f"Request body: {body}")
        LOGGER.debug(f"Request headers: {req_headers}")
        LOGGER.debug(f"Request URL: {url}")

        res = self._send_request(method, url, req_headers, body, timeout)

        if res.status_code == 307:
            return self._handle_redirect(res, method, headers, log_response)
        else:
            if log_response:
                self._log_response(res)

        return res

    def _build_url(self, base_url, path, query):
        return base_url + path + "?" + urlencode(query)

    def _send_request(self, method, url, headers, body, timeout):
        return requests.request(
            method,
            url,
            headers=headers,
            json=body,
            allow_redirects=False,
            stream=True,
            timeout=timeout,  # Specify an appropriate timeout value in seconds
        )

    def _handle_redirect(self, res, method, headers, log_response=True):
        location = urlparse(res.headers["Location"])
        querystring = parse_qs(location.query)

        LOGGER.debug(f"Request redirected to: {location.geturl()}")

        new_query = {key: querystring[key][0] for key in querystring}
        new_base_url = location.scheme + "://" + location.netloc

        return self.request(
            method, location.path, query=new_query, headers=headers, base_url=new_base_url, log_response=log_response
        )

    def _log_response(self, res):
        try:
            if not 200 <= res.status_code <= 206:
                LOGGER.debug(f"Request failed, details: {res.text}")
            else:
                LOGGER.debug(f"Request succeeded, details: {res.text}")
        except UnicodeEncodeError as e:
            LOGGER.error(f"UnicodeEncodeError: {e}")

    def _make_auth(self, method, date, nonce, path, query=None, ctype="application/json"):
        if query is None:
            query = {}
        query = urlencode(query)

        hmac_str = (
            str(method + "\n" + nonce + "\n" + date + "\n" + ctype + "\n" + path + "\n" + query + "\n")
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
