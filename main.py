import socketio
import cv2
import pickle
import numpy as np
import base64
import time

# Create a Socket.IO client instance
sio = socketio.Client()

# Event for successful connection
@sio.event
def connect():
    print("Connection established")

# Event for disconnection
@sio.event
def disconnect():
    print("Disconnected from server")

# Modified event for connection failure to accept an argument
@sio.event
def connect_error(data):
    print("The connection failed!", data)

# Function to encode video frames in Base64
def encode_frame(frame):
    ret, buffer = cv2.imencode('.jpg', frame)
    if ret:
        return base64.b64encode(buffer).decode('utf-8')
    return None

# Function to handle video processing and data sending
def process_and_send_data():
    cap = cv2.VideoCapture('C:\\Users\\ELH\\Desktop\\python pfa\\OPTIPARK\\carPark.mp4')
    with open('C:\\Users\\ELH\\Desktop\\python pfa\\OPTIPARK\\CarParkPos', 'rb') as f:
        posList = pickle.load(f)
    width, height = 107, 48

    while cap.isOpened():
        ret, img = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        # Resize the frame to reduce its size
        img = cv2.resize(img, (640, 480))

        imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        imgBlur = cv2.GaussianBlur(imgGray, (3, 3), 1)
        imgThreshold = cv2.adaptiveThreshold(imgBlur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                             cv2.THRESH_BINARY_INV, 25, 16)
        imgMedian = cv2.medianBlur(imgThreshold, 5)
        kernel = np.ones((3, 3), np.uint8)
        imgDilate = cv2.dilate(imgMedian, kernel, iterations=1)


        spaceCounter = 0
        for pos in posList:
            x, y = pos
            imgCrop = imgDilate[y:y + height, x:x + width]
            count = cv2.countNonZero(imgCrop)
            spaceCounter += (count < 900)

        encoded_frame = encode_frame(img)
        if encoded_frame:
            parkingData = {
                'free_spaces': spaceCounter,
                'total_spaces': len(posList),
                'encoded_frame': encoded_frame
            }
            sio.emit('parkingData', parkingData)
            # time.sleep(0.0001)  # Control the frame rate

    cap.release()

if __name__ == "__main__":
    try:
        sio.connect('http://localhost:3000')
        process_and_send_data()
    except Exception as e:
        print("An error occurred:", e)
    finally:
        sio.disconnect()
        print("Cleaned up resources")
