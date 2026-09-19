# Approval Dashboard Backend

A complete Node.js backend for an Approval Dashboard application with real-time WebSocket notifications, RESTful API, and email notifications.

## Features

- **User Authentication**: JWT-based authentication with refresh tokens
- **Approval Management**: Complete CRUD operations for approval requests
- **Real-time Notifications**: WebSocket integration for instant updates
- **Email Notifications**: SMTP and SendGrid support
- **PostgreSQL Database**: Robust data persistence
- **Role-based Access Control**: User roles (user, approver, admin)
- **RESTful API**: Well-structured API endpoints
- **Security**: Helmet, rate limiting, CORS protection
- **Docker Support**: Production-ready containerization

## Tech Stack

- **Runtime**: Node.js 18+
- **Framework**: Express.js
- **Database**: PostgreSQL
- **WebSocket**: Socket.IO
- **Authentication**: JWT (jsonwebtoken)
- **Password Hashing**: bcrypt
- **Email**: Nodemailer / SendGrid
- **Security**: Helmet, express-rate-limit
- **Logging**: Morgan, Winston

## Prerequisites

- Node.js 18 or higher
- PostgreSQL 12 or higher
- npm or yarn

## Installation

1. **Clone the repository** (if not already done)

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and configure your settings:
   - Database credentials
   - JWT secret
   - Email provider settings
   - Server port and CORS origin

4. **Set up PostgreSQL database**:
   ```sql
   CREATE DATABASE approval_dashboard;
   ```

5. **Start the server**:
   ```bash
   # Development mode with auto-reload
   npm run dev

   # Production mode
   npm start
   ```

The server will automatically create all required database tables on first run.

## API Endpoints

### Authentication (`/api/v1/auth`)

- `POST /register` - Register new user
- `POST /login` - User login
- `POST /refresh-token` - Refresh access token
- `POST /logout` - User logout
- `GET /profile` - Get user profile (authenticated)
- `PUT /profile` - Update user profile (authenticated)
- `POST /change-password` - Change password (authenticated)

### Approvals (`/api/v1/approvals`)

All approval endpoints require authentication.

- `POST /` - Create new approval request
- `GET /` - Get all approvals (with filters)
- `GET /stats` - Get approval statistics
- `GET /my-approvals` - Get user's approval requests
- `GET /pending` - Get pending approvals for review
- `GET /search?q=query` - Search approvals
- `GET /:id` - Get approval by ID
- `PUT /:id` - Update approval
- `DELETE /:id` - Delete approval
- `POST /:id/review` - Approve or reject approval

## WebSocket Events

### Client to Server

- `join_approval` - Join approval room
- `leave_approval` - Leave approval room
- `typing` - User is typing
- `stop_typing` - User stopped typing
- `mark_notification_read` - Mark notification as read

### Server to Client

- `connected` - Connection established
- `new_approval` - New approval created
- `approval_updated` - Approval updated
- `approval_approved` - Approval approved
- `approval_rejected` - Approval rejected
- `approval_deleted` - Approval deleted
- `user_typing` - Another user is typing
- `user_stop_typing` - Another user stopped typing

## Database Schema

### Tables

- **users** - User accounts and profiles
- **approvals** - Approval requests
- **approval_history** - Audit trail for approvals
- **notifications** - User notifications
- **refresh_tokens** - JWT refresh tokens

## Docker Deployment

1. **Build the Docker image**:
   ```bash
   docker build -t approval-dashboard-backend .
   ```

2. **Run the container**:
   ```bash
   docker run -p 5000:5000 \
     -e DB_HOST=your-db-host \
     -e DB_PASSWORD=your-db-password \
     -e JWT_SECRET=your-jwt-secret \
     approval-dashboard-backend
   ```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `NODE_ENV` - Environment (development/production)
- `PORT` - Server port (default: 5000)
- `DB_*` - Database configuration
- `JWT_SECRET` - Secret key for JWT tokens
- `EMAIL_PROVIDER` - Email provider (smtp/sendgrid)

## Security

- JWT authentication with refresh tokens
- Password hashing with bcrypt
- Rate limiting on API endpoints
- Helmet for security headers
- CORS protection
- Input validation
- SQL injection prevention (parameterized queries)

## Development

```bash
# Install dependencies
npm install

# Run in development mode with auto-reload
npm run dev

# Run tests
npm test

# Lint code
npm run lint
```

## API Response Format

### Success Response
```json
{
  "success": true,
  "message": "Operation successful",
  "data": { ... }
}
```

### Error Response
```json
{
  "success": false,
  "message": "Error message",
  "error": "Detailed error (development only)"
}
```

## License

MIT

## Support

For issues and questions, please open an issue on the repository.
