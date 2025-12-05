import os
import django
import random
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Final_Project_Om_opate22.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile
from dishes.models import Cuisine, Dish, Restaurant, RestaurantDish, DishIngredient
from swipes.models import SwipeAction, Favorite, FavoriteRestaurant, Blacklist
from community.models import Review, WeeklyRanking, TrendingDish, CommunityChallenge
from django.utils import timezone


def create_users():
    """Create test users"""
    print("Creating users...")

    # Create superuser if doesn't exist
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@swipebite.com', 'admin123')
        print("✓ Created superuser: admin/admin123")

    # Create test users
    users_data = [
        ('mohitg2', 'graingerlibrary', 'Mohit', 'Granger', 'mohit@test.com'),
        ('infoadmins', 'uiucinfo', 'Info', 'Admin', 'info@test.com'),
        ('foodie1', 'test123', 'Sarah', 'Chen', 'sarah@test.com'),
        ('foodie2', 'test123', 'Mike', 'Johnson', 'mike@test.com'),
        ('foodie3', 'test123', 'Emily', 'Davis', 'emily@test.com'),
    ]

    for username, password, first, last, email in users_data:
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(username, email, password, first_name=first, last_name=last)
            # Update profile
            profile = user.profile
            profile.city = random.choice(['Champaign', 'Urbana', 'Chicago', 'Springfield'])
            profile.diet_type = random.choice(['none', 'vegetarian', 'vegan'])
            profile.save()
            print(f"✓ Created user: {username}")


def create_cuisines():
    """Create cuisine types"""
    print("\nCreating cuisines...")

    cuisines_data = [
        ('Italian', '🍝', 'Pasta, pizza, and classic Italian dishes'),
        ('Mexican', '🌮', 'Tacos, burritos, and authentic Mexican food'),
        ('Chinese', '🥢', 'Traditional Chinese cuisine'),
        ('Japanese', '🍱', 'Sushi, ramen, and Japanese favorites'),
        ('Indian', '🍛', 'Curry, tandoori, and Indian spices'),
        ('American', '🍔', 'Classic American comfort food'),
        ('Thai', '🍜', 'Pad Thai, curries, and Thai specialties'),
        ('French', '🥐', 'Elegant French cuisine'),
        ('Mediterranean', '🥗', 'Healthy Mediterranean dishes'),
        ('Korean', '🍲', 'Korean BBQ and kimchi'),
    ]

    cuisines = []
    for name, emoji, desc in cuisines_data:
        cuisine, created = Cuisine.objects.get_or_create(
            name=name,
            defaults={'emoji': emoji, 'description': desc}
        )
        cuisines.append(cuisine)
        if created:
            print(f"✓ Created cuisine: {name}")

    return cuisines


