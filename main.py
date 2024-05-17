import socketio
import cv2
import pickle
import cvzone
import numpy as np
import base64
import threading

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
def encode_frame(frame, quality=20):
    # Set the JPEG compression quality
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    
    ret, buffer = cv2.imencode('.jpg', frame, encode_param)
    if ret:
        return base64.b64encode(buffer).decode('utf-8')
    return None

# Function to process and send data asynchronously
def process_and_send_data():
    cap = cv2.VideoCapture('C:\\Users\\ELH\\Desktop\\python pfa\\OPTIPARK\\tcarPark.mp4')
    with open('C:\\Users\\ELH\\Desktop\\python pfa\\OPTIPARK\\CarParkPos', 'rb') as f:
        posList = pickle.load(f)
    width, height = 107, 48

    while cap.isOpened():
        ret, img = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

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
            color = (0, 255, 0) if count < 900 else (0, 0, 255)
            thickness = 2
            img = cv2.rectangle(img, (x, y), (x + width, y + height), color, thickness)
            spaceCounter += (count < 900)

        cvzone.putTextRect(img, f'Free: {spaceCounter}/{len(posList)}', (100, 50), scale=3,
                           thickness=5, offset=20, colorR=(0, 200, 0))

        encoded_frame = encode_frame(img)
        if encoded_frame:
            parkingData = {
                'free_spaces': spaceCounter,
                'total_spaces': len(posList),
                'encoded_frame': encoded_frame
            }
            sio.emit('parkingData', parkingData)

    cap.release()

# Function to run the Socket.IO connection in a separate thread
def run_socketio():
    try:
        sio.connect('http://localhost:3000')
        sio.wait()
    except Exception as e:
        print("An error occurred:", e)

if __name__ == "__main__":
    # Start the Socket.IO connection in a separate thread
    socketio_thread = threading.Thread(target=run_socketio)
    socketio_thread.start()

    # Start processing and sending data
    process_and_send_data()

    # Ensure the main thread waits for the socket.io thread to finish
    socketio_thread.join()
    sio.disconnect()
    print("Cleaned up resources")
