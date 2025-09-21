# Deployment Guide - Seun M. Olawepo Portfolio

This guide covers different deployment options for your professional portfolio.

## 🌐 Production Deployment Options

### Option 1: Vercel + Railway (Recommended)

**Frontend: Vercel**
1. Connect your GitHub repository to Vercel
2. Framework preset: `React`
3. Build command: `cd frontend && yarn build`
4. Output directory: `frontend/build`
5. Environment variables:
   ```
   REACT_APP_BACKEND_URL=https://your-railway-app.railway.app
   ```

**Backend: Railway**
1. Connect your GitHub repository to Railway
2. Configure build settings:
   ```
   Build Command: cd backend && pip install -r requirements.txt
   Start Command: cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT
   ```
3. Environment variables:
   ```
   MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/portfolio_db
   DB_NAME=portfolio_db
   ```

**Database: MongoDB Atlas**
1. Create a free cluster at mongodb.com
2. Set up database user and network access
3. Get connection string for Railway backend

### Option 2: Netlify + Heroku

**Frontend: Netlify**
1. Connect GitHub repository
2. Build settings:
   ```
   Base directory: frontend
   Build command: yarn build
   Publish directory: frontend/build
   ```
3. Environment variables:
   ```
   REACT_APP_BACKEND_URL=https://your-heroku-app.herokuapp.com
   ```

**Backend: Heroku**
1. Create new Heroku app
2. Connect to GitHub repository
3. Add Procfile in backend directory:
   ```
   web: uvicorn server:app --host 0.0.0.0 --port $PORT
   ```
4. Set environment variables in Heroku dashboard

### Option 3: AWS (Enterprise-level)

**Frontend: S3 + CloudFront**
- Host static React build in S3 bucket
- Use CloudFront for CDN and custom domain
- Configure proper routing for SPA

**Backend: ECS or EC2**
- Containerize backend with Docker
- Deploy to ECS with Fargate
- Use Application Load Balancer

**Database: AWS DocumentDB**
- Managed MongoDB-compatible service
- Automatic backups and scaling

## 🔧 Environment Configuration

### Frontend Environment Variables
```bash
# .env (frontend)
REACT_APP_BACKEND_URL=https://your-backend-url.com
```

### Backend Environment Variables
```bash
# .env (backend)
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/portfolio_db
DB_NAME=portfolio_db
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
```

## 🚀 Quick Deploy Commands

### Deploy to Vercel (Frontend)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy from frontend directory
cd frontend
vercel --prod
```

### Deploy to Railway (Backend)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

## 🔒 Security Considerations

### Environment Variables
- Never commit .env files to GitHub
- Use secure random strings for JWT secrets
- Rotate database passwords regularly

### API Security
- Implement rate limiting for contact form
- Add CORS configuration for production
- Use HTTPS in production

### Database Security
- Enable MongoDB authentication
- Use strong passwords
- Restrict network access to specific IPs

## 📊 Monitoring & Analytics

### Application Monitoring
- Set up error tracking (Sentry)
- Monitor API response times
- Track database performance

### Analytics
- Google Analytics for portfolio visits
- Admin dashboard for contact form metrics
- Performance monitoring with Lighthouse

## 🔄 CI/CD Pipeline

### GitHub Actions Example
```yaml
name: Deploy Portfolio

on:
  push:
    branches: [ main ]

jobs:
  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
          working-directory: ./frontend

  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Railway
        uses: railway-cli-action@v1
        with:
          railway-token: ${{ secrets.RAILWAY_TOKEN }}
          working-directory: ./backend
```

## 📝 Domain Configuration

### Custom Domain Setup
1. Purchase domain (recommended: seunolawepo.com)
2. Configure DNS:
   - Frontend: Point to Vercel/Netlify
   - Backend: Point to Railway/Heroku
3. Set up SSL certificates (automatic with most platforms)
4. Update CORS and environment variables

### Subdomain Structure
- Main site: `seunolawepo.com`
- API: `api.seunolawepo.com`
- Admin: `seunolawepo.com/admin`

## 🆘 Troubleshooting

### Common Issues
1. **CORS Errors**: Check backend CORS configuration
2. **API Not Found**: Verify backend URL in frontend env
3. **Database Connection**: Check MongoDB Atlas network access
4. **Build Failures**: Verify Node.js/Python versions

### Debug Commands
```bash
# Check frontend build
cd frontend && yarn build

# Test backend locally
cd backend && uvicorn server:app --reload

# Test database connection
curl https://your-backend-url/api/portfolio/hero
```

## 📞 Support

For deployment assistance or issues:
- Email: seunolawepo2010@gmail.com
- LinkedIn: linkedin.com/in/seun-m-o
- Create GitHub issue in repository

---
*This deployment guide ensures your portfolio is production-ready and professionally hosted.*