from flask import Flask, render_template, request
import pandas as pd
import folium

app = Flask(__name__)

# Load data
DATA_PATH = r"M:\zomato_analysis\data\Cleaned_Data_for_Analysis_Cleaned.xlsx"
df = pd.read_excel(DATA_PATH)

@app.route('/')
def public_user_map():
    # Generate Map
    m = folium.Map(location=[13.0827, 80.2707], zoom_start=12)

    # Add all restaurants to map initially
    for idx, row in df.iterrows():
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=f"{row['Restaurant_Name']}<br>{row['Cuisine']}<br>₹{row['Price for 2']}"
        ).add_to(m)

    map_html = m._repr_html_()

    # Ensure filter options are populated
    cuisines = sorted(df['Cuisine'].dropna().unique().tolist())
    features = sorted(df['Features'].dropna().unique().tolist())

    return render_template('public_user_map.html', map_html=map_html, cuisines=cuisines, features=features)

@app.route('/filter', methods=['POST'])
def filter_data():
    cuisine = request.form.get('cuisine')
    feature = request.form.get('feature')
    price_range = request.form.get('price_range')

    filtered_df = df.copy()

    if cuisine and cuisine != 'All':
        filtered_df = filtered_df[filtered_df['Cuisine'].str.contains(cuisine, case=False, na=False)]

    if feature and feature != 'All':
        filtered_df = filtered_df[filtered_df['Features'].str.contains(feature, case=False, na=False)]

    if price_range:
        try:
            max_price = int(price_range)
            filtered_df = filtered_df[filtered_df['Price for 2'] <= max_price]
        except ValueError:
            pass

    # Map with filtered data
    m = folium.Map(location=[13.0827, 80.2707], zoom_start=12)
    for idx, row in filtered_df.iterrows():
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=f"{row['Restaurant_Name']}<br>{row['Cuisine']}<br>₹{row['Price for 2']}"
        ).add_to(m)

    map_html = m._repr_html_()

    # Re-populate filter options
    cuisines = sorted(df['Cuisine'].dropna().unique().tolist())
    features = sorted(df['Features'].dropna().unique().tolist())

    return render_template('public_user_map.html', map_html=map_html, cuisines=cuisines, features=features)

if __name__ == '__main__':
    app.run(debug=True)
