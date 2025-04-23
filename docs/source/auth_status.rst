Authentication Status
=====================

**Endpoint:** ``/api/authstatus/<server_id>/<token>``
**Method:** ``GET``

Description
-----------

Polled by the plugin to check if the user has completed authentication in
their browser. Your plugin’s repeating task hits this endpoint until login
succeeds.

Request Headers
---------------

- ``X-Server-Secret: <your-secret>``

Response
--------

On success:

.. code-block:: json

   {
     "logged_in": true
   }

Otherwise:

.. code-block:: json

   {
     "logged_in": false
   }

Usage in the Plugin
-------------------

When ``"logged_in": true``, the plugin forces the Minecraft login, registers
the player if new, and updates the password if needed.
