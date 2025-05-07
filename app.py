from flask import Flask, render_template, request
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
from geopy.distance import geodesic
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64
from wordcloud import WordCloud
import plotly.express as px
import plotly.io as pio

app = Flask(__name__)

# Load dataset
df = pd.read_excel("D:\certificates\zomato_analysis (2)\zomato_analysis\data\Cleaned_Data_for_Analysis_Cleaned.xlsx")

# -------------------- GENERATE MAP FUNCTION --------------------
def generate_map(dataframe):
    """Generates a Folium map with restaurant markers."""
    m = folium.Map(location=[13.0827, 80.2707], zoom_start=12)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in dataframe.iterrows():
        popup_content = f"""
            <b>{row['Restaurant_Name']}</b><br>
            🍳 {row['Cuisine']}<br>
            💰 ₹{row['Price for 2']}
        """
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=popup_content
        ).add_to(marker_cluster)

    return m._repr_html_()

# -------------------- HOMEPAGE ROUTE --------------------
@app.route('/')
def public_user_map():
    """Loads the homepage with the map and filters."""
    map_html = generate_map(df)
    cuisines = sorted(df['Cuisine'].dropna().unique())
    features = sorted(df['Features'].dropna().unique())

    return render_template('public_user_map.html',
                           map_html=map_html,
                           cuisines=cuisines,
                           features=features)

# -------------------- PROXIMITY ANALYSIS --------------------
@app.route('/proximity', methods=['POST'])
def proximity():
    """Shows nearby restaurants within the user-defined radius and adds navigation links."""
    try:
        user_lat = float(request.form.get('latitude'))
        user_lon = float(request.form.get('longitude'))
        radius = float(request.form.get('radius', 300))  # Default 300m

        df['Distance'] = df.apply(lambda row: geodesic(
            (user_lat, user_lon), (row['Latitude'], row['Longitude'])).meters, axis=1)
        nearby_restaurants = df[df['Distance'] <= radius]

        # Generate map
        m = folium.Map(location=[user_lat, user_lon], zoom_start=15)
        folium.Marker(location=[user_lat, user_lon], popup="📍 You are here",
                      icon=folium.Icon(color='blue')).add_to(m)

        for _, row in nearby_restaurants.iterrows():
            navigation_url = f"https://www.google.com/maps/dir/{user_lat},{user_lon}/{row['Latitude']},{row['Longitude']}/"
            popup_content = f"""
                <b>{row['Restaurant_Name']}</b><br>
                🚶 {round(row['Distance'], 2)}m away<br>
                🍳 {row['Cuisine']}<br>
                💰 ₹{row['Price for 2']}<br>
                <a href="{navigation_url}" target="_blank">📍 Get Directions</a>
            """
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                popup=popup_content,
                icon=folium.Icon(color='green')
            ).add_to(m)

        return m._repr_html_()

    except Exception as e:
        return f"❌ Error: {str(e)}"

# -------------------- HEATMAP ANALYSIS --------------------
@app.route('/heatmap')
def heatmap():
    """Generates a heatmap showing restaurant density."""
    m = folium.Map(location=[13.0827, 80.2707], zoom_start=12)
    heat_data = [[row['Latitude'], row['Longitude']] for _, row in df.iterrows()]
    HeatMap(heat_data).add_to(m)
    return m._repr_html_()

# -------------------- FILTER RESTAURANTS --------------------
@app.route('/filter', methods=['POST'])
def filter_restaurants():
    """Filters restaurants based on cuisine and features."""
    cuisine = request.form.get('cuisine', 'All')
    feature = request.form.get('feature', 'All')

    filtered_data = df.copy()

    if cuisine != 'All':
        filtered_data = filtered_data[filtered_data['Cuisine'].str.contains(cuisine, case=False, na=False)]
    if feature != 'All':
        filtered_data = filtered_data[filtered_data['Features'].str.contains(feature, case=False, na=False)]

    return render_template('public_user_map.html', map_html=generate_map(filtered_data))

