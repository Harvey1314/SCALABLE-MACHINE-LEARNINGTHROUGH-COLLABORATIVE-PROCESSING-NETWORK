__package__
import cv2 as cv
import numpy as np
import pathlib as Path
import pickle 
import configparser

config = configparser.RawConfigParser()
config.read('properties.properties')

dictionary_labels = config.get('FILES_PATH', 'label_dictionary')
labels_export_filepath = config.get('FILES_PATH', 'labels_serialized_export')
trained_dataset = config.get('FILES_PATH', 'trained_data_serialized_export')
trained_recogniser_exportpath  = config.get('FILES_PATH', 'trained_recognizer_export')

# Load the face cascade classifier for facial recognization
face_cascade = cv.CascadeClassifier(cv.data.haarcascades + "haarcascade_frontalface_default.xml")
#Images dataset path

# To store the training data and labels
training_data = []

#Dictiornay of elemens which has person:unique integer as  key:value pairs 
dict_labels = {}

labels = []
#This is varibale is used as an counter to increment and use this value to unique integer for dict_labels variable when ever we are training a new person. 
current_label_count = 0

def detect_faces(img):
    """Using opencv methods this method will convert image passed to this function into grayscale image and then using harcaas
    cascades face recognizer it will extract all the faces from the image and return the image"""
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor = 1.1, minNeighbors = 9)
    return faces, gray


def train_dataset_images(dataset_path, model_export_path):
    # To store the training data and labels
    training_data = []

    #Dictiornay of elemens which has person:unique integer as  key:value pairs 
    dict_labels = {}
    #**** To pass to train method
    labels = []
    #This is varibale is used as an counter to increment and use this value to unique integer for dict_labels variable when ever we are training a new person. 
    current_label_count = 0
    face_recognizer = cv.face.LBPHFaceRecognizer_create()
    for file_path in dataset_path.glob("**/*.jpg"):
        # Load the image and detect faces
        img = cv.imread(str(file_path))
        faces, gray = detect_faces(img)

        # Add each face to the training data array with its corresponding label
        for (x, y, w, h) in faces:
            training_data.append(gray[y:y+h, x:x+w])
            label = str(file_path.parent.name).replace('_', ' ').title()
            if label not in dict_labels:
                dict_labels[label] = current_label_count
                current_label_count += 1
            labels.append(dict_labels[label])
    face_recognizer.train(training_data, np.array(labels))
    face_recognizer.save(model_export_path)
    
    #print("Labesl in TM", labels)
   
    with open(labels_export_filepath, 'wb') as ll:
        pickle.dump(labels, ll)
    with open(trained_dataset, 'wb') as tds:
        pickle.dump(training_data, tds)
    with open(dictionary_labels, 'wb') as sl:
        pickle.dump(dict_labels, sl)

    print("Face Recognizer Model Exported")
    return face_recognizer



