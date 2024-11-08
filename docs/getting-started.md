Welcome to the `onshape-api` library! This guide will help you get started with using the library to interact with Onshape's REST API.

Onshape uses REST APIs to communicate with clients and third-party systems. The API calls return information in JSON format.

- **GET**: Retrieve (read) information from the server.
- **POST**: Update (write) the server with new information.
- **DELETE**: Delete information from the server.

## REST API

A typical REST API call in Onshape includes five major components:

1. **Method**: GET, POST, or DELETE.
2. **URL**: Specifies the API endpoint and part of the document that the API is calling.
3. **Query Parameters**: Optional parameters for the API call.
4. **Headers**: Defines the associated metadata, usually containing Content-Type and Accept.
5. **Payload Body**: Only applicable for POST requests.

### Example Onshape URL

Example URL: `https://cad.onshape.com/api/documents/e60c4803eaf2ac8be492c18e/w/d2558da712764516cc9fec62/e/6bed6b43463f6a46a37b4a22`

- **Base URL**: `https://cad.onshape.com/api`
- **Document ID**: `e60c4803eaf2ac8be492c18e`
- **Workspace ID**: `d2558da712764516cc9fec62`
- **Element ID**: `6bed6b43463f6a46a37b4a22`

## Authentication

To use the Onshape API, you need to authenticate your requests using your Onshape API keys. You can obtain these keys from the Onshape Developer Portal.
Once you have your keys, please create a .env file in the root directory of your project and add the following lines:

```plaintext
ACCESS_KEY = <your_access_key>
SECRET_KEY = <your_secret_key>
```
