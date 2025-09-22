# Seun M. Olawepo - Professional Portfolio

> Senior Agile & Cloud Application Leader/AI Generalist | 15+ Years Experience | 200+ Teams Mentored

## 🌐 Live Portfolio
**Website**: [https://portfolio-fullstack.preview.emergentagent.com](https://portfolio-fullstack.preview.emergentagent.com)  
**Admin Dashboard**: [https://portfolio-fullstack.preview.emergentagent.com/admin](https://portfolio-fullstack.preview.emergentagent.com/admin)

## 📋 About
Professional portfolio showcasing extensive experience in Agile transformation, cloud application development, and AI/ML integration across Fortune 500 companies. This full-stack application demonstrates technical leadership capabilities while serving as a comprehensive showcase of career achievements.

### Key Highlights
- **Leadership Scale**: 200+ teams mentored and led across enterprise transformations
- **Budget Management**: $5M+ in project budgets managed
- **Delivery Improvement**: 35+ improvement in delivery performance
- **AI/ML Integration**: Pioneering intelligent automation and data-driven decision making

## 🏗️ Technical Architecture

### Frontend
- **Framework**: React 19 with modern hooks and functional components
- **Styling**: Tailwind CSS with custom design system
- **UI Components**: Shadcn/ui component library
- **State Management**: React hooks and context API
- **Routing**: React Router for SPA navigation

### Backend
- **Framework**: FastAPI (Python) with async/await patterns
- **Database**: MongoDB with Motor (async driver)
- **Authentication**: JWT-based authentication ready
- **API Design**: RESTful APIs with OpenAPI documentation
- **Email Service**: Integrated notification system

### DevOps & Deployment
- **Containerization**: Docker with multi-stage builds
- **Process Management**: Supervisor for service orchestration
- **Environment Management**: Environment-specific configurations
- **Database**: MongoDB with automated seeding

## 🎯 Key Features

### Portfolio Management
- **Dynamic Content**: All content served from MongoDB APIs
- **Case Studies**: 6 detailed enterprise transformation case studies
- **Experience Timeline**: Complete professional history with achievements
- **Skills Matrix**: Organized by categories with AI/ML prominence
- **Certifications**: Professional credentials and education

### Contact & Communication
- **Contact Form**: Professional inquiry system with validation
- **Email Notifications**: Automated email alerts for new submissions
- **Admin Dashboard**: Complete message management interface
- **Status Tracking**: Message workflow management (new/read/responded)

### Professional Features
- **ATS Optimization**: Resume-friendly content structure
- **Mobile Responsive**: Perfect display across all devices
- **Performance Optimized**: Fast loading with efficient API calls
- **SEO Ready**: Proper meta tags and structured data

## 📁 Project Structure
```
/
├── frontend/                 # React application
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── services/        # API integration services
│   │   ├── data/           # Mock data and constants
│   │   └── hooks/          # Custom React hooks
│   ├── public/             # Static assets
│   └── package.json        # Dependencies and scripts
├── backend/                # FastAPI application
│   ├── models.py          # Database models and schemas
│   ├── database.py        # Database connection and operations
│   ├── portfolio_api.py   # Portfolio data endpoints
│   ├── contact_api.py     # Contact form endpoints
│   ├── admin_api.py       # Admin dashboard endpoints
│   ├── email_service.py   # Email notification service
│   └── server.py          # Main application server
└── docs/                  # Documentation and guides
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and Yarn
- Python 3.9+ and pip
- MongoDB instance
- Docker (optional)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/[your-username]/seun-olawepo-portfolio.git
   cd seun-olawepo-portfolio
   ```

2. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   
   # Set environment variables
   export MONGO_URL="mongodb://localhost:27017"
   export DB_NAME="portfolio_db"
   
   # Start the server
   uvicorn server:app --host 0.0.0.0 --port 8001 --reload
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   yarn install
   
   # Set environment variables
   echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env
   
   # Start the development server
   yarn start
   ```

4. **Seed the Database**
   ```bash
   curl -X POST http://localhost:8001/api/seed
   ```

### Production Deployment

The application is production-ready and can be deployed to:
- **Frontend**: Vercel, Netlify, or AWS S3 + CloudFront
- **Backend**: Railway, Heroku, or AWS EC2/ECS
- **Database**: MongoDB Atlas or AWS DocumentDB

## 🛠️ API Documentation

### Portfolio Endpoints
- `GET /api/portfolio/hero` - Hero section data
- `GET /api/portfolio/about` - About section data
- `GET /api/portfolio/projects` - Case studies with filtering
- `GET /api/portfolio/experience` - Work experience timeline
- `GET /api/portfolio/skills` - Skills and expertise
- `GET /api/portfolio/certifications` - Credentials and education

### Contact Endpoints
- `POST /api/contact/message` - Submit contact form
- `GET /api/contact/messages` - Retrieve messages (admin)
- `GET /api/contact/info` - Contact information

### Admin Endpoints
- `GET /api/admin/messages` - Message management with pagination
- `PUT /api/admin/messages/{id}/status` - Update message status
- `DELETE /api/admin/messages/{id}` - Delete message
- `GET /api/admin/dashboard/stats` - Dashboard statistics

## 📊 Case Studies Showcase

1. **Enterprise PI Planning Excellence Framework** - 200+ participants, 95% success rate
2. **AI-Enhanced WSJF Prioritization System** - 40% backlog reduction, 92% sprint success
3. **Intelligent Cross-Team Dependency Management** - 100% visibility, 30% blocker reduction
4. **AI-Driven CI/CD Excellence Platform** - 95% build success, 2x deployment frequency
5. **Executive Stakeholder Communication System** - 50% escalation reduction, <1 day decisions
6. **AI-Enhanced Scrum Ceremonies Framework** - 80% participation increase, 45% engagement improvement

## 🎖️ Certifications & Education

### Professional Certifications
- Project Management Professional (PMP) - PMI, 2022
- Professional Scrum Master (PSM I) - Scrum.org, 2019
- Certified ScrumMaster (CSM) - Scrum Alliance, 2019
- SAFe Release Train Engineer (RTE) - Scaled Agile, 2019
- AWS Cloud Practitioner - Amazon Web Services, 2025

### Education
- **M.Sc. Information Technology Project Management** - Northcentral University, 2022
- **B.Sc. Civil Engineering Technology** - University of Ilorin, 2007

## 🤝 Professional Experience

### Current Role
**TSPi - Sr. SAFe Scrum Master/Team Lead** (September 2023 – Present)
- Supporting USDA/NRCS projects with 40% automation improvement
- Leading BPMN process redesign with AI/ML integration
- Mentoring cross-functional teams in Agile best practices

### Previous Roles
- **Fidelity Investments** - Sr. Agile Delivery Manager & Business Rules Analyst Lead
- **Fidelity Investments** - Sr. SAFe Scrum Master/RTE  
- **UnitedHealth Group** - Sr. Agile Lead & Business Analyst Lead
- **UnitedHealth Group** - Senior Scrum Master (ART Leadership) / Product Owner
- **Mastercard** - IT Agile Scrum Master & Business Rules Analyst Lead

## 📞 Contact Information

**Email**: seunolawepo2010@gmail.com  
**LinkedIn**: [linkedin.com/in/seun-m-o](https://www.linkedin.com/in/seun-m-o/)  
**Availability**: 8am to 5pm CST  
**Focus**: Available for Cloud Applications Manager roles and enterprise Agile transformation consulting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with modern web technologies and best practices, showcasing technical leadership capabilities while maintaining focus on business outcomes and team empowerment.

---
*"Transforming organizations through Agile leadership and strategic delivery excellence"*