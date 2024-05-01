__package__
import cv2 as cv
from train_model import detect_faces
import pickle
import numpy as np
import configparser

config = configparser.RawConfigParser()
config.read('properties.properties')

dictionary_labels = config.get('FILES_PATH', 'label_dictionary')
labels_filepath = config.get('FILES_PATH', 'labels_serialized_export')
trained_dataset = config.get('FILES_PATH', 'trained_data_serialized_export')
trained_recogniser_exportpath  = config.get('FILES_PATH', 'trained_recognizer_export')


def predict_person(face_recognizer, image_path):
    user_input_flag = False
    unknown_faces = 0
    total_faces = 0
    
    #Deserialize dictionary having int:person name mapping
    dict_labels = {}
    with open(dictionary_labels, 'rb') as f:
        dict_labels = pickle.load(f)
    
    #Deserialize labels of trained model
    labels = []
    with open(labels_filepath, 'rb') as f:
        labels = pickle.load(f)

    #Deserialize trained data
    training_data = []
    with open(trained_dataset, 'rb') as f:
        training_data = pickle.load(f)
    
    img = cv.imread(image_path)
    
    #Detect all faces in the input image 
    faces, gray = detect_faces(img)
    total_faces = len(faces)
    for (x, y, w, h) in faces:
        # Crop the face region from the image
        face_roi = gray[y:y+h, x:x+w]

        # Predict the label of the face using the trained model
        label, loss = face_recognizer.predict(face_roi)

        #Get the person name using label from dict_labels dictionary
        for key, value in dict_labels.items():
            if value == label:
                label = key
                break

        print("Confidence for "+label +" : "+ str(100 - loss))

        # If confidence of predicted face is > 75% draw a rectangle around the face and display the predicted label and loss
        if loss < 25:
            cv.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv.putText(img, f'{label} ({100-loss:.2f}%)', (x, y-10), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)    
            
        elif loss > 25:
            cv.rectangle(img, (x, y), (x+w, y+h), (0, 0, 255), 2)
            cv.putText(img, f'Unknown Person', (x, y-10), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        #Save the image with identified faces
        cv.imwrite('output.jpg', img)
        
    #     else:
    #         unknown_faces +=1
    #         #Copy image to highlight person for labelling
    #         dup_img = img.copy()
    #         #Draw rectangle around the unknown face and wait for user input
    #         cv.rectangle(dup_img, (x, y), (x+w, y+h), (0, 0, 255), 2)
    #         cv.imshow('Unknown Person', dup_img)
    #         cv.waitKey(0)

    #         choice = input('Do you wish to label unknown person in image?(Y/N) :' )
    #         cv.destroyWindow('Unknown Person')
    #         if (choice == 'Y' or choice == 'y'):
    #             print(list(dict_labels.keys()))
    #             valid_name = True
    #             name = input("Label highlighted person in image (Hint: May use list displayed above): ")
    #             while valid_name:
    #                 if(len(name) < 1):
    #                     print("Please enter valid name : ")
    #                 else:
    #                     valid_name = False
    #             training_data.append(gray[y:y+h, x:x+w])
    #             labels_in_dict = list(dict_labels.keys())
                
    #             if len(labels_in_dict) == 0:
    #                 new_label = 0
    #                 dict_labels[name] = new_label
    #             else:
    #                 new_label = len(labels_in_dict)+1
    #                 labels.append(new_label)
    #                 dict_labels[name] = new_label
               
    #             user_input_flag = True
    #         else:
    #             print("Invalid input. skipping labeling the person...")
    #             cv.destroyWindow('Unknown Person')
    #             continue
    #     # Save the updated model and labels dictionary
    
    # #Train and save model only if user has trained 
    # if(user_input_flag):
    #     face_recognizer.train(training_data, np.array(labels))
    #     print("Training Model again with identified person...")
        
    #     face_recognizer.save(trained_recogniser_exportpath)
    #     print("Model Serialized and Imported...")
        
    #     with open(dictionary_labels, 'wb') as f:
    #         pickle.dump(dict_labels, f)  
    
    # # Display the final image with the identified faces and labels, displays only if there are identified faces
    # if( total_faces!= unknown_faces):
    #     cv.imshow('Identified People', img)
    #     cv.waitKey(0)
    #     cv.destroyAllWindows()
    # else:
    #     print('Model Saved.')