def create_dishes(cuisines):
    """Create sample dishes"""
    print("\nCreating dishes...")

    dishes_data = [
        # Italian
        ('Margherita Pizza', 'italian', 'Classic pizza with tomato, mozzarella, and basil', 850, 35, 90, 35, 'dinner',
         False, False, True, 0),
        ('Spaghetti Carbonara', 'italian', 'Creamy pasta with bacon and parmesan', 720, 28, 75, 38, 'dinner', False,
         False, False, 0),
        ('Chicken Parmesan', 'italian', 'Breaded chicken with marinara and mozzarella', 650, 42, 45, 28, 'dinner',
         False, False, False, 0),

        # Mexican
        ('Fish Tacos', 'mexican', 'Grilled fish tacos with cabbage slaw', 450, 32, 35, 18, 'lunch', False, False, False,
         1),
        ('Chicken Burrito Bowl', 'mexican', 'Rice bowl with chicken, beans, and veggies', 620, 38, 65, 22, 'lunch',
         False, False, True, 2),
        ('Beef Enchiladas', 'mexican', 'Rolled tortillas with beef and cheese', 580, 35, 48, 26, 'dinner', False, False,
         False, 2),

        # Chinese
        ('Kung Pao Chicken', 'chinese', 'Spicy stir-fried chicken with peanuts', 520, 36, 42, 22, 'dinner', False,
         False, False, 3),
        ('Vegetable Lo Mein', 'chinese', 'Stir-fried noodles with mixed vegetables', 480, 14, 68, 16, 'lunch', True,
         False, False, 1),
        ('General Tso\'s Chicken', 'chinese', 'Sweet and spicy fried chicken', 780, 32, 88, 35, 'dinner', False, False,
         False, 2),

        # Japanese
        ('Salmon Sushi Roll', 'japanese', 'Fresh salmon with rice and seaweed', 350, 18, 42, 12, 'lunch', False, False,
         True, 0),
        ('Chicken Ramen', 'japanese', 'Noodle soup with chicken and vegetables', 450, 28, 52, 14, 'dinner', False,
         False, False, 1),
        ('Teriyaki Bowl', 'japanese', 'Grilled chicken with teriyaki sauce over rice', 520, 32, 68, 10, 'lunch', False,
         False, False, 1),

        # Indian
        ('Chicken Tikka Masala', 'indian', 'Creamy curry with grilled chicken', 580, 36, 42, 28, 'dinner', False, False,
         True, 2),
        ('Vegetable Biryani', 'indian', 'Spiced rice with mixed vegetables', 420, 12, 72, 14, 'lunch', True, True, True,
         2),
        ('Butter Chicken', 'indian', 'Rich and creamy tomato-based curry', 620, 38, 45, 32, 'dinner', False, False,
         True, 1),

        # American
        ('Classic Cheeseburger', 'american', 'Beef patty with cheese, lettuce, tomato', 680, 35, 52, 35, 'lunch', False,
         False, False, 0),
        ('BBQ Ribs', 'american', 'Slow-cooked ribs with BBQ sauce', 820, 45, 38, 48, 'dinner', False, False, True, 0),
        ('Caesar Salad', 'american', 'Romaine lettuce with Caesar dressing', 280, 12, 18, 18, 'lunch', False, False,
         False, 0),

        # Thai
        ('Pad Thai', 'thai', 'Stir-fried rice noodles with shrimp', 520, 22, 65, 18, 'lunch', False, False, False, 2),
        ('Green Curry', 'thai', 'Spicy coconut curry with vegetables', 450, 16, 38, 28, 'dinner', True, True, True, 3),
        ('Tom Yum Soup', 'thai', 'Hot and sour Thai soup with shrimp', 180, 12, 15, 6, 'dinner', False, False, True, 3),
    ]

    cuisine_map = {c.name.lower(): c for c in cuisines}
    dishes = []

    for name, cuisine_name, desc, cal, prot, carbs, fat, meal, veg, vegan, gf, spice in dishes_data:
        if cuisine_name in cuisine_map:
            dish, created = Dish.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'cuisine': cuisine_map[cuisine_name],
                    'calories': cal,
                    'protein': prot,
                    'carbs': carbs,
                    'fat': fat,
                    'meal_type': meal,
                    'is_vegetarian': veg,
                    'is_vegan': vegan,
                    'is_gluten_free': gf,
                    'spice_level': spice,
                    'average_rating': round(random.uniform(3.5, 5.0), 1),
                    'total_ratings': random.randint(10, 100),
                }
            )
            dishes.append(dish)
            if created:
                print(f"✓ Created dish: {name}")

    return dishes


