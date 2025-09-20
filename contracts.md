# Backend Implementation Contracts for Seun M. Olawepo Portfolio

## Overview
Transform the frontend-only portfolio into a full-stack application with dynamic content management, contact form functionality, and admin capabilities.

## API Contracts

### 1. Portfolio Data Management
**Base URL**: `/api/portfolio`

**GET /api/portfolio/hero**
- Returns: Hero section data (name, titles, bio, stats)
- Purpose: Dynamic hero content

**GET /api/portfolio/about**  
- Returns: About section data (bio, key stats)
- Purpose: Dynamic about content

**GET /api/portfolio/projects**
- Query params: `?category=string&tag=string&limit=number`
- Returns: Array of projects with filtering
- Purpose: Dynamic case studies with filtering

**GET /api/portfolio/experience**
- Returns: Complete work experience timeline
- Purpose: Dynamic experience section

**GET /api/portfolio/skills**
- Returns: Skills organized by categories
- Purpose: Dynamic skills display

**GET /api/portfolio/certifications**
- Returns: All certifications and education
- Purpose: Dynamic credentials display

### 2. Contact & Communication
**Base URL**: `/api/contact`

**POST /api/contact/message**
- Body: `{ name, email, subject, message, availability_preference }`
- Returns: Success confirmation with message ID
- Purpose: Contact form submissions

**GET /api/contact/info**
- Returns: Contact information and availability
- Purpose: Dynamic contact details

### 3. Admin Management (Future Enhancement)
**Base URL**: `/api/admin`

**PUT /api/admin/portfolio/:section**
- Body: Section-specific data
- Purpose: Content updates via admin interface

## Database Schema

### Collections

**portfolio_data**
```json
{
  "_id": ObjectId,
  "section": "hero|about|projects|experience|skills|certifications",
  "data": {},
  "last_updated": DateTime,
  "version": Number
}
```

**contact_messages**
```json
{
  "_id": ObjectId,
  "name": String,
  "email": String,
  "subject": String,
  "message": String,
  "availability_preference": String,
  "submitted_at": DateTime,
  "status": "new|read|responded",
  "ip_address": String
}
```

**projects**
```json
{
  "_id": ObjectId,
  "title": String,
  "category": String,
  "problem": String,
  "role": String,
  "approach": [String],
  "outcomes": [String],
  "metrics": {},
  "tags": [String],
  "artifacts": [String],
  "image_url": String,
  "featured": Boolean,
  "display_order": Number,
  "created_at": DateTime
}
```

## Mock Data Migration Strategy

### Current Mock Data Locations:
- `/app/frontend/src/data/mock.js` - All portfolio content

### Migration Steps:
1. Create MongoDB models for each data type
2. Create seed script to populate database from mock data
3. Update frontend to fetch from API endpoints instead of mock
4. Remove mock.js dependency from components

## Integration Points

### Frontend Changes Required:
1. Replace mock data imports with API calls using axios
2. Add loading states for dynamic content
3. Implement contact form with validation
4. Add error handling for API failures
5. Update environment variables for API endpoints

### Backend Implementation:
1. Create FastAPI endpoints matching contracts
2. Implement MongoDB models using Motor (async)
3. Add input validation using Pydantic
4. Implement CORS for frontend communication
5. Add basic rate limiting for contact form
6. Create database seeding functionality

## Success Criteria
- [ ] All portfolio content loads dynamically from database
- [ ] Contact form successfully submits and stores messages  
- [ ] Project filtering works via API
- [ ] No breaking changes to existing UI/UX
- [ ] Fast loading times maintained (<2s initial load)
- [ ] Mobile responsiveness preserved
- [ ] SEO meta data remains intact

## Timeline
1. **Phase 1**: Backend API creation (30 minutes)
2. **Phase 2**: Database integration and seeding (20 minutes)  
3. **Phase 3**: Frontend API integration (25 minutes)
4. **Phase 4**: Testing and refinement (15 minutes)

Total estimated time: 90 minutes