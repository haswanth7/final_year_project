from flask import Flask, render_template, request, jsonify
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
import plotly.express as px

app = Flask(__name__)

# Load dataset
df = pd.read_excel("D:\certificates\zomato_analysis (2)\zomato_analysis\data\Cleaned_Data_for_Analysis_Cleaned.xlsx")

# -------------------- GENERATE MAIN RESTAURANT MAP --------------------
def generate_main_map():
    """Generates an interactive Folium map with restaurant markers."""
    m = folium.Map(location=[13.0827, 80.2707], zoom_start=12)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df.iterrows():
        popup_content = f"""
            <b>{row['Restaurant_Name']}</b><br>
            🍳 {row['Cuisine']}<br>
            ⭐ {row['Dining Rating']} / 5<br>
            💰 ₹{row['Price for 2']}
        """
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=popup_content
        ).add_to(marker_cluster)

    return m._repr_html_()

# -------------------- HOME ROUTE --------------------
@app.route('/')
def home():
    return "Welcome to Business Dashboard! <a href='/business_dashboard'>Go to Dashboard</a>"

# -------------------- BUSINESS DASHBOARD --------------------
@app.route('/business_dashboard')
def business_dashboard():
    """Main business dashboard with all insights."""
    map_html = generate_main_map()
    return render_template('business_dashboard.html', map_html=map_html)

# -------------------- COMPETITOR HEATMAP --------------------
@app.route('/competitor_analysis')
def competitor_analysis():
    """Heatmap showing high competition areas."""
    m = folium.Map(location=[13.0827, 80.2707], zoom_start=12)
    heat_data = df[['Latitude', 'Longitude']].dropna().values.tolist()
    HeatMap(heat_data).add_to(m)
    return m._repr_html_()

# -------------------- DEMAND ANALYSIS (Bar Chart) --------------------
@app.route('/demand_analysis')
def demand_analysis():
    """Bar chart of top 10 high-demand areas based on reviews."""
    top_demand = df.groupby("Restaurant_Name")["Dining Rating Count"].sum().nlargest(10).reset_index()
    fig = px.bar(top_demand, x="Restaurant_Name", y="Dining Rating Count", title="Top 10 High-Demand Restaurants", labels={"Dining Rating Count": "Total Reviews"})
    return fig.to_html(full_html=False)

# -------------------- PRICING STRATEGY (Pie Chart) --------------------
@app.route('/pricing_strategy')
def pricing_strategy():
    """Pie chart of price ranges."""
    price_bins = pd.cut(df["Price for 2"], bins=[0, 500, 1000, 1500, 2000, 5000], labels=["<500", "500-1000", "1000-1500", "1500-2000", ">2000"])
    price_distribution = price_bins.value_counts().reset_index()
    price_distribution.columns = ["Price Range", "Count"]
    fig = px.pie(price_distribution, names="Price Range", values="Count", title="Pricing Strategy Analysis")
    return fig.to_html(full_html=False)

# -------------------- CUSTOMER PREFERENCE (Top Cuisines) --------------------
@app.route('/customer_preference')
def customer_preference():
    """Bar chart of most preferred cuisines."""
    top_cuisines = df["Cuisine"].value_counts().nlargest(10).reset_index()
    top_cuisines.columns = ["Cuisine", "Count"]
    fig = px.bar(top_cuisines, x="Cuisine", y="Count", title="Top Preferred Cuisines", labels={"Count": "Number of Restaurants"})
    return fig.to_html(full_html=False)

# -------------------- MARKET GAP ANALYSIS --------------------
@app.route('/market_gap')
def market_gap():
    m = folium.Map(location=[13.0827, 80.2707], zoom_start=12)

    # Bin latitude/longitude to create small areas (~1km blocks)
    df['lat_bin'] = df['Latitude'].round(2)
    df['lon_bin'] = df['Longitude'].round(2)

    # Get top cuisines in the city (most common)
    top_cuisines = df['Cuisine'].str.split(', ').explode().value_counts().head(10).index.tolist()

    # Group by area
    grouped = df.groupby(['lat_bin', 'lon_bin'])

    for (lat_bin, lon_bin), group in grouped:
        avg_rating = group['Dining Rating'].mean()
        restaurant_count = group.shape[0]

        if restaurant_count >= 3 and avg_rating < 3.5:
            area_cuisines = group['Cuisine'].str.split(', ').explode().unique().tolist()
            missing_cuisines = [c for c in top_cuisines if c not in area_cuisines]

            popup_content = f"""
                <b>Underserved Area</b><br>
                📍 Location: ({lat_bin}, {lon_bin})<br>
                ⭐ Avg Rating: {avg_rating:.2f}<br>
                🍽 Restaurants: {restaurant_count}<br>
                💡 <b>Suggested Cuisines:</b><br>
                {"<br>".join(missing_cuisines) if missing_cuisines else "All Top Cuisines Present"}
            """

            folium.CircleMarker(
                location=[lat_bin, lon_bin],
                radius=12,
                color='red',
                fill=True,
                fill_color='red',
                fill_opacity=0.6,
                popup=folium.Popup(popup_content, max_width=300)
            ).add_to(m)

    return m.get_root().render()
@app.route('/delivery_hotspots')
def delivery_hotspots():
    df_delivery = df[
        (df['Delivery Rating'].notnull()) &
        (df['Latitude'].notnull()) & 
        (df['Longitude'].notnull())
    ].copy()

    text_fields = ['Restaurant_Name', 'Cuisine', 'Price for 2', 'Features']
    for field in text_fields:
        df_delivery[field] = df_delivery[field].fillna('Not Available').astype(str)

    chennai_coords = [13.0827, 80.2707]
    m = folium.Map(location=chennai_coords, zoom_start=13, tiles="CartoDB positron")

    marker_cluster = MarkerCluster(name="Delivery Hotspots").add_to(m)

    for _, row in df_delivery.iterrows():
        popup_html = f"""
        <div style='font-size: 14px;'>
            <b>{row['Restaurant_Name']}</b><br>
            <b>Cuisine:</b> {row['Cuisine']}<br>
            <b>Delivery Rating:</b> {row['Delivery Rating']}<br>
            <b>Price for 2:</b> ₹{row['Price for 2']}<br>
            <b>Features:</b> {row['Features']}
        </div>
        """
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color="green", icon="motorcycle", prefix="fa")
        ).add_to(marker_cluster)

    heat_data = [[row['Latitude'], row['Longitude']] for index, row in df_delivery.iterrows()]
    HeatMap(heat_data, name="Delivery Density Heatmap", radius=15, blur=25, min_opacity=0.3).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m.get_root().render()
# -------------------- RUN FLASK APP --------------------
if __name__ == '__main__':
    app.run(debug=True, port=5002)
