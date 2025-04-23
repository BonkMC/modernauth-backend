User Existence Check
====================

**Endpoint:** ``/api/isuser/<server_id>/<username>``
**Method:** ``GET``

Description
-----------

Checks whether a username is already registered on the backend for
the given server. Used at player join to choose the correct flow.

Response
--------

If the user exists:

.. code-block:: json

   {
     "exists": true
   }

Otherwise:

.. code-block:: json

   {
     "exists": false
   }

Usage in the Plugin
-------------------

If ``"exists": false``, the plugin defers confirmation so the player can
switch to the new authentication system; otherwise it proceeds normally.
