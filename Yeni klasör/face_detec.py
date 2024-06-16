import cv2
from ultralytics import YOLO
import face_recognition
import numpy as np
import os
from datetime import datetime
import random
from queue import Queue

def load_known_faces():

    known_face_encodings = []
    known_face_names = []
    
    known_faces_dir = 'known_faces'
    for filename in os.listdir(known_faces_dir):
        if filename.endswith(('.jpg', '.jpeg', '.png')):
            image_path = os.path.join(known_faces_dir, filename)
            image = face_recognition.load_image_file(image_path)
            
            # Yüzlerin olup olmadığını kontrol et
            face_encodings = face_recognition.face_encodings(image)
            if face_encodings:
                known_face_encodings.append(face_encodings[0])
                
                # Dosya ismini yüz adı olarak kullanma (dosya uzantısını kaldırarak)
                name = os.path.splitext(filename)[0]
                known_face_names.append(name)
    return known_face_encodings, known_face_names

def process_video_stream(known_face_encodings, known_face_names, result_queue):
    detected_faces_dir = "detected"

    model = YOLO('yolov8n.pt') 

    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)

        for result in results:
            for box in result.boxes:
                if int(box.cls) == 0: 
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    person_frame = frame[y1:y2, x1:x2]

                    rgb_small_frame = np.ascontiguousarray(frame[:, :, ::-1])

                    face_locations = face_recognition.face_locations(rgb_small_frame)

                    if face_locations is not None and face_locations:
                        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                        face_names = []
                        for face_encoding in face_encodings:
                
                            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                            name = "Unknown"

                        
                            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                            best_match_index = np.argmin(face_distances)
                            if matches[best_match_index]:
                                name = known_face_names[best_match_index]

                            face_names.append(name)
                    
                        for (top, right, bottom, left), name in zip(face_locations, face_names):
                    
                    
                            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

                            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                            font = cv2.FONT_HERSHEY_DUPLEX
                            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

                            if name == "Unknown":
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                random_number = random.randint(1000, 9999)
                                detected_image_path = os.path.join(detected_faces_dir, f"unknown_{timestamp}_{random_number}.jpg")
                                cv2.imwrite(detected_image_path, person_frame)
                                print(f"Unknown face detected, saved frame to {detected_image_path}")
                                result_queue.put(detected_image_path)


                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    label = model.names[int(box.cls)]
                    confidence = box.conf[0]
                    cv2.putText(frame, f'{label} {confidence:.2f}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow('YOLOv8 Object Detection', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()