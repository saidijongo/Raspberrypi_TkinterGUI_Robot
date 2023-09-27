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

def start_pump():
    motor_name = ingredient_motor_dropdown.get()
    volume = int(volume_entry.get())
    
    if motor_name == "All Motors":
        for motor_pin in relay_pins:
            run_motor(motor_pin, volume)
    else:
        motor_pin = motor_mapping[int(motor_name.split()[-1])]
        run_motor(motor_pin, volume)

def run_motor(motor_pin, volume):
    run_time = volume / flow_rate  # Calculate the run time based on volume
    
    try:
        GPIO.output(motor_pin, GPIO.LOW)  # Turn on the motor
        time.sleep(run_time)  # Run the motor for the calculated time
    except KeyboardInterrupt:
        print("Process interrupted by the user.")
    finally:
        GPIO.output(motor_pin, GPIO.HIGH)  # Turn off the motor
        print(f"Pumping {volume} mL from Motor {relay_pins.index(motor_pin) + 1}")
        print("Pumping complete!")

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
    run_times = [(motor_mapping[ingredient['motor']], ingredient['quantity'] / flow_rate) for ingredient in ingredients]
    
    # Sort the run_times in ascending order of run time
    run_times.sort(key=lambda x: x[1])
    
    # Turn on all required motors
    for motor_pin, _ in run_times:
        GPIO.output(motor_pin, GPIO.LOW)
    
    # Waiting for the longest run time (time for the last motor to stop)
    longest_run_time = run_times[-1][1]
    time.sleep(longest_run_time)
    
    # Turning off relays for each motor based on their individual run times
    for motor_pin, run_time in run_times:
        GPIO.output(motor_pin, GPIO.HIGH)
        time.sleep(run_time)
    
    print("Cocktail ready!")

# Initialize GPIO setup
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
for pin in relay_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

# Create the main tkinter window
root = tk.Tk()
root.title("Cocktail Bartending Robot")
root.geometry("700x500")

# Create the left frame (btn_frame) for cocktail image buttons
btn_frame = tk.Frame(root, bg="white")
btn_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky="nsew")

# Create the vertical dotted line
separator = ttk.Separator(root, orient="vertical")
separator.grid(row=0, column=1, rowspan=2, sticky="ns")

# Create the right frame (order_frame) for cocktail details and order button
order_frame = tk.Frame(root, bg="white")
order_frame.grid(row=0, column=2, rowspan=2, padx=10, pady=10, sticky="nsew")

# Create the horizontal dotted line
separator = ttk.Separator(root, orient="horizontal")
separator.grid(row=2, column=0, columnspan=3, pady=10, sticky="ew")

# Create the bottom frame (custom_frame) for pump motor selection and volume input
custom_frame = tk.Frame(root, bg="white")
custom_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

# Dropdown menu to select the ingredient motor
selected_motor = tk.StringVar()
ingredient_motor_dropdown = ttk.Combobox(custom_frame, textvariable=selected_motor)
ingredient_motor_dropdown['values'] = [f"Motor {i+1}" for i in range(len(relay_pins))] + ["All Motors"]
ingredient_motor_dropdown.pack()

label = ttk.Label(custom_frame, text="Enter Volume (ml):")
label.pack(pady=10)

# Entry field to input the volume
volume_entry = ttk.Entry(custom_frame)
volume_entry.pack()

start_button = ttk.Button(custom_frame, text="Start", command=start_pump)
start_button.pack(pady=10)

# Initialize variables for selected cocktail and its image
selected_cocktail = tk.StringVar()
selected_image = tk.PhotoImage()

# Create labels for selected cocktail and ingredients
details_label = ttk.Label(order_frame, text="", font=("Helvetica", 16, "bold"))
details_label.grid(row=0, column=0, columnspan=2)

ingredients_label = ttk.Label(order_frame, text="", font=("Helvetica", 12))
ingredients_label.grid(row=1, column=0, columnspan=2)

# Create a button to order the cocktail
order_button = ttk.Button(order_frame, text="Click to order", state=tk.DISABLED, command=lambda: make_cocktail(selected_cocktail.get()))
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
root.grid_rowconfigure(1, weight=1)
root.grid_rowconfigure(2, weight=0)
root.grid_rowconfigure(3, weight=0)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=0)
root.grid_columnconfigure(2, weight=1)

# Start the tkinter main loop
root.mainloop()

# Cleanup GPIO
GPIO.cleanup()
