# 🚀 Deployment Instructions for Seun M. Olawepo Portfolio

## Quick Deploy Guide

### **Option 1: One-Click Deploy (Recommended)**

#### **1. Database Setup (MongoDB Atlas)**
1. Go to [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Create free account and new cluster
3. Create database user: `portfolioadmin` with strong password
4. Add network access: `0.0.0.0/0` (allow from anywhere)
5. Get connection string: `mongodb+srv://portfolioadmin:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/portfolio_db`

#### **2. Backend Deploy (Railway)**
1. Go to [Railway.app](https://railway.app) and connect GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your `seun-olawepo-portfolio` repository
4. Configure service:
   - **Root Directory**: `/backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   ```
   MONGO_URL=mongodb+srv://portfolioadmin:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/portfolio_db
   DB_NAME=portfolio_db
   ```
6. Deploy and note your Railway URL: `https://your-app-name.railway.app`

#### **3. Frontend Deploy (Vercel)**
1. Go to [Vercel.com](https://vercel.com) and connect GitHub
2. Click "New Project" → Import your repository
3. Configure build:
   - **Framework Preset**: Create React App
   - **Root Directory**: `/frontend`
   - **Build Command**: `yarn build`
   - **Output Directory**: `build`
4. Add environment variable:
   ```
   REACT_APP_BACKEND_URL=https://your-app-name.railway.app
   ```
5. Deploy and get your Vercel URL

#### **4. Seed Database**
After both deployments are live:
```bash
curl -X POST https://your-app-name.railway.app/api/seed
```

---

## **Custom Domain Setup (Optional)**

### **Purchase Domain**
Recommended: `seunolawepo.com` or `seunolawepo.dev`

### **DNS Configuration**
1. **Main Site**: Point to Vercel
   - Add CNAME: `www` → `cname.vercel-dns.com`
   - Add A record: `@` → Vercel IP

2. **API Subdomain**: Point to Railway
   - Add CNAME: `api` → `your-app.railway.app`

### **SSL Certificates**
Both Vercel and Railway provide automatic SSL certificates.

---

## **Environment Variables Summary**

### **Backend (Railway)**
```env
MONGO_URL=mongodb+srv://portfolioadmin:PASSWORD@cluster0.xxxxx.mongodb.net/portfolio_db
DB_NAME=portfolio_db
SENDER_EMAIL=your-email@gmail.com (optional)
SENDER_PASSWORD=your-app-password (optional)
```

### **Frontend (Vercel)**
```env
REACT_APP_BACKEND_URL=https://your-railway-app.railway.app
```

---

## **Testing Checklist**

After deployment:

✅ **Frontend Tests**
- [ ] Portfolio loads at your domain
- [ ] All sections display correctly
- [ ] Case studies are clickable
- [ ] Contact form opens and submits
- [ ] Mobile responsiveness works

✅ **Backend Tests**
- [ ] API health check: `GET /api/`
- [ ] Portfolio data: `GET /api/portfolio/hero`
- [ ] Contact form: `POST /api/contact/message`
- [ ] Admin dashboard: `GET /api/admin/messages`

✅ **Database Tests**
- [ ] Data is seeded correctly
- [ ] Contact form submissions save
- [ ] Admin dashboard shows messages

---

## **Post-Deployment**

### **1. Update LinkedIn**
Add your live portfolio URL to your LinkedIn profile

### **2. SEO Setup**
Your portfolio includes proper meta tags and SEO optimization

### **3. Analytics (Optional)**
Add Google Analytics to track visitors:
1. Create Google Analytics account
2. Add tracking code to `public/index.html`

### **4. Email Setup (Optional)**
For email notifications to work:
1. Use Gmail app password or SendGrid
2. Add `SENDER_EMAIL` and `SENDER_PASSWORD` to Railway

---

## **Troubleshooting**

### **Common Issues**
1. **Build Fails**: Check Node.js version (use 18+)
2. **API Not Found**: Verify `REACT_APP_BACKEND_URL` env var
3. **Database Connection**: Check MongoDB Atlas network access
4. **CORS Errors**: Ensure backend allows frontend domain

### **Support Commands**
```bash
# Test backend locally
cd backend && uvicorn server:app --reload

# Test frontend locally  
cd frontend && yarn start

# Check environment variables
echo $REACT_APP_BACKEND_URL
```

---

## **Cost Breakdown**

### **Free Tier (Recommended for MVP)**
- **MongoDB Atlas**: Free (512MB storage)
- **Railway**: Free ($5/month after trial)
- **Vercel**: Free (unlimited static sites)
- **Total**: ~$5/month after free trials

### **Professional Tier**
- **MongoDB Atlas**: $9/month (10GB storage)
- **Railway**: $10/month (more resources)
- **Vercel Pro**: $20/month (custom domains, analytics)
- **Custom Domain**: $10-15/year
- **Total**: ~$40/month + domain

---

Your portfolio is production-ready and will showcase your expertise professionally!