def create_restaurants(cuisines):
    """Create sample restaurants"""
    print("\nCreating restaurants...")

    restaurants_data = [
        ('Bella Italia', 'italian', 'Authentic Italian restaurant', 'Champaign', '$$', 4.5),
        ('Mario\'s Pizza House', 'italian', 'Best pizza in town', 'Urbana', '$', 4.2),
        ('Taco Haven', 'mexican', 'Fresh Mexican food', 'Champaign', '$', 4.3),
        ('El Mariachi', 'mexican', 'Traditional Mexican cuisine', 'Urbana', '$$', 4.6),
        ('Golden Dragon', 'chinese', 'Chinese restaurant', 'Champaign', '$', 4.1),
        ('Sakura Sushi', 'japanese', 'Fresh sushi and Japanese food', 'Champaign', '$$$', 4.7),
        ('Taj Palace', 'indian', 'Authentic Indian cuisine', 'Urbana', '$$', 4.4),
        ('The Burger Joint', 'american', 'Classic American burgers', 'Champaign', '$', 4.0),
        ('Bangkok Express', 'thai', 'Thai street food', 'Urbana', '$', 4.3),
        ('Seoul Kitchen', 'korean', 'Korean BBQ and more', 'Champaign', '$$', 4.5),
    ]

    cuisine_map = {c.name.lower(): c for c in cuisines}
    restaurants = []

    addresses = [
        ('123 Main St', 'IL', '61820'),
        ('456 Green St', 'IL', '61801'),
        ('789 Springfield Ave', 'IL', '61820'),
        ('321 University Ave', 'IL', '61801'),
        ('654 Neil St', 'IL', '61820'),
    ]

    for name, cuisine_name, desc, city, price, rating in restaurants_data:
        addr, state, zip_code = random.choice(addresses)

        restaurant, created = Restaurant.objects.get_or_create(
            name=name,
            defaults={
                'description': desc,
                'cuisine_type': cuisine_map.get(cuisine_name),
                'address': addr,
                'city': city,
                'state': state,
                'zip_code': zip_code,
                'price_range': price,
                'rating': rating,
                'total_reviews': random.randint(50, 200),
                'has_uber_eats': random.choice([True, False]),
                'has_doordash': random.choice([True, False]),
                'has_grubhub': random.choice([True, False]),
            }
        )
        restaurants.append(restaurant)
        if created:
            print(f"✓ Created restaurant: {name}")

    return restaurants


def link_dishes_to_restaurants(dishes, restaurants):
    """Link dishes to restaurants with pricing"""
    print("\nLinking dishes to restaurants...")

    count = 0
    for dish in dishes:
        # Each dish available at 2-4 restaurants
        num_restaurants = random.randint(2, 4)
        selected_restaurants = random.sample(restaurants, min(num_restaurants, len(restaurants)))

        for restaurant in selected_restaurants:
            # Only link if cuisine matches or is compatible
            price = round(random.uniform(8.99, 24.99), 2)

            _, created = RestaurantDish.objects.get_or_create(
                restaurant=restaurant,
                dish=dish,
                defaults={'price': price}
            )
            if created:
                count += 1

    print(f"✓ Created {count} restaurant-dish links")


def create_sample_swipes():
    """Create sample swipe data"""
    print("\nCreating sample swipes...")

    users = User.objects.all()[:5]
    dishes = Dish.objects.all()

    count = 0
    for user in users:
        # Each user swipes on 10-20 dishes
        num_swipes = random.randint(10, 20)
        sample_dishes = random.sample(list(dishes), min(num_swipes, len(dishes)))

        for dish in sample_dishes:
            direction = random.choices(['right', 'left'], weights=[0.6, 0.4])[0]

            _, created = SwipeAction.objects.get_or_create(
                user=user,
                dish=dish,
                defaults={'direction': direction}
            )

            if created:
                # Update dish stats
                dish.total_swipes += 1
                if direction == 'right':
                    dish.total_right_swipes += 1
                    # Add to favorites
                    Favorite.objects.get_or_create(user=user, dish=dish)
                dish.save()
                count += 1

    print(f"✓ Created {count} swipe actions")


