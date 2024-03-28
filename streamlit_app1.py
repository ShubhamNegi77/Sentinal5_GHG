import streamlit as st
import ee
import geemap
import matplotlib.pyplot as plt
import folium

# Set page configuration to wide mode
st.set_page_config(layout="wide")

# Authenticate Earth Engine
ee.Authenticate()
ee.Initialize(project="ee-shubhamnegi7")


# Define a function to get methane emission data
def get_methane_emission(year, india_geometry, scale=100000):
    try:
        # Load the methane emission dataset
        methane_dataset = ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_CH4").filterDate(
            str(year) + "-01-01", str(year) + "-12-31"
        )

        # Check if there are any images in the collection for the given year
        count = methane_dataset.size().getInfo()
        if count == 0:
            return None

        # Reduce the dataset to a single image by taking the mean
        mean_methane_image = methane_dataset.mean()

        # Clip the image to the geometry of India
        clipped_methane_image = mean_methane_image.clip(india_geometry)

        # Check if clipped_methane_image has at least one band before multiplication
        if clipped_methane_image.bandNames().length().gt(0).getInfo():
            # If there is at least one band, proceed with the multiplication
            methane_emission_percentage = clipped_methane_image.multiply(
                0.000001
            ).multiply(100)

            # Reduce region to get mean methane emission value
            methane_emission_value = methane_emission_percentage.reduceRegion(
                reducer=ee.Reducer.mean(), geometry=india_geometry, scale=scale
            )

            return methane_emission_value
        else:
            return None
    except ee.EEException as e:
        print("An error occurred:", e)
        return None


# Define the geometry of India
india_geometry = ee.Geometry.Rectangle(68.7, 7.5, 97.5, 35.5)

# Create the Streamlit app
st.title("Methane Emission Data for India")

# Year range selection
left_column, middle_column, right_column, right_most = st.columns(4)
with left_column:
    start_year = st.number_input(
        "Start Year", min_value=2000, max_value=2023, value=2019
    )
with middle_column:
    end_year = st.number_input(
        "End Year", min_value=start_year, max_value=2023, value=2023
    )
with right_column:
    threshold = st.number_input("Threshold", min_value=1000, max_value=2000, value=1850)
with right_most:
    year = st.number_input("Year", min_value=2000, max_value=2023, value=2019)


# Initialize lists to store years and methane emission values
years = []
methane_values = []

# Loop through each selected year
for year in range(start_year, end_year + 1):
    # Get methane emission data for the current year
    methane_emission_value = get_methane_emission(year, india_geometry)

    # Store methane emission data for the current year in the lists
    if methane_emission_value is not None:
        years.append(year)
        methane_values.append(
            methane_emission_value.get(
                "CH4_column_volume_mixing_ratio_dry_air"
            ).getInfo()
        )

# Display methane emission data for selected years
if not years:
    st.write("No methane emission data available for the selected years and country.")
else:
    # Plot methane emission data using matplotlib
    left_column, right_column = st.columns(2)

    with left_column:
        plt.figure(figsize=(12, 6))  # Larger figure size
        plt.plot(years, methane_values, marker="o", linestyle="-")
        plt.xlabel("Year")
        plt.ylabel("Methane Emission (CH4_column_volume_mixing_ratio_dry_air)")
        plt.title("Methane Emission Data for India")
        plt.grid(True)
        plt.xticks(range(start_year, end_year + 1))

        st.pyplot(plt)

    # Display the map on the right column
    with right_column:
        # Define a function to create the map
        def create_map():
            # Define the image collection for methane emissions
            collection = (
                geemap.ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_CH4")
                .select("CH4_column_volume_mixing_ratio_dry_air")
                .filterDate(f"{year}-06-01", f"{year}-07-16")
            )

            # Define the center of India
            center_of_india = [20.5937, 78.9629]

            # Create a map centered on India
            Map = geemap.Map(
                center=center_of_india, zoom=4, width="100%", height="600px"
            )  # Larger map size

            # Define visualization parameters
            band_viz = {
                "min": 1750,
                "max": 1900,
                "palette": [
                    "black",
                    "blue",
                    "purple",
                    "cyan",
                    "green",
                    "yellow",
                    "red",
                ],
            }

            # Add the methane emission layer to the map
            Map.addLayer(collection.mean(), band_viz, "Methane Emission")

            # Threshold methane emissions to identify areas with higher emissions
            high_emission_mask = collection.mean().gt(threshold)

            # Clip the emission mask to the geometry of India
            india_boundary = geemap.ee.Geometry.Polygon(
                [
                    [68.1766451354, 7.96553477623],
                    [97.4025614766, 7.96553477623],
                    [97.4025614766, 35.4940095078],
                    [68.1766451354, 35.4940095078],
                ]
            )
            high_emission_mask = high_emission_mask.clip(india_boundary)

            # Add the high methane emission mask to the map
            Map.addLayer(
                high_emission_mask.updateMask(high_emission_mask),
                {"palette": "red"},
                "High Methane Emission",
            )
            Map.add_legend(legend_keys=["High Methane Emission"], legend_colors=["red"])

            return Map

        # Display the map
        Map = create_map()
        Map.to_streamlit()
