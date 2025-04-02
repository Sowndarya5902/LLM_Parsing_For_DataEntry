import streamlit as st
import os
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import tempfile
import io
import json  
import re

# Set the Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  

# Function to process the uploaded PDF and convert it to an image
def input_pdf_setup(uploaded_file):
    # Check if a file has been uploaded
    if uploaded_file is not None:
        # Create a temporary file to save the uploaded PDF in a user-specified folder
        temp_dir = r"C:\path\to\your\temp\folder"  # Replace this with a folder you have write access to
        os.makedirs(temp_dir, exist_ok=True)  # Ensure the folder exists

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir=temp_dir) as tmp_pdf:
            tmp_pdf.write(uploaded_file.getvalue())  # Write the PDF data into the temp file
            tmp_pdf_path = tmp_pdf.name  # Get the file path for conversion

        # Specify the Poppler path (adjust this to your local path)
        poppler_path = r"C:\poppler-24.08.0\Library\bin"

        # Convert the first page of the PDF to an image
        images = convert_from_path(tmp_pdf_path, first_page=1, last_page=1, poppler_path=poppler_path)

        # Convert the PIL Image to bytes (JPEG format)
        byte_io = io.BytesIO()
        images[0].save(byte_io, format="JPEG")
        image_bytes = byte_io.getvalue()  # Get the byte data of the image
        image_parts = [{"mime_type": "image/jpeg", "data": image_bytes}]
        return image_parts, images[0]  # Return the image object too
    else:
        raise FileNotFoundError("No file uploaded")

# Function to extract purchase details from OCR text
def extract_purchase_details(text):
    # Define regex patterns for the details (you may need to adjust these based on invoice format)
    items = []
    
    # Adjust the regex pattern to capture item names, codes, quantities, prices, and totals
    item_pattern = re.compile(r"(\d+)\s*([A-Za-z0-9\s]+?)\s*(\d+)\s*\$?(\d+\.\d{2})\s*\$?(\d+\.\d{2})")  # Item rows
    total_pattern = re.compile(r"Total\s*\$?(\d+\.\d{2})")  # Total amount pattern
    
    # Extract items using the regex pattern
    for match in item_pattern.finditer(text):
        item_code = match.group(1)
        item_name = match.group(2).strip()  
        quantity = int(match.group(3))
        item_price = float(match.group(4))
        total = float(match.group(5))

        # Append the item details to the list
        items.append({
            "item_code": item_code,
            "item_name": item_name,
            "quantity": quantity,
            "item_price": item_price,
            "total": total
        })

    # Extract total order amount
    total_match = total_pattern.search(text)
    order_amount = None
    if total_match:
        order_amount = float(total_match.group(1))

    # Return the purchase details in JSON format
    purchase_details = {
        "items": items,
        "order_amount": order_amount
    }
    
    return purchase_details

# Function to extract seller details (name, email, phone, address)
def extract_seller_details(text):
    # Regex patterns for extracting seller details
    seller_details = {
        "seller_name": None,
        "seller_email": None,
        "seller_phone": None,
        "seller_address": None
    }
    
    # Adjusted regex for seller name, email, phone, and address without using lookbehind
    name_pattern = re.compile(r"(Seller|Vendor|From)\s*[:\-]?\s*([A-Za-z0-9\s]+)")
    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    phone_pattern = re.compile(r"\(?\+?[0-9]*\)?[\s.-]?[0-9]+[\s.-]?[0-9]+[\s.-]?[0-9]+")
    address_pattern = re.compile(r"(Address\s*[:\-]?\s*[A-Za-z0-9\s,]+)") 
    
    # Extract seller name (matches "Seller:", "Vendor:", or "From:" labels)
    name_match = name_pattern.search(text)
    if name_match:
        seller_details["seller_name"] = name_match.group(2).strip()

    # Extract seller email
    email_match = email_pattern.search(text)
    if email_match:
        seller_details["seller_email"] = email_match.group(0).strip()

    # Extract seller phone number
    phone_match = phone_pattern.search(text)
    if phone_match:
        seller_details["seller_phone"] = phone_match.group(0).strip()

    # Extract seller address
    address_match = address_pattern.search(text)
    if address_match:
        seller_details["seller_address"] = address_match.group(1).strip()

    return seller_details

# Initialize the Streamlit app
st.set_page_config(page_title="Gemini AI")
st.header("LLM Parsing")

# Get input prompt from the user
input = st.text_input("Input Prompt: ", key="input")

uploaded_file = st.file_uploader("Choose a PDF...", type=["pdf"])
image = ""   

if uploaded_file is not None:
    try:
        # Convert the uploaded PDF to an image
        image_data, image = input_pdf_setup(uploaded_file)  
        st.image(image, caption="Uploaded PDF Page.", use_column_width=True)

        # Display the button after the image
        submit = st.button("Tell me about the image")
        
        if submit:
            # Perform OCR to extract text from the image
            ocr_text = pytesseract.image_to_string(image)
            
            # Extract purchase details
            purchase_details = extract_purchase_details(ocr_text)
            
            # Extract seller details
            seller_details = extract_seller_details(ocr_text)
            
            # Combine both seller and purchase details
            result = {
                "seller_details": seller_details,
                "purchase_details": purchase_details
            }
            
            # Display the combined result in JSON format
            st.subheader("The Extracted Details (JSON):")
            st.json(result)  # Displaying the response in JSON format

    except Exception as e:
        st.error(f"Error: {e}")

else:
    st.error("Please upload a PDF file to proceed.")
