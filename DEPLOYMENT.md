# Deployment Guide for Employee Management System Backend

## Deploying to Render

### Prerequisites
- A Render account
- Your code pushed to a Git repository (GitHub, GitLab, etc.)

### Method 1: Using render.yaml (Recommended)

1. **Push your code to Git repository**
   ```bash
   git add .
   git commit -m "Fix Dockerfile for Render deployment"
   git push origin main
   ```

2. **Connect to Render**
   - Go to [render.com](https://render.com)
   - Sign up/Login
   - Click "New +" and select "Blueprint"
   - Connect your Git repository
   - Render will automatically detect the `render.yaml` file

3. **Deploy**
   - Render will automatically create both the web service and database
   - The deployment will use the configuration in `render.yaml`

### Method 2: Manual Deployment

1. **Create Database**
   - Go to Render Dashboard
   - Click "New +" → "PostgreSQL"
   - Choose "Free" plan
   - Note down the connection string

2. **Create Web Service**
   - Click "New +" → "Web Service"
   - Connect your Git repository
   - Configure:
     - **Name**: `employee-management-backend`
     - **Environment**: `Python`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
     - **Plan**: Free

3. **Set Environment Variables**
   ```
   FLASK_ENV=production
   CREATE_APP_ON_IMPORT=1
   SEED_DEMO_USERS=true
   SECRET_KEY=<generate-a-secure-secret>
   DATABASE_URL=<your-postgresql-connection-string>
   UPLOADS_DIR=uploads/employees
   ```

### Environment Variables Explained

- `FLASK_ENV=production`: Sets Flask to production mode
- `CREATE_APP_ON_IMPORT=1`: Ensures the Flask app is created when imported
- `SEED_DEMO_USERS=true`: Creates demo users for testing
- `SECRET_KEY`: Used for JWT tokens and session management
- `DATABASE_URL`: PostgreSQL connection string (auto-provided by Render)
- `UPLOADS_DIR`: Directory for file uploads

### Demo Users Created

When `SEED_DEMO_USERS=true`:
- **Admin**: `admin@company.com` / `admin123`
- **Employee**: `employee@company.com` / `emp123`

### API Endpoints

Your API will be available at:
- Base URL: `https://your-app-name.onrender.com`
- Health Check: `https://your-app-name.onrender.com/health`
- API Docs: `https://your-app-name.onrender.com/`

### Troubleshooting

1. **Build Fails**: Check the build logs in Render dashboard
2. **Database Connection**: Ensure `DATABASE_URL` is set correctly
3. **Port Issues**: Render automatically sets the `PORT` environment variable
4. **File Uploads**: Files are stored in the container's ephemeral storage

### Frontend Configuration

Update your frontend's API base URL to point to your Render backend:
```javascript
const API_BASE_URL = 'https://your-app-name.onrender.com/api';
```

### Important Notes

- The free tier has limitations on build time and runtime
- Files uploaded to the app will be lost on container restart (use external storage for production)
- The database is persistent and will survive container restarts
- Monitor your usage to stay within free tier limits

### Production Considerations

For production deployment:
1. Use a paid plan for better performance
2. Set up external file storage (AWS S3, etc.)
3. Configure proper logging
4. Set up monitoring and alerts
5. Use environment-specific configurations


