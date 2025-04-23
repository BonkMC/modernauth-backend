Welcome to the ModernAuth API docs!
===========================================

.. raw:: html

   <div class="github-buttons">
     <a class="btn-backend"
        href="https://github.com/bonknetwork/modernauth-backend"
        target="_blank">
       Backend<br>GitHub<br>
     </a>
     <a class="btn-spigot"
        href="https://github.com/bonknetwork/modernauth-spigot"
        target="_blank">
       Spigot Plugin GitHub<br>
     </a>
     <a class="btn-velocity"
        href="https://github.com/bonknetwork/modernauth-velocity"
        target="_blank">
       Velocity Plugin GitHub<br>
     </a>
     <a class="btn-org"
        href="https://github.com/bonknetwork/"
        target="_blank">
       Organization GitHub
     </a>
   </div>

This documentation details the HTTP endpoints provided by the ModernAuthentication plugin, which is compatible with both Spigot and Velocity servers. These endpoints facilitate a web-based login system for Minecraft players, enhancing account security and ease of access.

The endpoints are accessible to all users, whether they are working with their own clones of the project or using the public deployment available at https://auth.bonkmc.org.

The backend system is designed with flexibility in mind: anyone with a valid access code can develop their own plugin implementation. This allows server owners and developers to customize their authentication workflow while still relying on the robust and secure core authentication infrastructure provided by ModernAuthentication.

.. toctree::
   :maxdepth: 2
   :caption: API Endpoints

   create_token
   auth_status
   is_user
