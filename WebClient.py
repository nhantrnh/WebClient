import socket
import threading
import pathlib
import PySimpleGUI as sg
import re

layoutLinkList = [
    [sg.Text("Put your link : "), sg.In(size = (25, 1), enable_events = True, key = "-LINK-")], 
    [sg.Text(enable_events = True, size = (40, 15), key = "-LINK LIST-", background_color = "white", text_color = "black")], 
    [sg.Button("GET"), sg.Button("CLEAR"), sg.Button("DOWNLOAD")]
]

layoutFileDownload = [[sg.Text("File downloading : ")], 
    [sg.Text(size = (40, 15), key = "-FILE-", background_color = "white", text_color = "black")]]

layoutConsole = [[sg.Text("Information")], 
    [sg.Multiline(size = (40, 15), key = "-CONSOLE-", background_color = "white", text_color = "black")]]

layoutWindow = [[sg.Column(layoutLinkList), sg.VSeperator(), sg.Column(layoutFileDownload), sg.VSeperator(), sg.Column(layoutConsole)]]
sg.theme('SandyBeach')
sg.SetGlobalIcon("client.ico")
window = sg.Window(title = "CLIENT", layout = layoutWindow, enable_close_attempted_event = True, keep_on_top = True)

def checkLink(url):  
    for s in url:                   # Delete superfluous slashes ("/") at the beginning or at the end of url:
        if url.find("/",0,len(url)) == 0 :
            url = url[1: ]
        if url.rfind("/",len(url)-1,len(url)) != -1:
            url = url[0 : len(url)-1]
    if url.find("http://") != -1:   # If url user put in has "http://", cut and get url without "http://"
        url = url[7 :]
    url = url + "/"                 # Add a slash to url
    return url

def isValidURL(url):
    regex = ("((http|https)://)(www.)?" +
             "[a-zA-Z0-9@:%._\\+~#?&//=]" +
             "{2,256}\\.[a-z]" +
             "{2,6}\\b([-a-zA-Z0-9@:%" +
             "._\\+~#?&//=]*)")
    p = re.compile(regex)
    if (url == None):
        return False
    if (re.search(p,url)):
        return True
    else:
        return False

def findHost(url):
    return url[ : url.find("/")]    # Host starts from the beginning of url to the character before the first slash "/" because after checking url, url has no http:// anymore. 

def findPath(url):
    path = url[url.find("/") : len(url)]    # Path starts after the first slash of url to the end of url
    if path.rfind("/",len(path)-1,len(path)) != -1:
        path = path[0 : len(path)-1]
    if path == "":                          # If after finding path, it has no character then we add a slash for it.
        path = path + "/"
    return path

def findFileName(url):
    url = url[  : len(url) - 1]          # Delete the finnal slash
    pos = url.rfind("/",0,len(url))      # Checking if Url had a slash from the right of it.
    if (pos == -1):                      # Pos return -1 when not find "/", then return a hollow string
        return ""
    else:
        return str(url[pos+1: len(url)]) # Return a tring from the position of "/" plus 1 to the end of url to get FileName

def createName(url):
    if findFileName(url).find(".",0,len(findFileName(url))) == -1 and findFileName(url) == "": # If request is "/"
        name = "./" + findHost(url) + "_index.html"                                            # then has no filename and client will download and save file with name: “<domain>_index.html”
                                                                                               # Ex: http://example.com or http://example.com/ --> "example.com_index.html"
    if findFileName(url).find(".",0,len(findFileName(url))) != -1 and findFileName(url) != "": # If request is a file
        name = "./" + findHost(url) + "_" + findFileName(url)                                  # then client will download and save file with name:"<domain>_<tenfile>". 
                                                                                               # Ex: http://example.com/index.html -> “example.com_index.html”
    if findFileName(url).find(".",0,len(findFileName(url))) == -1 and findFileName(url) != "": # If request is a subfolder
        name = "./" + findHost(url) + "_" + findFileName(url)                                  # then client will download and save file into folder "<domain>_<tenfolder>"
                                                                                               # Ex: http://web.stanford.edu/class/cs224w/slides/ -> “web.stanford.edu_slides”,
    if url == findHost(url) + "/" + findFileName(url) + "/" and findFileName(url) != "" and findFileName(url).find(".",0,len(findFileName(url))) == -1:
        name = "./" + findHost(url) + "_" + findFileName(url) + ".html"                        # Another case
                                                                                               # Ex: http://anglesharp.azurewebsites.net/Chunked -> "anglesharp.azurewebsites.net_Chunked.html"
    return name

