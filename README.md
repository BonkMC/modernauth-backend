# ModernAuth

ModernAuth is a Python-based authentication and user management system built using Flask for offline-mode minecraft servers. It provides features such as user linking, admin management, and secure token handling.

## Features

- **User Authentication**: Secure user login and session management.
- **Account Linking**: Link accounts from external providers (e.g., Google).
- **Admin Panel**: Manage users and servers with admin privileges.
- **Token Management**: Securely handle and validate tokens.
- **Server Configuration**: Manage server-specific settings and access.

## Requirements

- Please run pip install -r requirements.txt to install the required packages.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/modernauth.git
   cd modernauth
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Make a copy of `.env.example` and rename it to `.env`. Fill in the required values. More info on this will be added soon.

4. Run the application:
   ```bash
   python src/modernauth/app.py
   ```

## Usage

- Access the application at `http://localhost:3000`.
- Admin panel is available at `/admin`.
- To manage the application, run the following command to get help:
  ```bash
  modernauth
  ```
- API endpoints:
  - `/api/isuser/<server_id>/<username>`: Check if a user exists.
  - `/api/authstatus`: Check the authentication status.
  - `/api/createtoken`: Create a new token.

## Documentation

For detailed documentation, visit [https://docs.bonkmc.org](https://docs.bonkmc.org).

## Production Deployment

The production site is hosted at [https://auth.bonkmc.org](https://auth.bonkmc.org).

## Spigot and Velocity Plugins for Usage

Spigot Plugin GitHub: https://github.com/bonknetwork/modernauth-spigot
Velocity Plugin GitHub: https://guthub.com/bonknetwork/modernauth-velocity

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
```