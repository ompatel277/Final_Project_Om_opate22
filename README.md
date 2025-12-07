# 🍔 Swipe&Bite - Food Discovery Platform

Swipe&Bite is a full-stack Django web application that lets users discover food by swiping—similar to Tinder's interface. Users can swipe on dishes, find nearby restaurants, save favorites, write reviews, and get personalized recommendations.

## 🚀 Live Demo

**Deployed URL:** [Add your PythonAnywhere URL here after deployment]

## 👥 Test Accounts

### Internal Tester Account
- **Username:** `mohitg2`
- **Password:** `graingerlibrary`
- **Role:** Staff access with testing privileges

### Internal Guest Account
- **Username:** `infoadmins`
- **Password:** `uiucinfo`
- **Role:** Regular user access

## 📋 Features Implemented

### **Table 1: Foundational Features (15 pts)**

1. ✅ **GitHub Repository & Environment Setup** (3 pts)
   - Complete Django project with virtual environment
   - Organized app structure (8 Django apps)
   - Proper .gitignore and version control

2. ✅ **UI/UX Planning** (2 pts)
   - Wireframes available in `/Docs/wireframe/`
   - User flow diagrams
   - Tinder-inspired swipe interface design

3. ✅ **Models + ORM Basics** (3 pts)
   - 15+ models with complex relationships
   - Models: UserProfile, Dish, Restaurant, RestaurantDish, SwipeAction, Favorite, Review, WeeklyRanking, TrendingDish, CommunityChallenge, UserBadge
   - All models registered in admin with custom configurations
   - Database populated with 50+ dishes, 30+ restaurants

4. ✅ **Views + Templates + URLs** (3 pts)
   - 30+ function-based and class-based views
   - 31 HTML templates with inheritance
   - Proper URL namespacing across 8 apps
   - Context data passing and template tags

5. ✅ **User Authentication for Internal Users** (2 pts)
   - Django built-in authentication
   - Login/logout/register functionality
   - Staff accounts: mohitg2, infoadmins
   - Protected routes with @login_required
   - Session management

6. ✅ **Deployment** (2 pts)
   - Production-ready settings
   - Static files configured with WhiteNoise
   - Environment variables with python-dotenv
   - Ready for PythonAnywhere deployment

### **Table 2: Functional Add-ons (15 pts)**

1. ✅ **ORM Queries + Data Summaries** (3 pts)
   - Advanced QuerySet filtering, aggregations, annotations
   - select_related() and prefetch_related() for optimization
   - Complex queries for rankings and recommendations
   - Example: `User.objects.annotate(review_count=Count('reviews'))`

2. ✅ **Static Files (CSS/JS Integration)** (3 pts)
   - Bootstrap 5 for responsive design
   - Custom CSS (`swipe&bite.css`)
   - Font Awesome icons
   - Google Fonts (Poppins)
   - Properly configured STATIC_ROOT and collectstatic

3. ✅ **Charts / Visualization** (3 pts)
   - Rating distributions for reviews
   - Trending score calculations with visual ranking
   - Match rate percentages for swipes
   - Dashboard statistics display

4. ✅ **Forms + Basic Input / CRUD** (3 pts)
   - UserRegistrationForm with validation
   - Profile editing forms (UserUpdateForm, UserProfileForm)
   - Review submission forms
   - Complete CRUD for dishes, reviews, favorites
   - Form validation and error handling

5. ✅ **User Authentication for External Users** (3 pts)
   - Public signup with UserCreationForm
   - Email validation
   - Auto-login after registration
   - Profile setup wizard for new users
   - Separate staff and public user roles

### **Bonus Features (+10 pts estimated)**

- ✅ **Community Ranking System** - Weekly top 10 dishes aggregation
- ✅ **AI-Powered Recommendations** - Mock AI assistant with rule-based responses
- ✅ **Advanced Search** - Multiple filters (cuisine, diet, calories, price)
- ✅ **Swipe-Based Discovery** - Unique Tinder-style interface for food
- ✅ **Favorites & Blacklist** - User preference management
- ✅ **Review System** - 5-star ratings with helpful voting
- ✅ **Badge/Achievement System** - User gamification
- ✅ **Trending Dishes Algorithm** - Time-decay scoring system
- ✅ **Leaderboards** - Top reviewers, swipers, badge earners
- ✅ **Multiple Delivery Options** - Uber Eats, DoorDash, Grubhub integration ready

## 🛠️ Tech Stack

- **Backend:** Django 5.2.7
- **Frontend:** Bootstrap 5, HTML5, CSS3, JavaScript
- **Database:** SQLite3 (Development) / PostgreSQL-ready (Production)
- **Authentication:** Django Auth + JWT (REST API ready)
- **APIs Ready:** Google Maps, Uber Eats, DoorDash, OpenAI
- **Deployment:** WhiteNoise for static files, ready for PythonAnywhere
- **Additional:** django-filter, django-cors-headers, djangorestframework

## 📦 Installation & Setup

### Prerequisites
- Python 3.10+
- pip package manager
- Virtual environment (venv)

### Local Setup

1. **Clone the repository**
```bash
git clone https://github.com/ompatel277/Final_Project_Om_opate22.git
cd Final_Project_Om_opate22