def getHeader(client):
    header = ""                             # Give a hollow string
    while True:                             # Start to get header
        header = header + client.recv(1).decode()
        if header.find("\r\n\r\n") != -1:   # When header has \r\n\r\n, that's at the end of header, then break.
            break
        if not header:                      # If header was hollow then break.
            break
    return header

def isContentLength(contentLength):
    return contentLength != 0                        # If header has content length, the length will be longer than 0

def isChunked(pos):
    return pos != -1                                # If header does not have "Transfer-Encoding: chunked" then return -1

def isSubFolder(url):
    if findFileName(url).find(".",0,len(findFileName(url))) == -1 and findFileName(url) != "" and url != findHost(url) + "/" + findFileName(url) + "/":
        return 1   # If request is subfolder then return 1
    return 0

def findContentLength(header):
    if header.find("Content-Length: ") != -1:        # Find string "Content-Length: " and get the length 
        contentLength = int(header[header.find("Content-Length: ") + 16 : header.find("\r\n", header.find("Content-Length: ") + 16)]) # From after "Content-Length: " to "\r\n" of its sentence and convert this string into number
    else:
        contentLength = 0                            # If not has "Content-Length: ", return 0
    return contentLength

def getBodyByContentLength(client, contentLength):
    body = b""
    while len(body) < contentLength:        # Recieve until the length of body is equal with contentLength we got
        body = body + client.recv(100000)
        if not body:                        # If body was hollow then break.
            break
    return body

#4\r\n        (bytes to send)
#Wiki\r\n     (data)
#6\r\n        (bytes to send)
#pedia \r\n   (data)
def getBodyByChunked(client):
    body = b""
    while True:
        chunkedSize = ""                                                        # create a hollow string to get size of each chunked
        while True:
            chunkedSize = chunkedSize + client.recv(1).decode()
            if chunkedSize.find("\r\n") != -1:                                  # Stop recieving when chunkedSize has \r\n
                chunkedSize = int(chunkedSize[ : chunkedSize.find("\r\n")], 16) # Convert string into number
                break
        if chunkedSize == 0:                                                    # After recieving enough body, chunkedSize = 0 
            break
        chunked = b""                               # get chunkued
        reslen = 0                                  # size of chunked being got
        while reslen < chunkedSize:                 # Recieve until the length of chunked is equal with chunkedSize we got
            tempt = client.recv(chunkedSize - reslen)
            chunked = chunked + tempt
            reslen = reslen + len(tempt)
        body = body + chunked                       # Add chunked to body
        delete = client.recv(2)                     # Create a tempt to recieve "\r\n" at the end of each chunked
        if not body:                                # If body was hollow, then break.
            break
    return body