def create_sample_reviews():
    """Create sample reviews"""
    print("\nCreating sample reviews...")

    users = User.objects.all()[:5]
    dishes = Dish.objects.all()[:15]

    review_titles = [
        "Absolutely delicious!",
        "Pretty good, would order again",
        "Not bad, but could be better",
        "Amazing flavors!",
        "Best dish I've had in a while",
        "Decent portion size",
        "A bit too spicy for me",
        "Perfect comfort food",
        "Loved it!",
        "Highly recommend",
    ]

    review_contents = [
        "The flavors were incredible and the portion was generous. Definitely ordering this again!",
        "Good quality ingredients and well-prepared. Service was quick too.",
        "It was okay, nothing special but satisfied my hunger.",
        "This exceeded my expectations! The presentation was beautiful and taste was perfect.",
        "One of the best meals I've had. Worth every penny!",
        "Pretty standard but reliable. Good for a quick meal.",
        "Too much spice for my taste, but the quality was good.",
        "Comfort food at its finest. Made me feel right at home.",
        "Can't stop thinking about this dish. Will definitely order again soon!",
        "Great value for money. Tasty and filling.",
    ]

    count = 0
    for user in users:
        # Each user reviews 2-5 dishes
        num_reviews = random.randint(2, 5)
        sample_dishes = random.sample(list(dishes), min(num_reviews, len(dishes)))

        for dish in sample_dishes:
            rating = random.randint(3, 5)

            _, created = Review.objects.get_or_create(
                user=user,
                dish=dish,
                defaults={
                    'rating': rating,
                    'title': random.choice(review_titles),
                    'content': random.choice(review_contents),
                    'helpful_count': random.randint(0, 10),
                }
            )
            if created:
                count += 1

    print(f"✓ Created {count} reviews")


def create_trending_data():
    """Create trending dishes data"""
    print("\nCreating trending data...")

    dishes = Dish.objects.all()[:10]

    count = 0
    for i, dish in enumerate(dishes):
        trending, created = TrendingDish.objects.get_or_create(
            dish=dish,
            defaults={
                'trending_score': random.uniform(50, 200),
                'recent_swipes_24h': random.randint(5, 30),
                'recent_swipes_7d': random.randint(20, 100),
                'recent_reviews_7d': random.randint(2, 15),
                'current_rank': i + 1,
            }
        )
        if created:
            count += 1

    print(f"✓ Created {count} trending dishes")


def create_weekly_rankings():
    """Create weekly rankings"""
    print("\nCreating weekly rankings...")

    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    dishes = Dish.objects.all()[:10]

    count = 0
    for i, dish in enumerate(dishes):
        ranking, created = WeeklyRanking.objects.get_or_create(
            dish=dish,
            week_start=week_start,
            defaults={
                'week_end': week_end,
                'rank': i + 1,
                'total_swipes': random.randint(50, 200),
                'right_swipes': random.randint(30, 150),
                'reviews_count': random.randint(5, 30),
                'average_rating': round(random.uniform(3.8, 5.0), 1),
            }
        )
        if created:
            count += 1

    print(f"✓ Created {count} weekly rankings")


def main():
    """Run all data population functions"""
    print("=" * 50)
    print("POPULATING DATABASE WITH SAMPLE DATA")
    print("=" * 50)

    create_users()
    cuisines = create_cuisines()
    dishes = create_dishes(cuisines)
    restaurants = create_restaurants(cuisines)
    link_dishes_to_restaurants(dishes, restaurants)
    create_sample_swipes()
    create_sample_reviews()
    create_trending_data()
    create_weekly_rankings()

    print("\n" + "=" * 50)
    print("✅ DATABASE POPULATED SUCCESSFULLY!")
    print("=" * 50)
    print("\nTest Credentials:")
    print("Admin: admin / admin123")
    print("User 1: mohitg2 / graingerlibrary")
    print("User 2: infoadmins / uiucinfo")
    print("\nYou can now run: python manage.py runserver")


if __name__ == '__main__':
    main()