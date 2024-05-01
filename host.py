import socket
import pandas as pd
import os
import threading
import shutil

connected_clients = []
connected_clients_dict = {}
connected_users_dict = {}



SIZE = 1024 
FILE_SIZE_BYTE = 50000                                         
BYTEORDER_LENGTH = 8
FORMAT = "utf-8"
RECOGNIZER_PATH = "templates/imagerecognizer"

def copy2node(client):
    client.send('SETUP_FILE_TRANSFER'.encode())
    # msg = client.recv(SIZE).decode()                          
    # print('[*] server:', msg)
    shutil.make_archive("imagerecognizer", 'zip', RECOGNIZER_PATH)

    file_size = os.path.getsize('imagerecognizer.zip')
    print("File Size is :", file_size/1024/1024, "MBytes")
    file_size_in_bytes = file_size.to_bytes(BYTEORDER_LENGTH, 'big')
    
    print("Sending the file size")
    client.send(file_size_in_bytes)
    msg = client.recv(SIZE).decode(FORMAT)                    
    print(f"[SERVER]: {msg}")
    
    print("Sending the file name")
    client.send("imagerecognizer.zip".encode(FORMAT))           
    msg = client.recv(SIZE).decode(FORMAT)                    
    print(f"[SERVER]: {msg}")  
    
    print("Sending the file data")    
    with open ('imagerecognizer.zip','rb') as f1:
        client.send(f1.read())  
    msg = client.recv(FILE_SIZE_BYTE).decode(FORMAT)
    print(f"[SERVER]: {msg}")
    print('[SERVER]: Message received from client: ',client.recv(FILE_SIZE_BYTE).decode(FORMAT))
    

    os.remove('imagerecognizer.zip')

def send_file(client_socket, filename):
    print(f"[SEND] Sending the file size")
    file_size = os.path.getsize(filename)
    file_size_in_bytes = file_size.to_bytes(BYTEORDER_LENGTH, 'big')
    client_socket.send(file_size_in_bytes)
    print("File size sent:", file_size, " bytes")

    print(f"[SEND] Sending the file data")
    with open(filename, 'rb') as f:
        packet = f.read(FILE_SIZE_BYTE)
        while packet:
            client_socket.send(packet)
            packet = f.read(FILE_SIZE_BYTE)
    print(f"File data sent.")
    

def receive_file(server_socket, from_node = False):

    log_type = ''
    
    if from_node:
        log_type =  '[RECEIVE FROM NODE] '
        file_name = 'output.jpg'
        print(log_type+" Waiting for file size")
    else:
        file_name = 'Image.jpg'
        log_type = '[RECEIVE FROM USER] '
        print(log_type+ "Waiting for file size")

    
    file_size_bytes = server_socket.recv(BYTEORDER_LENGTH)
    file_size = int.from_bytes(file_size_bytes, 'big')
    print(log_type + "Received file size:", file_size, "bytes")


    print(log_type+"Receiving file data")
    
    with open(file_name, 'wb') as f:
        total_received = 0
        while total_received < file_size:
            data = server_socket.recv(FILE_SIZE_BYTE)
            total_received += len(data)
            f.write(data)
    print(log_type+"File received.")

        
def check_available_clients():
    try:
        connected_devices_df = pd.read_csv("host_status.csv")
    except FileNotFoundError:
        connected_devices_df = pd.DataFrame(columns=['IP Address', 'Status', 'Date Joined', 'Date Updated', 'Running'])
        connected_devices_df.to_csv("host_status.csv", index=False)

    #For other clients in dataframe that are not in connected_clients_dict set their status to unreachable and running to False
    for client in connected_devices_df['IP Address']:
        if client not in connected_clients_dict.keys():
            connected_devices_df.loc[connected_devices_df['IP Address'] == client, 'Status'] = 'unreachable'
            connected_devices_df.loc[connected_devices_df['IP Address'] == client, 'Date Updated'] = pd.Timestamp.now()
            connected_devices_df.loc[connected_devices_df['IP Address'] == client, 'Running'] = False
            connected_devices_df.to_csv("host_status.csv", index=False)

    #Check if connectec_clinet_dict is empty
    if not connected_clients_dict:
        return
    
    for client in list(connected_clients_dict.keys()):
        try:
            connected_clients_dict[client].send("ping".encode(FORMAT))
            response = connected_clients_dict[client].recv(1024).decode(FORMAT)
            if response == "pong":
                print(f"Client {client} is reachable.")
                connected_devices_df.loc[connected_devices_df['IP Address'] == client, 'Status'] = 'reachable'
                connected_devices_df.loc[connected_devices_df['IP Address'] == client, 'Date Updated'] = pd.Timestamp.now()
                connected_devices_df.loc[connected_devices_df['IP Address'] == client, 'Running'] = True
                connected_devices_df.to_csv("host_status.csv", index=False)

        except ConnectionRefusedError:
            print(f"Client {client} is unreachable.")
            connected_devices_df.loc[connected_devices_df['IP Address'] == client, 'Status'] = 'unreachable'
            connected_devices_df.loc[connected_devices_df['IP Address'] == client, 'Date Updated'] = pd.Timestamp.now()
            connected_devices_df.loc[connected_devices_df['IP Address'] == client, 'Running'] = False
            connected_devices_df.to_csv("host_status.csv", index=False)
            connected_clients_dict.pop(client)

        except BrokenPipeError:
            print(f"Client {client} disconnected.")
            connected_clients_dict.pop(client)
            continue

        except Exception as e:
            print(f"An error occurred in check_available_clients(): {e}")
            connected_clients_dict.pop(client)
            continue
       
