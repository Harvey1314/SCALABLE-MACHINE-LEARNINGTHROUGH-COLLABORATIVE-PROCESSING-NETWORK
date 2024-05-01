import socket
import os
import zipfile
import os

try:
    import psutil
except ImportError:
    os.system("pip3 install psutil")
    import psutil

FORMAT = "utf-8"                                     
SIZE = 1024
BYTEORDER_LENGTH = 8
FILE_SIZE_BYTE = 50000
PORT = 0

def display_menu():
    print("1. Join as Node")
    print("2. Join as User")
    print("3. Exit")

def server_details():

    while True:
        try:
            #Chage this user input
            port = int(input("Enter the port number of the server: "))
            # port = 12345
            if port > 0 and port <= 65535:
                return host, port
            else:
                print("Invalid port number. Please enter a number between 1 and 65535.")
        except ValueError:
            print("Invalid input. Please enter a valid port number.")


def receive_setup_file(client_socket):

    print(f"[RECV] Receiving the file size")
    file_size_in_bytes = client_socket.recv(BYTEORDER_LENGTH)
    file_size= int.from_bytes(file_size_in_bytes, 'big')
    print("File size received:", file_size, " bytes")
    client_socket.send("File size received on client node.".encode(FORMAT))

    print(f"[RECV] Receiving the filename.")
    filename = client_socket.recv(SIZE).decode(FORMAT)
    print(f"[RECV] Filename Received:", filename)
    client_socket.send("Filename Received .".encode(FORMAT))

    print(f"[RECV] Receiving the file data.")
    packet = b""

    while len(packet) < file_size:
        if(file_size - len(packet)) > FILE_SIZE_BYTE:
            buffer = client_socket.recv(FILE_SIZE_BYTE)
        else:
            buffer = client_socket.recv(file_size - len(packet))

        if not buffer:
            raise Exception("Incomplete file received")
        packet += buffer

    with open(filename, 'wb') as f:
        f.write(packet)
            
    print(f"[RECV] File data received.")
    client_socket.send("File data received".encode(FORMAT))


    with zipfile.ZipFile(filename, 'r') as zip_ref:
        zip_ref.extractall("imagerecognizer")
    os.remove(filename)

    print(f"Setup files unzipped successfully.")

    print("Installing Required Packages")
    
    os.system("pip3 install -r imagerecognizer/requirements.txt")
    print("\n\n")
    print("====================================================")
    print("Packages Installed Successfully.")
    client_socket.send("INSTALLATION_SUCCESSFUL".encode(FORMAT))
    print("[NODE] Waiting for further commands from the MASTER node.")
    print("====================================================")
    return

def send_file(client_socket, filename):
    print(f"[SEND] Sending the file size")
    file_size = os.path.getsize(filename)
    file_size_in_bytes = file_size.to_bytes(BYTEORDER_LENGTH, 'big')
    try:
        client_socket.send(file_size_in_bytes)
        print("File size sent:", file_size, " bytes")
    
        print(f"[SEND] Sending the file data")
        with open(filename, 'rb') as f:
            packet = f.read(FILE_SIZE_BYTE)
            while packet:
                client_socket.send(packet)
                packet = f.read(FILE_SIZE_BYTE)
        print(f"File data sent.")
    except BrokenPipeError as e:
        print("BrokenPipeError in send_file():", e)
        client_socket.close()
        exit()
    except Exception as e:
        print("An error occurred in send_file():", e)
        client_socket.close()
        exit()

def receive_file(server_socket, from_master = False):

    if from_master:
        file_name = r'output_user.jpg'
    else:
        file_name = r'imagerecognizer/input.jpg'

    print("[RECEIVE] Waiting for file size")
    file_size_bytes = server_socket.recv(BYTEORDER_LENGTH)
    file_size = int.from_bytes(file_size_bytes, 'big')
    print("Received file size:", file_size, "bytes")


    #Move the file to imagerecognizer folder
    print("[RECEIVE] Receiving file data")
    with open(file_name , 'wb') as f:
        total_received = 0
        while total_received < file_size:
            data = server_socket.recv(FILE_SIZE_BYTE)
            total_received += len(data)
            f.write(data)
    print("[RECEIVE] File received.")

    #Move the image to imagerecognizer folder
    # os.system("mv input.jpg imagerecognizer")

    


