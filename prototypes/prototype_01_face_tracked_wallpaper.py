import cv2
import os
import math
import tkinter as tk
from dotenv import load_dotenv

load_dotenv()

folder = os.getenv("IMAGE_SEQUENCE_FOLDER")

if folder is None:
    print("IMAGE_SEQUENCE_FOLDER is not set in .env")
    exit()

image_start = 1

x_steps = 60
y_steps = 9

distance_from_camera_cm = 45.8

camera_x_range_cm = 47.0
camera_y_range_cm = 34.0

rendered_x_fov_min = -30.0
rendered_x_fov_max = 30.0

rendered_y_fov_min = -10.0
rendered_y_fov_max = 10.0

reverse_x = True
reverse_y = False

smooth_strength = 0.25

num_images = x_steps * y_steps
images = []

for i in range(num_images):
    frame = image_start + i
    path = os.path.join(folder, f"view_{frame:04d}.png")
    img = cv2.imread(path)

    if img is None:
        print("Failed to load:", path)
    else:
        images.append(img)

if len(images) != num_images:
    print("Expected images:", num_images)
    print("Loaded images:", len(images))
    exit()

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

cap = cv2.VideoCapture(0)

ret, test_frame = cap.read()

if not ret:
    print("Failed to read webcam")
    cap.release()
    exit()

frame_h, frame_w = test_frame.shape[:2]

print("Camera frame:", frame_w, "x", frame_h)

camera_x_fov = math.degrees(
    2 * math.atan((camera_x_range_cm / 2) / distance_from_camera_cm)
)

camera_y_fov = math.degrees(
    2 * math.atan((camera_y_range_cm / 2) / distance_from_camera_cm)
)

print("Measured camera X FOV:", camera_x_fov)
print("Measured camera Y FOV:", camera_y_fov)

root = tk.Tk()
screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
root.destroy()

cv2.namedWindow("wallpaper", cv2.WINDOW_NORMAL)
cv2.setWindowProperty(
    "wallpaper",
    cv2.WND_PROP_FULLSCREEN,
    cv2.WINDOW_FULLSCREEN
)

cv2.namedWindow("tracking", cv2.WINDOW_NORMAL)
cv2.resizeWindow("tracking", 640, 480)

smooth_x_angle = 0.0
smooth_y_angle = 0.0

def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))

def angle_to_index(angle, angle_min, angle_max, steps):
    angle = clamp(angle, angle_min, angle_max)
    normalized = (angle - angle_min) / (angle_max - angle_min)
    index = round(normalized * (steps - 1))
    return int(clamp(index, 0, steps - 1))

def get_image_index(x_index, y_index):
    if reverse_x:
        x_index = (x_steps - 1) - x_index

    if reverse_y:
        y_index = (y_steps - 1) - y_index

    return y_index * x_steps + x_index

while True:
    ret, cam_f = cap.read()

    if not ret:
        print("Failed to read from webcam")
        break

    fh, fw = cam_f.shape[:2]

    gray = cv2.cvtColor(cam_f, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5
    )

    if len(faces) > 0:
        x, y, w, h = max(faces, key=lambda face: face[2] * face[3])

        face_center_x = x + w // 2
        face_center_y = y + h // 2

        x_offset_normalized = (face_center_x - (fw / 2)) / (fw / 2)
        y_offset_normalized = (face_center_y - (fh / 2)) / (fh / 2)

        x_offset_cm = x_offset_normalized * (camera_x_range_cm / 2)
        y_offset_cm = y_offset_normalized * (camera_y_range_cm / 2)

        raw_x_angle = math.degrees(
            math.atan(x_offset_cm / distance_from_camera_cm)
        )

        raw_y_angle = -math.degrees(
            math.atan(y_offset_cm / distance_from_camera_cm)
        )

        smooth_x_angle = (1 - smooth_strength) * smooth_x_angle + smooth_strength * raw_x_angle
        smooth_y_angle = (1 - smooth_strength) * smooth_y_angle + smooth_strength * raw_y_angle

        cv2.rectangle(cam_f, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.circle(cam_f, (face_center_x, face_center_y), 5, (0, 255, 255), -1)

    x_index = angle_to_index(
        smooth_x_angle,
        rendered_x_fov_min,
        rendered_x_fov_max,
        x_steps
    )

    y_index = angle_to_index(
        smooth_y_angle,
        rendered_y_fov_min,
        rendered_y_fov_max,
        y_steps
    )

    image_index = get_image_index(x_index, y_index)

    img = images[image_index]
    display_img = cv2.resize(img, (screen_w, screen_h))

    cv2.line(cam_f, (fw // 2, 0), (fw // 2, fh), (255, 0, 0), 2)
    cv2.line(cam_f, (0, fh // 2), (fw, fh // 2), (255, 0, 0), 2)

    cv2.putText(
        cam_f,
        f"x angle: {smooth_x_angle:.2f} deg | y angle: {smooth_y_angle:.2f} deg",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )

    cv2.putText(
        cam_f,
        f"x index: {x_index + 1}/{x_steps} | y index: {y_index + 1}/{y_steps}",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )

    cv2.putText(
        cam_f,
        f"image: {image_index + 1:04d}/{num_images:04d}",
        (20, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )

    if len(faces) == 0:
        cv2.putText(
            cam_f,
            "No face detected",
            (20, 145),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2
        )

    cv2.imshow("wallpaper", display_img)
    cv2.imshow("tracking", cam_f)

    k = cv2.waitKey(30) & 0xff

    if k == 27:
        break

cap.release()
cv2.destroyAllWindows()