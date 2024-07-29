from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Union
import requests
import os
from .utilities import *

app = FastAPI()


@app.get("/nearby-places", response_model=NearbyPlacesResponse)
def find_nearby_places(latitude: float, longitude: float):
    try:
        places = get_here_places(latitude, longitude)
        summary = generate_summary(places)
        # print(summary)
        
        for category, place_list in places.items():
            if not place_list:
                places[category] = {"search_result": []}
        print({"nearby_places": places, "review": summary})
        places['review'] = {"summary":[summary]}
        return {"nearby_places": places, "review": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