# -------------------- CUISINE POPULARITY ANALYSIS --------------------
@app.route('/cuisine_popularity')
def cuisine_popularity():
    """Generates interactive bar and pie charts for cuisine popularity."""
    cuisine_counts = df['Cuisine'].value_counts().head(10)

    # Bar chart using Plotly
    bar_fig = px.bar(cuisine_counts, x=cuisine_counts.index, y=cuisine_counts.values,
                     labels={'x': 'Cuisine', 'y': 'Number of Restaurants'},
                     title="Top 10 Most Popular Cuisines")
    bar_fig.update_traces(marker_color='skyblue')

    # Pie chart using Plotly
    pie_fig = px.pie(cuisine_counts, names=cuisine_counts.index, values=cuisine_counts.values,
                     title="Cuisine Popularity Distribution")

    # Convert to HTML
    bar_html = pio.to_html(bar_fig, full_html=False)
    pie_html = pio.to_html(pie_fig, full_html=False)

    return render_template('charts.html', bar_html=bar_html, pie_html=pie_html)

# -------------------- SENTIMENT ANALYSIS --------------------
@app.route('/sentiment_analysis')
def sentiment_analysis():
    """Generates an interactive sentiment heatmap and rating-based sentiment analysis."""

    if 'Dining Rating' not in df.columns:
        return "❌ No rating data available. Please update the dataset."

    # Define sentiment categories based on Dining Rating
    def categorize_sentiment(rating):
        if rating >= 4.0:
            return "😃 Positive"
        elif 2.5 <= rating < 4.0:
            return "😐 Neutral"
        else:
            return "😞 Negative"

    df['Sentiment'] = df['Dining Rating'].apply(categorize_sentiment)

    # Create a sentiment heatmap
    m = folium.Map(location=[13.0827, 80.2707], zoom_start=12)
    
    color_map = {"😃 Positive": "green", "😐 Neutral": "orange", "😞 Negative": "red"}

    for _, row in df.iterrows():
        popup_content = f"""
            <b>{row['Restaurant_Name']}</b><br>
            Rating: {row['Dining Rating']} ⭐<br>
            Sentiment: {row['Sentiment']}
        """
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=popup_content,
            icon=folium.Icon(color=color_map[row['Sentiment']])
        ).add_to(m)

    # Get top 5 best and worst restaurants
    top_positive = df[df['Dining Rating'] >= 4.5][['Restaurant_Name', 'Dining Rating']].head(5)
    top_negative = df[df['Dining Rating'] <= 2.5][['Restaurant_Name', 'Dining Rating']].head(5)

    return render_template('sentiment.html', map_html=m._repr_html_(), 
                           top_positive=top_positive.to_html(classes="table"), 
                           top_negative=top_negative.to_html(classes="table"))

@app.route('/affordability', methods=['GET', 'POST'])
def affordability():
    """Generates a heatmap showing affordability across restaurants with a search option."""
    
    # Get the search query from the request, if any
    search_query = request.form.get('search', '').lower()
    
    # Filter data based on search query
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[filtered_df['Restaurant_Name'].str.contains(search_query, case=False, na=False)]
    
    m = folium.Map(location=[13.0827, 80.2707], zoom_start=12)

    # Define a color scale based on 'Price for 2'
    def get_color(price):
        if price <= 300:
            return 'green'  # Budget-friendly
        elif 300 < price <= 700:
            return 'orange'  # Moderate price
        else:
            return 'red'  # Expensive

    # Loop through filtered restaurants
    for _, row in filtered_df.iterrows():
        color = get_color(row['Price for 2'])
        popup_content = f"""
            <b>{row['Restaurant_Name']}</b><br>
            🍳 {row['Cuisine']}<br>
            💰 ₹{row['Price for 2']}
        """
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=popup_content,
            icon=folium.Icon(color=color)
        ).add_to(m)

    # Render the map with the search bar
    return render_template('affordability.html', map_html=m._repr_html_(), search_query=search_query)

# -------------------- RUN APP --------------------
if __name__ == '__main__':
    app.run(debug=True)
