# Approval Dashboard Frontend

Modern, responsive React application for managing approval workflows with real-time updates.

## Features

- **Authentication**: JWT-based login and registration
- **Real-time Updates**: WebSocket integration for live approval status changes
- **Role-Based Access**: Different UI/actions based on user roles (Requester, Approver, Admin)
- **Material-UI Design**: Clean, professional interface with Material Design
- **Responsive**: Mobile-friendly design that works on all devices
- **Toast Notifications**: Real-time feedback for all actions
- **CRUD Operations**: Create, read, update, and delete approvals
- **Advanced Filtering**: Search, filter by status, priority, and type
- **Approval Actions**: Approve, reject, and rollback functionality
- **History Tracking**: View complete approval history

## Technology Stack

- **React 18** - UI framework
- **React Router v6** - Client-side routing
- **Material-UI (MUI)** - Component library
- **Axios** - HTTP client
- **Socket.IO Client** - Real-time WebSocket communication
- **React Toastify** - Toast notifications
- **date-fns** - Date formatting utilities
- **jwt-decode** - JWT token decoding

## Prerequisites

- Node.js 16+ and npm
- Backend API running on http://localhost:5000 (or configure `REACT_APP_API_URL`)

## Installation

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set your backend API URL:
   ```env
   REACT_APP_API_URL=http://localhost:5000/api
   REACT_APP_SOCKET_URL=http://localhost:5000
   ```

## Development

Start the development server:

```bash
npm start
```

The application will open at http://localhost:3000

## Building for Production

Create an optimized production build:

```bash
npm run build
```

The build files will be in the `build/` directory.

## Docker Deployment

### Build Docker Image

```bash
docker build -t approval-dashboard-frontend .
```

### Run Container

```bash
docker run -p 80:80 \
  -e REACT_APP_API_URL=http://your-backend-api:5000/api \
  -e REACT_APP_SOCKET_URL=http://your-backend-api:5000 \
  approval-dashboard-frontend
```

### Docker Compose

The frontend is designed to work with Docker Compose. See the main `docker-compose.yml` in the parent directory.

## Project Structure

```
frontend/
├── public/
│   └── index.html              # HTML template
├── src/
│   ├── components/             # Reusable components
│   │   ├── ApprovalActions.jsx # Approve/Reject/Rollback buttons
│   │   ├── ApprovalCard.jsx    # Approval card component
│   │   ├── ApprovalForm.jsx    # Create/Edit form
│   │   ├── Header.jsx          # Navigation header
│   │   └── NotificationBell.jsx # Real-time notifications
│   ├── context/                # React Context providers
│   │   ├── AuthContext.jsx     # Authentication state
│   │   └── NotificationContext.jsx # Notification state
│   ├── hooks/                  # Custom React hooks
│   │   └── useApprovals.js     # Approval data hook
│   ├── pages/                  # Page components
│   │   ├── ApprovalDetailPage.jsx # Single approval view
│   │   ├── DashboardPage.jsx   # Main dashboard
│   │   └── LoginPage.jsx       # Login/Register
│   ├── services/               # API and WebSocket services
│   │   ├── api.js              # Axios HTTP client
│   │   └── websocket.js        # Socket.IO client
│   ├── styles/                 # Global styles
│   │   └── App.css             # Main stylesheet
│   ├── App.jsx                 # Main app component
│   └── index.jsx               # React entry point
├── .dockerignore               # Docker ignore file
├── .env.example                # Environment variables template
├── Dockerfile                  # Docker build configuration
├── nginx.conf                  # NGINX configuration
├── package.json                # Dependencies and scripts
└── README.md                   # This file
```

## Key Components

### Authentication
- **AuthContext**: Manages user authentication state
- **LoginPage**: Login and registration forms
- JWT token stored in localStorage
- Automatic token validation and refresh

### Real-time Updates
- **WebSocket Service**: Singleton WebSocket connection
- **NotificationContext**: Manages real-time notifications
- **NotificationBell**: Displays unread notifications
- Auto-reconnection on connection loss

### Approval Management
- **DashboardPage**: Lists all approvals with filtering
- **ApprovalDetailPage**: Detailed view of single approval
- **ApprovalForm**: Create and edit approvals
- **ApprovalActions**: Approve, reject, rollback actions
- **ApprovalCard**: Card component for approval list

### Custom Hooks
- **useApprovals**: Fetches and manages approval data
- Automatic real-time updates via WebSocket
- Built-in loading and error states

## API Integration

The application integrates with the backend API:

- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/approvals` - Get all approvals
- `GET /api/approvals/:id` - Get single approval
- `POST /api/approvals` - Create approval
- `PUT /api/approvals/:id` - Update approval
- `DELETE /api/approvals/:id` - Delete approval
- `POST /api/approvals/:id/approve` - Approve
- `POST /api/approvals/:id/reject` - Reject
- `POST /api/approvals/:id/rollback` - Rollback
- `GET /api/notifications` - Get notifications

## WebSocket Events

Real-time events via Socket.IO:

- `approval:created` - New approval created
- `approval:updated` - Approval updated
- `approval:approved` - Approval approved
- `approval:rejected` - Approval rejected
- `approval:rolledback` - Approval rolled back
- `notification:new` - New notification received

## Role-Based Access

### Requester
- Create new approvals
- Edit own pending approvals
- Delete own approvals
- View all approvals

### Approver
- All requester permissions
- Approve/reject pending approvals
- Rollback approved approvals

### Admin
- All permissions
- User management (if implemented)

## Configuration

### Environment Variables

- `REACT_APP_API_URL` - Backend API base URL (default: http://localhost:5000/api)
- `REACT_APP_SOCKET_URL` - WebSocket server URL (default: http://localhost:5000)
- `NODE_ENV` - Environment (development/production)

### NGINX Configuration

The `nginx.conf` includes:
- Gzip compression
- Security headers
- Static asset caching
- API proxy to backend
- WebSocket proxy
- Client-side routing support
- Health check endpoint at `/health`

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Performance

- Code splitting with React lazy loading
- Optimized production build with minification
- Gzip compression via NGINX
- Static asset caching (1 year)
- Efficient re-rendering with React hooks

## Security

- JWT token authentication
- HTTPS ready
- Security headers (X-Frame-Options, X-XSS-Protection, etc.)
- Input validation
- XSS protection
- CORS configuration

## Troubleshooting

### WebSocket Connection Issues
- Verify backend server is running
- Check `REACT_APP_SOCKET_URL` is correct
- Ensure CORS is configured on backend
- Check browser console for errors

### API Errors
- Verify `REACT_APP_API_URL` is correct
- Check backend server is running
- Verify JWT token is valid
- Check network tab in browser DevTools

### Build Errors
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Clear cache: `npm cache clean --force`
- Check Node.js version (16+ required)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Create an issue on GitHub
- Contact the development team
- Check the documentation

## Future Enhancements

- [ ] Dark mode support
- [ ] Advanced analytics dashboard
- [ ] Export approvals to PDF/Excel
- [ ] Email notifications
- [ ] Approval templates
- [ ] Bulk operations
- [ ] Advanced search with filters
- [ ] Approval workflow designer
- [ ] Integration with external services (Slack, Teams, etc.)
- [ ] Mobile app (React Native)
