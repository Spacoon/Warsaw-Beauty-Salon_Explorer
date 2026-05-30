import json
import os
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

SALONS_FILE = "salons.json"

app = FastAPI(
    title="Warsaw Beauty Salons REST API",
    description="A simple REST API to browse, search, and update beauty salons in Warsaw.",
    version="1.0.0"
)

# Enable CORS for frontend cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_data() -> pd.DataFrame:
    """Loads the salon data from salons.json into a Pandas DataFrame, ensuring standard columns exist."""
    if not os.path.exists(SALONS_FILE):
        return pd.DataFrame(columns=[
            "Name of the business", "Address", "District",
            "Website / social media link", "Services offered",
            "Price range", "Rating + number of reviews", "Phone number"
        ])

    # Read the JSON using Pandas
    df = pd.read_json(SALONS_FILE)

    # Ensure all required and optional columns are present
    if "Phone number" not in df.columns:
        df["Phone number"] = ""
    if "Price range" not in df.columns:
        df["Price range"] = ""
    if "Rating + number of reviews" not in df.columns:
        df["Rating + number of reviews"] = ""

    # Fill NaN values to prevent JSON serialization errors
    df["Phone number"] = df["Phone number"].fillna("")
    df["Price range"] = df["Price range"].fillna("")
    df["Rating + number of reviews"] = df["Rating + number of reviews"].fillna("None")

    # Ensure array columns contain lists
    if "Website / social media link" in df.columns:
        df["Website / social media link"] = df["Website / social media link"].apply(
            lambda x: x if isinstance(x, list) else [])
    else:
        df["Website / social media link"] = [[] for _ in range(len(df))]

    if "Services offered" in df.columns:
        df["Services offered"] = df["Services offered"].apply(lambda x: x if isinstance(x, list) else [])
    else:
        df["Services offered"] = [[] for _ in range(len(df))]

    return df


def save_data(df: pd.DataFrame):
    """Saves the Pandas DataFrame back to salons.json in a clean, indented JSON format."""
    # Convert dataframe back to list of dicts
    data = df.to_dict(orient="records")
    # Atomically write to prevent corruption
    temp_file = SALONS_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    # Rename to target file
    if os.path.exists(SALONS_FILE):
        os.remove(SALONS_FILE)
    os.rename(temp_file, SALONS_FILE)


# Pydantic schema for editing salon details
class SalonUpdate(BaseModel):
    name: str
    address: str
    district: str
    phone: Optional[str] = ""
    websites: List[str] = []
    services: List[str] = []
    price_range: Optional[str] = ""
    rating: Optional[str] = ""


@app.get("/")
def read_root():
    return {"message": "Welcome to Warsaw Beauty Salons API. Head over to /docs for interactive Swagger documentation."}


@app.get("/api/salons")
def get_salons(district: Optional[str] = None, service: Optional[str] = None, search: Optional[str] = None):
    """Returns a list of salons, optionally filtered by district, service, and text search."""
    df = load_data()
    salons = []
    for idx, row in df.iterrows():
        # Filter by district
        if district and row["District"] != district:
            continue

        # Filter by service
        if service:
            services_offered = row["Services offered"]
            if not isinstance(services_offered, list) or service not in services_offered:
                continue

        # Filter by keyword search (matches business name or services)
        if search:
            q = search.lower()
            name_match = q in str(row["Name of the business"]).lower()

            services_offered = row["Services offered"]
            services_match = False
            if isinstance(services_offered, list):
                services_match = any(q in str(s).lower() for s in services_offered)

            if not (name_match or services_match):
                continue

        salons.append({
            "id": int(idx),
            "name": row["Name of the business"],
            "district": row["District"],
            "rating": row["Rating + number of reviews"],
            "price_range": row["Price range"]
        })
    return salons


@app.get("/api/salons/{salon_id}")
def get_salon(salon_id: int):
    """Returns the full details of a single salon by its index (id)."""
    df = load_data()
    if salon_id < 0 or salon_id >= len(df):
        raise HTTPException(status_code=404, detail=f"Salon with ID {salon_id} not found.")

    row = df.iloc[salon_id]
    return {
        "id": salon_id,
        "name": row["Name of the business"],
        "address": row["Address"],
        "district": row["District"],
        "phone": row["Phone number"],
        "websites": row["Website / social media link"],
        "services": row["Services offered"],
        "price_range": row["Price range"],
        "rating": row["Rating + number of reviews"]
    }


@app.put("/api/salons/{salon_id}")
def update_salon(salon_id: int, updated_salon: SalonUpdate):
    """Modifies a single salon's details and persists them to disk."""
    df = load_data()
    if salon_id < 0 or salon_id >= len(df):
        raise HTTPException(status_code=404, detail=f"Salon with ID {salon_id} not found.")

    # Update row values
    df.at[salon_id, "Name of the business"] = updated_salon.name
    df.at[salon_id, "Address"] = updated_salon.address
    df.at[salon_id, "District"] = updated_salon.district
    df.at[salon_id, "Phone number"] = updated_salon.phone
    df.at[salon_id, "Website / social media link"] = updated_salon.websites
    df.at[salon_id, "Services offered"] = updated_salon.services
    df.at[salon_id, "Price range"] = updated_salon.price_range
    df.at[salon_id, "Rating + number of reviews"] = updated_salon.rating

    save_data(df)
    return {"message": "Salon details updated successfully", "id": salon_id}


@app.get("/api/districts")
def get_districts():
    """Returns a sorted list of unique districts for UI filtering."""
    df = load_data()
    districts = df["District"].dropna().unique().tolist()
    # Clean up whitespace and empty strings
    cleaned_districts = sorted(list(set([d.strip() for d in districts if isinstance(d, str) and d.strip()])))
    return cleaned_districts


@app.get("/api/services")
def get_services():
    """Returns a sorted list of unique services for autocomplete/filtering."""
    df = load_data()
    all_services = []
    for services_list in df["Services offered"].dropna():
        if isinstance(services_list, list):
            all_services.extend(services_list)
    cleaned_services = sorted(list(set([s.strip() for s in all_services if isinstance(s, str) and s.strip()])))
    return cleaned_services
