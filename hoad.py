import streamlit as st
import pandas as pd
import os
import uuid
from PIL import Image
from pathlib import Path
import datetime
import smtplib
from email.mime.text import MIMEText

# -----------------------------
# Configuration
# -----------------------------
DATA_FILE = "hoardings.csv"
BOOKINGS_FILE = "bookings.csv"
IMAGE_DIR = "hoarding_images"
DISTRICTS = ["Raipur", "Durg"]
MAX_IMAGES = 5

# Create directories if they don't exist
Path(IMAGE_DIR).mkdir(parents=True, exist_ok=True)

# -----------------------------
# CSS and Styling
# -----------------------------
def inject_custom_css():
    st.markdown(
        """
        <style>
            .hoarding-card {
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 20px;
                margin: 15px 0;
                background: #ffffff;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            }
            .placeholder-image {
                background: #f8f9fa;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                color: #6c757d;
                width: 100%;
                height: 200px;
            }
            .status-available { color: #28a745; }
            .status-booked { color: #dc3545; }
            /* Book Now button styling */
            #book-now-container button {
                background-color: #28a745 !important;
                color: white !important;
                border: none !important;
                padding: 8px 16px !important;
                border-radius: 4px !important;
                cursor: pointer !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

# -----------------------------
# Data Loading & Saving
# -----------------------------
def load_data():
    """Load hoardings data, ensuring correct columns and dtypes."""
    try:
        df = pd.read_csv(DATA_FILE)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        # Create empty DataFrame if file not found or empty
        df = pd.DataFrame(columns=[
            "id", "location", "district", "size", "price",
            "is_available", "landmark", "coordinates",
            "address", "images"
        ])
    
    # Ensure missing columns exist
    for col in ["images", "landmark", "coordinates", "address"]:
        if col not in df.columns:
            df[col] = ""
    
    # Convert images from '|' string to list
    if "images" in df.columns:
        df["images"] = df["images"].apply(lambda x: x.split("|") if pd.notna(x) and x != "" else [])
    
    # Attempt to convert numeric columns to proper dtype
    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
    # Convert is_available to boolean if it exists
    if "is_available" in df.columns:
        # Convert any non-boolean to boolean. If invalid, default to False.
        df["is_available"] = df["is_available"].apply(lambda x: True if str(x).lower() in ["true", "1"] else False)
    
    return df

def save_data(df):
    """Save hoardings data to CSV, converting images to '|' string."""
    if "images" in df.columns:
        df["images"] = df["images"].apply(lambda x: "|".join(x) if x else "")
    df.to_csv(DATA_FILE, index=False)

def load_bookings():
    """Load booking data from CSV (creates file if not found)."""
    try:
        bdf = pd.read_csv(BOOKINGS_FILE)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        bdf = pd.DataFrame(columns=[
            "booking_id", "hoarding_id", "user_name",
            "phone", "email", "start_date", "end_date",
            "status"
        ])
    return bdf

def save_bookings(bdf):
    """Save bookings data to CSV."""
    bdf.to_csv(BOOKINGS_FILE, index=False)

# -----------------------------
# Image Handling
# -----------------------------
def handle_image_upload():
    """Handle multiple image uploads and return list of saved file paths."""
    uploaded_files = st.file_uploader(
        "Upload Hoarding Photos (Max 5)",
        type=["jpg", "png", "jpeg"],
        accept_multiple_files=True
    )
    saved_paths = []
    for uploaded_file in uploaded_files[:MAX_IMAGES]:
        try:
            img = Image.open(uploaded_file)
            ext = uploaded_file.type.split("/")[-1]
            filename = f"{uuid.uuid4()}.{ext}"
            filepath = Path(IMAGE_DIR) / filename
            img.save(filepath)
            saved_paths.append(str(filepath))
        except Exception as e:
            st.error(f"Error saving {uploaded_file.name}: {str(e)}")
    return saved_paths

def show_hoarding_images(image_paths):
    """
    Show the hoarding images in a placeholder-like box.
    If multiple images exist, just show the first for this layout.
    """
    valid_paths = [p for p in image_paths if Path(p).exists() and Path(p).is_file()]
    if not valid_paths:
        st.markdown("<div class='placeholder-image'>No photos available</div>", unsafe_allow_html=True)
        return
    st.image(valid_paths[0], use_column_width=True)

# -----------------------------
# Booking Form
# -----------------------------
def booking_form(hoarding_id):
    """
    Show a booking form for the selected hoarding.
    - Collect user details and create a new booking in bookings.csv
    """
    st.subheader("Book Hoarding")
    bdf = load_bookings()
    
    with st.form("booking_form", clear_on_submit=True):
        user_name = st.text_input("Your Name")
        phone = st.text_input("Phone Number")
        email = st.text_input("Email Address")
        start_date = st.date_input("Start Date", datetime.date.today())
        end_date = st.date_input("End Date", datetime.date.today())
        
        if st.form_submit_button("Confirm Booking"):
            # Validate user input
            if not user_name or not phone or not email:
                st.error("Please fill all required fields.")
            elif end_date < start_date:
                st.error("End date cannot be before start date.")
            else:
                new_booking = {
                    "booking_id": str(uuid.uuid4()),
                    "hoarding_id": hoarding_id,
                    "user_name": user_name,
                    "phone": phone,
                    "email": email,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "status": "Pending"
                }
                bdf = pd.concat([bdf, pd.DataFrame([new_booking])], ignore_index=True)
                save_bookings(bdf)
                st.success("Booking created successfully!")
                st.balloons()

# -----------------------------
# Main Application
# -----------------------------
def main():
    st.set_page_config(
        page_title="CG Hoarding Management",
        page_icon="🏙️",
        layout="wide"
    )
    inject_custom_css()
    
    st.title("Chhattisgarh Hoarding Management System")
    st.markdown("**Manage 100+ Advertising Spaces Across Raipur & Durg**")
    
    # -----------------------------
    # Sidebar Operations with Default
    # -----------------------------
    # If a default operation is set in session_state (e.g., "Bookings" from a Book Now click), use that.
    operations = ["View Hoardings", "Add New", "Edit Existing", "Bookings"]
    if "default_operation" in st.session_state:
        default_index = operations.index(st.session_state["default_operation"])
        operation = st.sidebar.radio("Select Operation", operations, index=default_index)
        # Clear the default after using it
        del st.session_state["default_operation"]
    else:
        operation = st.sidebar.radio("Select Operation", operations)
    
    # Load data
    df = load_data()
    bdf = load_bookings()  # Load bookings to display them if needed
    
    # --------------------------------
    # 1. View Hoardings
    # --------------------------------
    if operation == "View Hoardings":
        st.header("Available Hoarding Spaces")
        
        if df.empty:
            st.warning("No hoardings available in database")
            return
        
        # Filters
        with st.expander("Filter Options", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                district_filter = st.selectbox("District", ["All"] + DISTRICTS)
            with col2:
                status_filter = st.selectbox("Availability", ["All", "Available", "Booked"])
            with col3:
                size_filter = st.text_input("Size Contains")
        
        # Apply filters
        filtered_df = df.copy()
        if district_filter != "All":
            filtered_df = filtered_df[filtered_df.district == district_filter]
        if status_filter != "All":
            is_avail = (status_filter == "Available")
            filtered_df = filtered_df[filtered_df.is_available == is_avail]
        if size_filter:
            filtered_df = filtered_df[filtered_df.size.str.contains(size_filter, case=False, na=False)]
        
        # Display hoardings
        for _, row in filtered_df.iterrows():
            st.markdown("<div class='hoarding-card'>", unsafe_allow_html=True)
            
            # Two-column layout: images on the left, details on the right
            col_left, col_right = st.columns([1, 2])
            
            with col_left:
                # Show hoarding images
                show_hoarding_images(row["images"])
            
            with col_right:
                # Basic details (like a product listing)
                st.markdown(f"### {row['location']}")
                st.markdown(f"**ID:** `{row['id']}`")
                st.markdown(f"**District:** {row['district']}")
                st.markdown(f"**Size:** {row['size']}")
                
                # Price and status
                st.markdown(f"**Price:** ₹{row['price'] if not pd.isna(row['price']) else 'N/A'}/month")
                status_text = "Available" if row["is_available"] else "Booked"
                status_class = "status-available" if row["is_available"] else "status-booked"
                st.markdown(f"**Status:** <span class='{status_class}'>{status_text}</span>", unsafe_allow_html=True)
                
                # Landmark
                st.markdown(f"**Landmark:** {row['landmark'] or 'Not specified'}")
                
                # Expandable location details
                with st.expander("Location Details"):
                    st.markdown(f"**Address:** {row['address']}")
                    if row["coordinates"]:
                        st.markdown(f"**Coordinates:** {row['coordinates']}")
                
                # If hoarding is available, show a "Book Now" button
                if row["is_available"]:
                    if st.button("Book Now", key=f"book_{row['id']}"):
                        # Store the hoarding ID in session_state for booking
                        st.session_state["selected_hoarding_for_booking"] = row["id"]
                        # Set default operation to "Bookings" so that on rerun the booking tab is active
                        st.session_state["default_operation"] = "Bookings"
                        try:
                            st.experimental_rerun()
                        except:
                            pass
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    # --------------------------------
    # 2. Add New Hoarding
    # --------------------------------
    elif operation == "Add New":
        st.header("Add New Hoarding Space")
        
        with st.form("add_form", clear_on_submit=True):
            cols = st.columns(2)
            with cols[0]:
                st.markdown("### Basic Details")
                location = st.text_input("Location Name", key="loc_name")
                district = st.selectbox("District", DISTRICTS)
                size = st.text_input("Dimensions (WxH)")
                price = st.number_input("Monthly Price (₹)", min_value=0, step=500, value=0)
            
            with cols[1]:
                st.markdown("### Location Details")
                landmark = st.text_input("Nearest Landmark")
                coordinates = st.text_input("GPS Coordinates")
                address = st.text_area("Full Address")
                images = handle_image_upload()
            
            is_available = st.checkbox("Mark as available", value=True)
            
            if st.form_submit_button("Submit Hoarding"):
                if not all([location, district, size]):
                    st.error("Please fill all required fields (location, district, size).")
                else:
                    new_hoarding = {
                        "id": str(uuid.uuid4()),
                        "location": location,
                        "district": district,
                        "size": size,
                        "price": float(price),
                        "is_available": bool(is_available),
                        "landmark": landmark,
                        "coordinates": coordinates,
                        "address": address,
                        "images": images
                    }
                    df = pd.concat([df, pd.DataFrame([new_hoarding])], ignore_index=True)
                    save_data(df)
                    st.success("Hoarding added successfully!")
                    st.balloons()
    
    # --------------------------------
    # 3. Edit Existing Hoarding
    # --------------------------------
    elif operation == "Edit Existing":
        st.header("Modify Existing Hoarding")
        
        if df.empty:
            st.warning("No hoardings available for editing")
            return
        
        # Hoarding Selector
        hoarding_list = df.apply(
            lambda x: f"{x['id']} | {x['location']} ({x['district']})",
            axis=1
        ).tolist()
        
        selected = st.selectbox("Select Hoarding", hoarding_list)
        hoarding_id = selected.split("|")[0].strip()
        hoarding_data = df[df.id == hoarding_id].iloc[0]
        
        # Edit Form
        with st.form("edit_form"):
            cols = st.columns(2)
            with cols[0]:
                st.markdown("### Basic Details")
                new_location = st.text_input("Location", value=hoarding_data["location"])
                new_district = st.selectbox(
                    "District",
                    DISTRICTS,
                    index=DISTRICTS.index(hoarding_data["district"])
                )
                new_size = st.text_input("Size", value=hoarding_data["size"])
                new_price_val = hoarding_data["price"] if not pd.isna(hoarding_data["price"]) else 0
                new_price = st.number_input("Price", value=float(new_price_val), step=500.0)
            
            with cols[1]:
                st.markdown("### Location Details")
                new_landmark = st.text_input("Landmark", value=hoarding_data["landmark"])
                new_coords = st.text_input("Coordinates", value=hoarding_data["coordinates"])
                new_address = st.text_area("Address", value=hoarding_data["address"])
                new_images = handle_image_upload()
                existing_images = hoarding_data["images"]
            
            new_available = st.checkbox("Available", value=hoarding_data["is_available"])
            
            if st.form_submit_button("Update Hoarding"):
                updates = {
                    "location": new_location,
                    "district": new_district,
                    "size": new_size,
                    "price": float(new_price),
                    "landmark": new_landmark,
                    "coordinates": new_coords,
                    "address": new_address,
                    "is_available": bool(new_available),
                    "images": existing_images + new_images,
                }
                
                row_index = df.index[df.id == hoarding_id][0]
                for key, value in updates.items():
                    df.at[row_index, key] = value
                save_data(df)
                
                st.success("Hoarding updated successfully!")
                try:
                    st.experimental_rerun()
                except:
                    pass
    
    # --------------------------------
    # 4. Bookings
    # --------------------------------
    elif operation == "Bookings":
        st.header("Booking Management")
        
        # If the user clicked "Book Now" from View Hoardings, show booking form
        if "selected_hoarding_for_booking" in st.session_state:
            hoarding_to_book = st.session_state["selected_hoarding_for_booking"]
            st.info(f"You are booking hoarding: {hoarding_to_book}")
            booking_form(hoarding_to_book)
        else:
            st.info("No hoarding selected for booking at the moment.")
        
        # Display existing bookings
        bdf = load_bookings()
        if not bdf.empty:
            st.subheader("Existing Bookings")
            st.dataframe(bdf)
        else:
            st.warning("No bookings yet.")

if __name__ == "__main__":
    main()