def getSubFolderBody(client, host, url, body):
    folderpath = createName(url)    # Create a folder name
    path = pathlib.Path(folderpath) # Create a path
    path.mkdir(exist_ok = True)     # If it was available then don't create
    
    pos = body.find(b"href=")       # Find the position of the first "href="
    while pos != -1:                # Until has no "href=" in body
        if body.find(b".", pos, body.find(b">", pos)) != -1:   # If there was a file, it must have format name.type as well as have "." in its 
            filename = body[body.find(b"\"", pos) + 1 : body.find(b"\"", body.find(b"\"", pos) + 1)].decode() # Find the file name, from the " behind "href =" until the next "
            path = findPath(url) + "/" + filename                    # Path = Path of folder + File Name
            
            request = "GET " + path + " HTTP/1.1\r\nHost:" + host + "\r\nConnection: keep-alive\r\n\r\n" # Request GET 
            client.send(request.encode()) # Send request

            header = getHeader(client) # Get header of each file in subfolder
           
            # Get body of each file
            if isContentLength(findContentLength(header)):              # If content length > 0 then get body by content-length
                bodyFile = getBodyByContentLength(client, findContentLength(header))
                
            elif isChunked(header.find("Transfer-Encoding: chunked")):  # If it had "Transfer-Encoding: chunked" then get body by chunked
                bodyFile = getBodyByChunked(client)
            
            file = open(folderpath + "/" + filename,'wb')               # Write to file
            file.write(bodyFile)
            file.close()
        pos = body.find(b"href=", pos + 6)                              # Find the next position of "href="
                
def clientConnection(url):
    url = checkLink(url)
    host = findHost(url)
    path = findPath(url)
    if isSubFolder(url) == 1:
        path = path + "/"
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create a TCP socket
    
        client.connect((host, 80)) # Connect to web server port 80
    
        request = "GET " + path + " HTTP/1.1\r\nHost: " + host + "\r\nConnection: keep-alive\r\n\r\n"  # Request GET
        client.send(request.encode()) # Send request
    except:
        sg.popup(f"Disconnect to web server!")
    try:
        header = getHeader(client)                                # Get header
        window["-CONSOLE-"].update(window["-CONSOLE-"].get() + header)
        window["-CONSOLE-"].update(window["-CONSOLE-"].get() + "\n")
        
        filename = createName(url)                                # Create File name
        if isContentLength(findContentLength(header)):            # If content length > 0 then get body by content-length
            body = getBodyByContentLength(client, findContentLength(header))
        elif isChunked(header.find("Transfer-Encoding: chunked")): # If it had "Transfer-Encoding: chunked" then get body by chunked
            body = getBodyByChunked(client)
        
        if isSubFolder(url) == 1:                  # If it was a subfolder then down and save file by subfolder
            getSubFolderBody(client, host, url, body)
        else:                                      # Else down and save by:
            path = pathlib.Path(filename)          # Create a path to save file
            path.touch(exist_ok = True)            # If it was available then don't create
            file = open(filename, 'wb')            # Write to file
            file.write(body)
            file.close()                           # Close file
    except:
        print("Disconnect to web server")
    finally:
        client.close()                             # Close socket

# window.SetIcon(r'')

while True:
    event, values = window.read()

    if event == sg.WINDOW_CLOSE_ATTEMPTED_EVENT and sg.popup_yes_no('Do you really want to exit?', keep_on_top = True) == 'Yes':
        break

    text = window["-LINK LIST-"]
    if event == "GET":
        if isValidURL(values["-LINK-"]):
            text.update(text.get() + values["-LINK-"] + "\n")
        else:
            sg.popup_error_with_traceback(f"Invalid url! Please enter again")
    elif event == "CLEAR":
        text.update("")
        window["-FILE-"].update("")
        window["-CONSOLE-"].update("")
    elif event == "DOWNLOAD":
        mainURL = text.get()
        mainURL = mainURL[:len(mainURL)-1]
        url = mainURL.split("\n")

        try:
            for i in url:
                i = i[7 :]
                if i == "":
                    sg.popup_error_with_traceback(f"Invalid url! Please enter again")
                    break
                else:
                    c = threading.Thread(target = clientConnection, args = (i, ))
                    c.start()
                    window["-FILE-"].update(window["-FILE-"].get() + createName(i) + "\n")
                    sg.popup(f"Successful!", keep_on_top = True)
                    text.update("")
        except:
            sg.popup_error(f"Error", keep_on_top = True)

window.close()