def handle_user(conn, addr):
    
    if len(connected_clients_dict) == 0:
       print("No clients available to process the request.")
       message_type = "NO_CLIENTS"
       conn.send(message_type.encode(FORMAT))
       conn.send("No clients available to process the request.".encode(FORMAT))
       return
    
    if len(connected_clients_dict) > 0:

        for client in connected_clients_dict.keys():
            connected_clients_dict[client].send("SENT_AVAILABILTY_STATUS".encode(FORMAT))
            response =  connected_clients_dict[client].recv(1024).decode(FORMAT)

            if response == "BUSY":
                print(f"Client {client} is busy.")
                continue

            elif response == "NOT_BUSY":
                #Get Image from user
                conn.send("SEND_IMAGE".encode(FORMAT))
                # connected_clients_dict[client].send('START_IMAGE_RECOGNITION'.encode(FORMAT))   
                receive_file(conn)
                connected_clients_dict[client].send('START_IMAGE_RECOGNITION'.encode(FORMAT))
                send_file(connected_clients_dict[client], 'Image.jpg')

                os.remove('Image.jpg')
                
                code_status = connected_clients_dict[client].recv(1024).decode(FORMAT)
                
                if code_status == "EXECUTION_SUCCESS" :

                    print('[MASTER]: Image Recognition Completed Successfully')
                    receive_file(connected_clients_dict[client], from_node=True)
                    print('[MASTER]: Image Received from',{client})

                #Send image to user
                    conn.send('EXECUTION_SUCCESS'.encode(FORMAT))
                    send_file(conn, 'output.jpg')
                #Call recieve function 
                    #Send 
                elif code_status == "EXECUTION_FAILURE":
                    print('[MASTER]: Image Recognition Failed')

                    # Send message to user 
                    conn.send('EXECUTION_FAILURE'.encode(FORMAT))

                    


def host():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    port = 12345
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(10)
    print("Host is ready to receive connections...")

    def send_shutdown_message(client_socket):
        client_socket.send("SHUTDOWN".encode(FORMAT))
        client_socket.close()

    try:
        while True:
            check_available_clients()
            if connected_clients_dict:
                print("====================================================")
                print("Connected clients:")
                for i in connected_clients_dict.keys():
                    print(i)
                print("====================================================")
            print("Press Ctrl+C to stop the server...")

            # Accept connections from clients
            conn, addr = server_socket.accept()
            user_type = conn.recv(50).decode(FORMAT)
            
            if user_type == "USER":
                print(f"[SERVER]: User connected from {addr}")
                connected_users_dict[addr[0]] = conn
                
                user_thread = threading.Thread(target=handle_user, args=(conn, addr))
                user_thread.start()
                print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
    
            elif user_type == "CLIENT":
                print(f"[SERVER]: Client connected from {addr}")
                connected_clients_dict[addr[0]] = conn
                try:
                    hosts_df = pd.read_csv("host_status.csv")
                    #Change this logic 
                    if addr[0] not in hosts_df['IP Address'].values:
                        hosts_df.loc[len(hosts_df)] = [addr[0], 'reachable', pd.Timestamp.now(), pd.Timestamp.now(), False]
                        print('[SERVER]: New device connected.....')
                        copy2node(conn)
                        check_available_clients()
                    elif addr[0] in hosts_df['IP Address'].values:
                        print(f'[SERVER]: Registered Device Conneted. IP Address: {addr[0]}')

                except BrokenPipeError:
                    print(f"Client {addr} disconnected.")
                    connected_clients_dict.pop(addr[0])
                    conn.close()
                    continue
                except FileNotFoundError:
                    hosts_df = pd.DataFrame({'IP Address': [addr[0]], 'Status': ['reachable'], 'Date Joined': [pd.Timestamp.now()],'Date Updated': [pd.Timestamp.now()], 'Running': [False]})
                finally:
                    hosts_df.to_csv("host_status.csv", index=False)
    except KeyboardInterrupt:
        print("KeyboardInterrupt: Stopping the host server...")

    finally:
        for client in connected_clients_dict.values():
            send_shutdown_message(client)
        for client in connected_clients_dict.values():
            client.close()
        server_socket.close()
    

if __name__ == "__main__":
    host()
