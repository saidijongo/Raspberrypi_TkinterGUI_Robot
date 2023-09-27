import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import json
import requests
from io import BytesIO
import RPi.GPIO as GPIO
import time
import os

# Defining the GPIO pins connected to the relay module
relay_pins = [23, 21, 19, 15, 13, 11, 7, 5, 31, 33, 35]

# Flow rate of the pump motors in mL/second
flow_rate = 105 / 60  # mL/second

# Loading recipes from JSON
with open('db.json') as file:
    recipes = json.load(file)

# Map the index of relay_pins with the pump motor number
motor_mapping = {i + 1: pin for i, pin in enumerate(relay_pins)}

def start_pump(motor_pin, volume):
    run_time = volume / flow_rate  # Calculate the run time based on volume
    
    try:
        GPIO.output(motor_pin, GPIO.LOW)  # Turn on the motor
        start_time = time.time()  # Record the start time
        time.sleep(run_time)  # Run the motor for the calculated time
        end_time = time.time()  # Record the end time
    except KeyboardInterrupt:
        print("Process interrupted by the user.")
    finally:
        GPIO.output(motor_pin, GPIO.HIGH)  # Turn off the motor
        elapsed_time = end_time - start_time
        print(f"Pumping {volume} mL from Motor {relay_pins.index(motor_pin) + 1}. Time: {int(elapsed_time // 60)} minutes {int(elapsed_time % 60)} seconds")
        return elapsed_time

def load_cocktail_image(cocktail):
    local_img_path = recipes[cocktail]['imgpath']
    if os.path.exists(local_img_path):
        try:
            image = Image.open(local_img_path)
            image = image.resize((210, 210), Image.BILINEAR)
            return ImageTk.PhotoImage(image)
        except Exception as e:
            print(f"Error loading image for {cocktail} from local imgpath: {e}")
    else:
        # Load the image from "image_url"
        response = requests.get(recipes[cocktail]['image_url'])
        try:
            image = Image.open(BytesIO(response.content))
            image = image.resize((210, 210), Image.BILINEAR)
            return ImageTk.PhotoImage(image)
        except Exception as e:
            print(f"Error loading image for {cocktail} from image_url: {e}")
    # Return None if image loading fails
    return None

def show_cocktail_details(cocktail):
    selected_cocktail.set(cocktail)
    cocktail_data = recipes[cocktail]

    details_label.config(text=f"Selected Cocktail\n{cocktail}")
    ingredients_label.config(text="\n".join([f"{ingredient['name']}: {ingredient['quantity']} mL" for ingredient in cocktail_data['ingredients']]))

    order_button.config(state=tk.NORMAL)

def make_cocktail(cocktail):
    print(f"Preparing 1 {cocktail}...")
    
    # Getting the ingredient motors and volumes for the selected cocktail
    ingredients = recipes[cocktail]['ingredients']
    
    # Calculate the estimated pump run times based on ingredient volumes
    run_times = [(motor_mapping[ingredient['motor']], ingredient['quantity']) for ingredient in ingredients]
    
    # Sort the run_times in ascending order of volume
    run_times.sort(key=lambda x: x[1])
    
    # Create a list to store start times
    start_times = []
    
    # Turn on all required motors
    for motor_pin, volume in run_times:
        elapsed_time = start_pump(motor_pin, volume)
        start_times.append(elapsed_time)  # Record the start time for each motor
    
    end_time = time.time()  # Record the end time for the last motor
    
    print("Cocktail ready!")
    
    # Calculate and print total time
    total_time = end_time - start_times[0]
    print(f"Total time: {int(total_time // 60)} minutes {int(total_time % 60)} seconds")

# Initialize GPIO setup
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
for pin in relay_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

# Create the main tkinter window
root = tk.Tk()
root.title("Cocktail Bartender Robot")

# Create frames
btn_frame = ttk.Frame(root, padding=10)
btn_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

order_frame = ttk.Frame(root, padding=10)
order_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

custom_frame = ttk.Frame(root, padding=10)
custom_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

# Create vertical dotted line separator
separator = ttk.Separator(root, orient="vertical")
separator.grid(row=0, column=1, rowspan=2, sticky="ns")

# Create horizontal dotted line separator
separator2 = ttk.Separator(root, orient="horizontal")
separator2.grid(row=1, column=0, columnspan=3, sticky="ew")

# Initialize variables
selected_cocktail = tk.StringVar()
selected_cocktail.set("")

# Dropdown menu to select the ingredient motor
selected_motor = tk.StringVar()
ingredient_motor_dropdown = ttk.Combobox(custom_frame, textvariable=selected_motor)
motor_options = [f"Motor {i+1}" for i in range(len(relay_pins))] + ["All Motors"]
ingredient_motor_dropdown['values'] = motor_options
ingredient_motor_dropdown.pack()

# Entry field to input the volume
volume_label = ttk.Label(custom_frame, text="Enter Volume (mL):")
volume_label.pack(pady=10)
volume_entry = ttk.Entry(custom_frame)
volume_entry.pack()

# Start button to activate the selected motor
start_button = ttk.Button(custom_frame, text="Start", command=lambda: start_pump(motor_mapping[selected_motor.get()], int(volume_entry.get())))
start_button.pack(pady=10)

# Initialize labels
details_label = ttk.Label(order_frame, text="Selected Cocktail", font=("Helvetica", 14, "bold"))
details_label.grid(row=0, column=0, columnspan=2, pady=10)

ingredients_label = ttk.Label(order_frame, text="", font=("Helvetica", 12))
ingredients_label.grid(row=1, column=0, columnspan=2, pady=10)

order_button = ttk.Button(order_frame, text="Click to order", command=lambda: make_cocktail(selected_cocktail.get()), state=tk.DISABLED)
order_button.grid(row=2, column=0, columnspan=2, pady=10)

# Load cocktail images and create buttons
cocktail_buttons = []
for i, cocktail in enumerate(recipes):
    image = load_cocktail_image(cocktail)
    if image:
        cocktail_button = ttk.Button(btn_frame, image=image, text=cocktail, compound=tk.TOP, command=lambda c=cocktail: show_cocktail_details(c))
        cocktail_button.grid(row=i // 2, column=i % 2, padx=10, pady=10)
        cocktail_buttons.append(cocktail_button)

# Configure grid weights for frame resizing
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=0)
root.grid_columnconfigure(2, weight=1)

# Start the tkinter main loop
root.mainloop()

# Cleanup GPIO
GPIO.cleanup()
