
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Union
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
HERE_API_KEY = os.getenv("HERE_API_KEY")
client = OpenAI(api_key=API_KEY)

class Place(BaseModel):
    name: str
    address: str
    location: List[float]
    distance: str

class NearbyPlacesResponse(BaseModel):
    nearby_places: Dict[str, Union[List[Place], Dict[str, List]]]

def generate_summary(places: Dict[str, List[Dict]]) -> str:
    summary_prompt = """You are an expert reviewer. 
    Based on the following nearby places, provide a concise and professional summary of the advantages of this unit's location.
    The review should be easy for users to understand, not exceed three lines or 30 words, and evaluate each category with score starting from 0 to 10. make the score based on the nearest location as well as the number of nearest locations for each category
    Generate the review in Arabic, please. 
    Review Format Example:

    1. **البنوك:**  أقرب بنك 0.58 كيلومتر. **(10/10)**
    2. **المطاعم:** العديد منها على بعد 0.14 كيلومتر. **(10/10)**
    3. **المدارس:**  أقرب مدرسة على بعد 0.41 كيلومتر. **(9/10)**
    4. **الصيدليات:** قريب جداً، أقرب صيدلية على بعد 0.59 كيلومتر. **(10/10)**
    5. **الحدائق:**  عدة حدائق على بعد أقل من 1 كيلومتر. **(8/10)**
    6. **الفنادق:**  بعضها على بعد 0.11 كيلومتر. **(9/10)**
    7. **المقاهي:** تنوع رائع، العديد منها على بعد 0.34 كيلومتر. **(10/10)**
    8. **المولات:** عدة خيارات على بعد 0.38 كيلومتر. **(8/10)**
    9. **هايبرماركت:**  لم يتم العثور على هايبرماركت قريب **(0/10)**
    10. **مستشفيات:**  لم يتم العثور على مستشفيات قريبه **(0/10)**

    """
    
    for category, place_list in places.items():
        summary_prompt += f"\n{category}:\n"
        if place_list:
            for place in place_list:
                if float(place['distance']) < 1500:
                    summary_prompt += f"- Name: {place['name']}, Address: {place['address']}, Distance: {float(place['distance']) / 1000:.2f} kilometers\n"
        else:
            summary_prompt += "No places found.\n"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a brilliant reviewer capable of understanding the provided nearby places and generating an insightful review."},
            {"role": "user", "content": summary_prompt}
        ]
    )
    
    review = response.choices[0].message.content
    
    return review

def geocode_address(address: str):
    geolocator = Nominatim(user_agent="geoapiExercises")
    location = geolocator.geocode(address)
    if location:
        return location.latitude, location.longitude
    else:
        return None, None

def get_here_places(latitude: float, longitude: float) -> Dict[str, List[Dict]]:
    places_url = "https://discover.search.hereapi.com/v1/discover"
    place_categories = {
        "Hypermarkets": "hypermarket",
        "Banks": "bank",
        "Restaurants": "restaurant",
        "Schools": "school",
        "Hospitals": "hospital",
        "Pharmacies": "pharmacy",
        "Parks": "park",
        "Hotels": "hotel",
        "Cafes": "cafe",
        "Shopping Malls": "shopping-mall"
    }
    places = {category: [] for category in place_categories.keys()}

    for category, query in place_categories.items():
        places_params = {
            "at": f"{latitude},{longitude}",
            "limit": 10,
            "q": query,
            "apiKey": HERE_API_KEY
        }
        response = requests.get(places_url, params=places_params)
        data = response.json()

        for item in data['items']:
            place = {
                'name': item['title'],
                'address': item['address']['label'],
                'location': [item['position']['lat'], item['position']['lng']],
                'distance': f"{geodesic((latitude, longitude), (item['position']['lat'], item['position']['lng'])).meters / 1000:.2f}"
            }
            if float(place['distance']) < 1.5:  # only include places within 1.5 km
                places[category].append(place)

    return places