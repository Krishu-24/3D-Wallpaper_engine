import cv2
import os
import tkinter as tk  # Used to get screen size for fullscreen display


# -----------------------------
# Future geometry variables
# Currently not used
# -----------------------------

# h_len = None          # Length of horizontal view at 70 cm from webcam in cm
# webcam_fov = None     # Total angle covered by the webcam in degrees
# rendered_fov = None   # Angle covered by the rendered image sequence in degrees


# -----------------------------
# Image sequence settings
# -----------------------------

folder = r"C:\Users\Arnav Sinha\Desktop\krishu\codes_projects\3D_Wallpaper_engine\assets\cube\test_cube_imageseq50_1"

image_start = 1
num_images = 50

images = []


# Load image sequence into memory
for i in range(num_images):
    frame = i + image_start

    # Example filename: 0001.png, 0002.png, 0003.png ...
    path = os.path.join(folder, f"{frame:04d}.png")

    img = cv2.imread(path)

    # Safety check in case an image path is wrong or image fails to load
    if img is None:
        print("Failed to load:", path)
    else:
        images.append(img)


# Reverse sequence if movement direction is opposite
images.reverse()


# Load Haar Cascade face detector
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


# Start webcam capture
cap = cv2.VideoCapture(0)


# Get screen size
root = tk.Tk()
screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
root.destroy()

# Create fullscreen wallpaper window
cv2.namedWindow("wallpaper", cv2.WINDOW_NORMAL)
cv2.setWindowProperty(
    "wallpaper",
    cv2.WND_PROP_FULLSCREEN,
    cv2.WINDOW_FULLSCREEN
)


# Start from the middle image until a face is detected
current_index = num_images // 2


# -----------------------------
# Main loop
# -----------------------------

while True:

    # Read frame from webcam
    ret, cam_f = cap.read()

    # If camera frame was not captured correctly, stop the loop
    if not ret:
        print("Failed to read from webcam")
        break

    # Convert camera frame to grayscale for face detection
    gray = cv2.cvtColor(cam_f, cv2.COLOR_BGR2GRAY)

    # Detect faces in the grayscale webcam frame
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    # If one or more faces are detected, use the first detected face
    for (x, y, w, h) in faces:

        # x is the left edge of the face rectangle.
        # Use the center of the face instead for better mapping.
        face_center_x = x + (w // 2)

        # Map face center x-coordinate to image sequence index.
        # Current usable camera x range is assumed to be 0 to 500.
        image_index = int((face_center_x / 500) * (num_images - 1))

        # Clamp index so it always stays between 0 and num_images - 1
        image_index = max(0, min(num_images - 1, image_index))

        # Store the latest valid image index
        current_index = image_index

        # Only use one face for now
        break

    # Select the image corresponding to the current face position
    img = images[current_index]

    # Resize image to fill the screen.
    # If render ratio matches screen ratio, this will not visually distort it.
    display_img = cv2.resize(img, (screen_w, screen_h))

    # Display fullscreen wallpaper image
    cv2.imshow("wallpaper", display_img)

    # Press Esc to exit
    k = cv2.waitKey(30) & 0xff
    if k == 27:
        break


# Cleanup
cap.release()
cv2.destroyAllWindows()