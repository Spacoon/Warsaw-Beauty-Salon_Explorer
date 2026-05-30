# Warsaw Beauty Salon Explorer

Warsaw Beauty Salon Explorer is a full-stack web application designed to collect, explore, search, and update information about hair and beauty salons across Warsaw.

The system features:
1. **Data Collection Pipeline**: A BeautifulSoup-based scraper that extracts structured data for **120 salons** from Booksy Warsaw.
2. **Backend REST API**: A FastAPI service that exposes endpoints to retrieve and modify salon records.
3. **Frontend UI**: An interactive Streamlit dashboard allowing users to filter, search, sort, inspect detail profiles and edit details.

---

## 🎯 Features & Product Thinking

This application has been developed with **Product Thinking** at its core to ensure the interface genuinely helps users find the perfect beauty salon:
- **Comprehensive Search & Filters**: Search for names/services and filter salons by district or service type.
- **Dynamic Sorting**: Order salons by rating (highest first), review count (most popular first), or name (alphabetically A-Z) to find top-performing locations.
- **Top Rated Highlights**: Salons with rating $\ge 4.9$ and $\ge 50$ reviews automatically receive a **🏆 (Top Rated)** visual badge to build trust.
- **Google Maps Navigation Link**: Click on any salon address to automatically search for it on Google Maps for seamless navigation.
- **Real-Time Marketplace Stats**: Top metric cards dynamically summarizing the marketplace statistics (Total Salons, Unique Districts covered, and average rating).

---

## 🔧 Technical Solution & Tech Stack

- **Backend Framework**: **FastAPI**.
- **Frontend Framework**: **Streamlit**.
- **Data Scraping**: **BeautifulSoup4** & **Requests**.
- **Data Validation & Quality**: **Pandera**.
- **Data Persistence**: **JSON File Storage (`salons.json`)**.

---

## 🚀 How to Run the Application

Follow these steps to set up and run the project locally.

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Install Dependencies
Install all python packages defined in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 3. Run the Backend REST API
Launch the FastAPI development server:
```bash
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```
- The API will run at `http://localhost:8000`.
- Interactive Swagger documentation is available at `http://localhost:8000/docs`.

### 4. Run the Streamlit Frontend UI
In a separate terminal, start the Streamlit web application:
```bash
streamlit run app.py
```
- The application will automatically open in your default browser at `http://localhost:8501`.

*(Optional)* **Running the Scraper**:
If you want to re-run the scraper pipeline (e.g. to update the records in `salons.json`), run:
```bash
python scraper.py
```
*Note: The scraper is configured to parse 6 pages (120 salons) by default and will validate the data using Pandera before writing it to disk.*

---

## 🔮 What I'd improve with more time
If given more time, the following features and improvements would be introduced:
1. **Relational Database Integration**: Transition from the simple flat JSON file storage to a relational database like SQLite (for local development) or PostgreSQL (for production). This would support proper schemas (separating Salons, Services, and Reviews), transaction safety, and foreign key constraints.
2. **Real-time Map Integration**: Embed an interactive map on the frontend so users can visualize salons geographically, search on the map, and filter salons by radius or current user location.
3. **Service Categorization**: Group the highly granular Booksy services (e.g., merging "Manicure hybrydowy", "Manicure klasyczny", "Manicure męski" under a clean parent category "Manicure") to make dropdown filters more compact, intuitive, and user-friendly.
4. **Image & Gallery Scraping**: Extract and show photos of the salons in the Streamlit UI details card to create a more engaging, visual experience for the user.
5. **Performance & Speed Optimization**: Improve responsiveness and application load times by introducing caching layers (e.g., API response caching), optimizing data rendering/loading states in the Streamlit frontend and pagination.