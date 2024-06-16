import threading
import face_detec
from queue import Queue
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time


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

if __name__ == "__main__":
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
            print(f"New detected file: {new_file}")
        
        # Burada ana programınızın diğer işlemlerini ekleyebilirsiniz
        time.sleep(1)