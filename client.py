import socket
import concurrent.futures
import sys
import os

MAXBUF = 8192
current_Directory = os.path.dirname(os.path.realpath(__file__))
#http://web.stanford.edu/class/cs231a/project.html

#functions
def get_domain_name(link_name):
    if("http://" in link_name):
        domain_name = link_name[7:].split("/")[0] 
    else:
        domain_name = link_name.split("/")[0] 
    return domain_name

def get_file_ending(link_name):
    file_ending = ""
    if("http://" in link_name):
        i = -1
        while(file_ending == ""):
            file_ending =  link_name[7:].split("/")[i]
            i-=1
    else:
        i = -1
        while(file_ending == ""):
            file_ending =  link_name.split("/")[i]
            i-=1
    if(file_ending == get_domain_name(link_name)):
        return "index.html"
    return file_ending

def output_file_name(link_name):
    domain = get_domain_name(link_name)
    file_end = get_file_ending(link_name)
    return domain +  "_" + file_end

def get_link_to_file(link_name):
    domain = get_domain_name(link_name)
    link_to_file = link_name[link_name.find(domain) +len(domain):]
    if(link_to_file == '/' or link_to_file == ""):
        return "/index.html"
    return link_to_file

def receiveHeader(s):
    data = b""
    while data[-4:] != b"\r\n\r\n":
        data += s.recv(1)
    return data


#content_length
def find_content_length(data):
    data_decoded = data.split(b"\r\n\r\n")[0].decode()
    index = data_decoded.find("Content-Length: ")
    contentLength = data_decoded[index + 16:]
    contentLength = contentLength.split("\r\n")[0]
    contentLength = int(contentLength)
    return contentLength


#chunked_encoding
def empty_chunk(data):
    if data == b"0\r\n" or data == b"\r\n":
        return True
    return False

def get_chunk_size(s:socket.socket):
    #size = b''
    #while b"\r\n" not in size:
    #    size += s.recv(1)
    #size = size[:size.find(b"\r\n")]
    #size = size.decode()
    #size = int(size, base=16)
    #return size

    data = b""
    while b"\r\n" not in data:
        data += s.recv(1)
    data = data.split(b"\r\n")[0]
    try:
        data = data.decode()
    except:
        print("data: ", data)
    data = int(data, base = 16)
    return data

def skip_eof_chunk(s):
    skippable = b""
    while b"\r\n" not in skippable:
        skippable += s.recv(1)

def recv_chunk_content(s, chunkSize, chunks:list):
    complete_chunk = b''
    while True:
        if chunkSize > MAXBUF:
            data = s.recv(MAXBUF)
        else: 
            data = s.recv(chunkSize)
        chunkSize -= len(data)
        complete_chunk +=data
        if chunkSize == 0:
            break
    chunks.append(complete_chunk)

def CheckIsFolder(link_name):
    return((get_file_ending(link_name).find('.') == -1))



s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def client_receive(s, temp_buff):
    chunks = []
    #Content length
    if(b"Content-Length" in temp_buff):
        print("content_length download!")
        content_length = find_content_length(temp_buff)
        if b"\r\n\r\n" in temp_buff:
            data = temp_buff[temp_buff.find(b"\r\n\r\n") + 4:]
        while True:
            data = s.recv(MAXBUF)
            if not data:
                break
            content_length -= len(data)
            chunks.append(data)
            if content_length <= 0:
                break
        return chunks
            
        #file = open(file_name, "wb")
        #for i in chunks:
        #    file.write(i)
        #file.close()
    elif(b"Transfer-Encoding: chunked" in temp_buff):
        print("chunked encoding download!")
        chunkSize = get_chunk_size(s)
        while chunkSize != 0:
            recv_chunk_content(s, chunkSize, chunks)
            skip_eof_chunk(s)
            chunkSize = get_chunk_size(s)
        return chunks
        #file = open(file_name, "wb")
        #for i in chunks:
        #    file.write(i)
        #file.close()

def client_service(s, link ):
    domain = get_domain_name(link)
    file_name = output_file_name(link)
    link_to_file = get_link_to_file(link)
    is_folder = CheckIsFolder(link)

    s.connect((domain, 80))

    request = "GET " +link_to_file + " HTTP/1.1\r\nHost:"+ domain +"\r\nConnection: keep-alive\r\nKeep-Alive: timeout=5, max=100\r\n\r\n"

    s.sendall(request.encode())
    temp_buff = receiveHeader(s)
    #complete first data
    first_data = client_receive(s, temp_buff)

    destination_folder =  file_name

    if( not is_folder): 
        file = open(file_name, "wb")
        for i in first_data:
            file.write(i)
        file.close()
    else:
        #creating folder for files
        if(os.path.dirname(current_Directory) != current_Directory):
            os.chdir(current_Directory)
        if(os.path.isdir(destination_folder) == False):
            os.mkdir(destination_folder)
        os.chdir(destination_folder)

        #write index file before reading all sub files
        file = open(file_name, "wb")
        data_index = first_data
        for i in data_index:
            file.write(i)
        file.close()

        #get all sub files into a list
        sub_files = []
        data = b''.join(first_data)
        for line in data.split(b'\n'):
            if(line.find(b'href=') >= 0):
                begPos = line.find(b'\"', line.find(b'href='))
                endPos = line.find(b'\"', begPos + 1)
                fileName = line[begPos + 1 : endPos]
                if(fileName.find(b'.') >= 0):
                    sub_files.append(fileName)

        for request in sub_files:
            fileName = request.decode().replace('%20', ' ')
            request_msg = "GET " + link_to_file + request.decode() + " HTTP/1.1\r\nHost:"+ domain +"\r\nConnection: keep-alive\r\nKeep-Alive: timeout=5, max=100\r\n\r\n"
            s.sendall(request_msg.encode())
            temp_buff = receiveHeader(s)
            sub_data = client_receive(s, temp_buff)
            os.chdir(current_Directory + '\\' + destination_folder)
            file = open(fileName, "wb")
            data_sub = sub_data
            for i in data_sub:
                file.write(i)
            file.close()

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for index in range(1, len(sys.argv)):
            link = sys.argv[index]
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            executor.submit(client_service, s, link)