def client(client_socket):  
    client_socket.send('CLIENT'.encode(FORMAT))
    image = None
    while True:
        
        try:
            # client_socket.send('copy trash'.encode())
            command = client_socket.recv(50).decode(FORMAT)
            if len(command) > 0:
                print("[CLIENT] Command Received:", command)

            if command == "SETUP_FILE_TRANSFER":
                receive_setup_file(client_socket)

            if command == "ping":
                print("[PING] Received ping from server. Sending pong to server.")
                client_socket.send("pong".encode(FORMAT))
                
            if command == "SENT_AVAILABILTY_STATUS":
                for process in psutil.process_iter(['name']):
                    if 'ImageRecognizer' in process.info['name']:
                        client_socket.send("BUSY".encode(FORMAT))
                client_socket.send("NOT_BUSY".encode(FORMAT))
                print("[AVAILABILITY_STATUS] Sent availability status to server.")
           
            if command == "START_IMAGE_RECOGNITION":
                print("[NODE] Received command to start image recognition.")
                receive_file(client_socket)
                print("[RECEIVE & EXECUTE] Image received successfully.")

                print("[RECEIVE & EXECUTE] Executing Image Recognizer...")
                #Change the directory to imagerecognizer
                os.chdir("imagerecognizer")
                # os.chdir("../imagerecognizer")
                
                print("[RECEIVE & EXECUTE] Current working directory set to:", os.getcwd())

                #Pass image as argument to Image Recognizer
                image = "input.jpg"
                print("[Image] ",image)
                result = os.system("python3 driver.py " + image)

                if result != 0:
                    print("[RECEIVE & EXECUTE] An error occurred while executing the Image Recognizer. Please try again.")
                    client_socket.send("EXECUTION_FAILURE".encode(FORMAT))
                else:
                    print("[RECEIVE & EXECUTE] Execution complete.")
                    client_socket.send("EXECUTION_SUCCESS".encode(FORMAT))

                # Send back to Master Server
                send_file(client_socket, r"output.jpg")
                os.chdir("..")
                

            if command == "SHUTDOWN":
                print("[CLIENT] Server is shutting down")
                exit()
        except ConnectionRefusedError:
            print("Connection refused. Make sure the server is running and reachable.")
        except KeyboardInterrupt:
            print("\nCtrl+C KeyboardInterrupt. Exiting.")
            client_socket.close()
            exit()
        except Exception as e:
            client_socket.send("ERROR".encode(FORMAT))
            print("An error occurred in client() :", e)
            client_socket.close()
            exit()

def user(user_socket):
        #Get Image path from user
        user_socket.send('USER'.encode(FORMAT))
        response = user_socket.recv(1024).decode(FORMAT)
        if response == "NO_CLIENTS":
            print("No clients available for image recognition. Please try again later.")
            user_socket.close()
            exit()

        if response == "SEND_IMAGE":
            print("====================================================")
            print("[USER] Sending Image to Master Node")
           

            image_path = input("Enter the path of the image you want to recognize:")
            image_path = r'%s' % image_path

            
            send_file(user_socket, image_path)

            print("[USER] Image sent successfully.")      

            print("[USER] Waiting for response from server...")

            response = user_socket.recv(SIZE).decode(FORMAT)
            print(response +" received after waiting for response from server.")

            if response == 'EXECUTION_FAILURE':
                print("[USER] An error occurred while recognizing the image. Please try again.")
                user_socket.close()
                exit()  

            if response == 'EXECUTION_SUCCESS':

                print("[USER] Image recognized successfully.")
                receive_file(user_socket, from_master=True)
                
            os.system("open output_user.jpg")
            exit()

            if response == 'SHUTDOWN':
                print("[USER] Master rerver is Shutting down")
                exit()
    
        if response == "EXECUTION_SUCCESS":

            print("Image recognized successfully.")
            #Should receive the recognized image from the server
            receive_file(user_socket)
            #Open the recognized image
            os.system("open output.jpg")

            #on successful recognition, ask user if they want to recognize another image
            print("Do you want to recognize another image? (Y/N)")
            choice = input()
            if choice == "Y" or choice == "y":
                user(user_socket)
            else:
                print("Exiting...")
                user_socket.close()
                exit()
        
        else:
            print("An error occurred while recognizing the image. Please try again.")

if __name__ == "__main__":
    host, port = server_details()
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, port))
    except ConnectionRefusedError:
        print("Connection refused. Make sure the server is running and reachable.")
        exit()
    except Exception as e:
        print("An error occurred in main():", e)
        exit()
    
    print("====================================================")
    print("Connected to the server.")
    print("Press Ctrl+C to close connection with server...")
    print("====================================================")

    display_menu()
    
    print()
    choice = input("Enter your choice: ")
    if choice == "1":
        client(client_socket)
    elif choice == "2":
        user(client_socket)
    elif choice == "3":
        print("Exiting...")
        client_socket.close()
        exit()
    else:
        print("Invalid choice. Please select between 1 and 3.")

        
   

    

