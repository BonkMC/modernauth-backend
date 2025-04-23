Create Token
============

**Endpoint:** ``/api/createtoken``
**Method:** ``POST``

Description
-----------

Invoked by the Spigot plugin when a player starts the authentication process.
Creates a unique token tied to the player’s username and server ID, stores it
in the backend’s token system, and later verifies web login.

Request Headers
---------------

- ``Content-Type: application/json``
- ``X-Server-Secret: <your-secret>``

Request Body
------------

Send JSON with:

.. code-block:: json

   {
     "server_id": "your-server-id",
     "token": "unique-generated-token",
     "username": "player_username"
   }

Response
--------

Returns a generic JSON payload:

.. code-block:: json

   {
     "message": "If your token is valid, you will see the appropriate behavior."
   }

Usage in the Plugin
-------------------

After generating a token, the plugin calls this endpoint and sends the player
a URL to complete web login:

::

  https://<your-domain>/auth/<server_id>/<token>?username=<player_username>
