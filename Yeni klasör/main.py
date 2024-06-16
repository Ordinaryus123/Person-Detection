import face_detec
from queue import Queue
import socket
import threading
import smtplib
from email.mime.text import MIMEText
import time
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from datetime import datetime
import cv2
from deepface import DeepFace
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

FORMAT = 'utf-8'
HEADER = 2048
HOST = "192.168.1.106"
SOCKET_PORT = 5050
FLASK_PORT = 8080
DISCONNECT = "aaa"
id_counter = 1
messages = []
conn_dic = {}

app = Flask(__name__)
socketio = SocketIO(app)

EMAIL_ADDRESS = "emirsaygili1903@gmail.com"
EMAIL_PASSWORD = "sldi lsrm utzk cgdw"


class DetectedFolderHandler(FileSystemEventHandler):
    def __init__(self, queue):
        self.queue = queue

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(('.jpg', '.jpeg', '.png')):
            self.queue.put(event.src_path)


def start_face_yolo(result_queue):
    # Yüz tanıma verilerini yükle
    known_faces_dir = 'known_faces'
    known_face_encodings, known_face_names = face_detec.load_known_faces()

    # Video akışını işle
    face_detec.process_video_stream(known_face_encodings, known_face_names, result_queue)

def monitor_detected_folder(detected_dir, queue):
    event_handler = DetectedFolderHandler(queue)
    observer = Observer()
    observer.schedule(event_handler, detected_dir, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
def the_end():
    detected_dir = 'detected'
    result_queue = Queue()
    # Yüz tanıma ve YOLO işlemlerini bir thread'de başlat
    face_yolo_thread = threading.Thread(target=start_face_yolo, args=(result_queue,))
    face_yolo_thread.start()

    detected_folder_thread = threading.Thread(target=monitor_detected_folder, args=(detected_dir, result_queue))
    detected_folder_thread.start()


    while True:
        if not result_queue.empty():
            new_file = result_queue.get()
            send_detection_message(new_file,"Unknown")
            send_email("Stranger Person Detected", "There is a stranger person detected.")
            
        
        # Burada ana programınızın diğer işlemlerini ekleyebilirsiniz
        time.sleep(1)

def send_email(subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = "selinaelif.esit@bahcesehir.edu.tr"

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, "selinaelif.esit@bahcesehir.edu.tr", msg.as_string())
        server.quit()
    except Exception as e:
        print("An error occurred while sending email:", e)

@app.route('/')
def index():
    return render_template('nice_tablo.html', messages=messages)

@app.route('/messages', methods=['GET'])
def get_messages():
    return jsonify(messages)

@app.route('/send_message', methods=['POST'])
def send_message():
    message = request.form['message']
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, SOCKET_PORT))
            s.sendall(f"WebClient: {message}".encode(FORMAT))
            messages.append(f"WebClient: {message}")
    except Exception as e:
        return str(e)
    return 'Message sent!'

def send_detection_message(name, surname):
    message = f"send_to {name} {surname}"
    for client_id, client_socket in conn_dic.items():
        try:
            client_socket.send(message.encode(FORMAT))
        except Exception as e:
            print(f"Failed to send message to client {client_id}: {e}")
    socketio.emit('update_table', {'isim': name, 'soyisim': surname})

      

def handle_client(client_socket, client_address):
    global id_counter, conn_dic
    client_id = id_counter
    id_counter += 1
    conn_dic[client_id] = client_socket
    while True:
        try:
            message = client_socket.recv(HEADER).decode(FORMAT)
            if not message:
                break
            print(f"Received message from {client_address}: {message}")

            if message == "get_id":
                client_socket.send(str(client_id).encode(FORMAT))
                print(f"New client came : {client_id}")

            elif message.startswith("send_to"):
                messages.append(message)
                parts = message.split()
                dest_id = int(parts[1])
                dest_message = " ".join(parts[2:])
                if dest_id in conn_dic:
                    conn_dic[dest_id].send(dest_message.encode(FORMAT))
                else:
                    print("Invalid client ID:", dest_id)

        except Exception as e:
            print(f"An error occurred while handling client {client_address}: {e}")
            break

    client_socket.close()
    del conn_dic[client_id]

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, SOCKET_PORT))
    server_socket.listen()
    print(f"[*] Server listening on {HOST}:{SOCKET_PORT}")
    while True:
        client_socket, client_address = server_socket.accept()
        print(f"[+] {client_address} connected.")
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()

@app.route('/receive_message', methods=['POST'])
def receive_message():
    message = request.form['message']
    parts = message.split()
    if len(parts) >= 2 and parts[0] == "send_to":
        name = " ".join(parts[2:])
        socketio.emit('set_names', {'isim': parts[2], 'soyisim': parts[3]})
        return 'Message received and table updated!'
    return 'Invalid message format!'

@socketio.on('connect') #client bağlandığında çalışır
def handle_connect():
    print('Client connected')

@socketio.on('disconnect') #client bağlantısı kesildiğinde çalışır
def handle_disconnect():
    print('Client disconnected')

@socketio.on('server_message')  #sunucudan gelen mesajları işler
def handle_server_message(data):
    print('Alarm kapatma isteği alındı:', data)

@socketio.on('server_message')
def handle_message(message):
    print('Received message from client:', message)
    print(f"İsim: {message['isim']}, Soyisim: {message['soyisim']}")
    dest_id = 1
    dest_message = f"send_to {dest_id} {message['isim']} {message['soyisim']}"
    if dest_id in conn_dic:
        conn_dic[dest_id].send(dest_message.encode(FORMAT))
    else:
        print("Invalid client ID:", dest_id)
    emit('update_table', message)

def start_flask():
    socketio.run(app, host=HOST, port=FLASK_PORT, debug=True)

if __name__ == "__main__":
    print("Starting server...")
    server_thread = threading.Thread(target=start_server)
    server_thread.start()
    print("Starting Flask app...")
    thread_the_end=threading.Thread(target=the_end)
    thread_the_end.start()
    start_flask()
    