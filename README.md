<h1 align="center"> <strong>HTTP Server Project</strong></b> </h1>
<p align="center">
  <img src="https://github.com/user-attachments/assets/c05857d8-d5c1-4f45-bdc8-1d7c2ca0fad0" width="500" height="500" alt="image" />
</p>


<h2 align="center"> A Multi-threaded HTTP Server Using Socket Programming </h2>

### **Objective**

Design and implement a multi-threaded HTTP server from scratch using low-level socket programming. This assignment deepens understanding of:

- HTTP protocol
- Concurrent programming
- Network security
- File handling (HTML, text, and binary)
- JSON processing
- Error handling

## **Folder Structure**
```
http-server-project/
├── server.py                 # Main Python HTTP server
├── resources/                # Directory containing all static and test resources
│   ├── index.html            # Default homepage
│   ├── about.html            # About page
│   ├── contact.html          # Contact page
│   ├── sample.txt            # Sample text file
│   ├── notes.txt             # Additional text file
│   ├── logo.png              # PNG image
│   ├── banner.png            # Additional PNG image
│   ├── photo.jpeg            # JPEG image
│   ├── portrait.jpeg         # Additional JPEG image
│   └── uploads/              # Folder to store POSTed JSON files
```
## **Features Implemented**

1. **Server Configuration**
    1. Default host: 127.0.0.1
    2. Default port: 8080
    3. Configurable thread pool size (default 10)
    4. Command-line arguments: ```python3 server.py \[port\] \[host\] \[threads\]  ```

       
1. **Socket Implementation**
    1. TCP socket server with queue size of 50
    2. Proper socket lifecycle management for persistent and non-persistent connections
2. **Multi-threading & Concurrency**
    1. Thread pool handles multiple clients concurrently
    2. Pending connections queued if threads are busy
    3. Synchronization ensures thread safety
3. **GET Request Handling**
    1. Serves HTML files (text/html; charset=utf-8)
    2. Serves text (.txt) and image files (.png, .jpeg) as binary with application/octet-stream
    3. Content-Disposition header triggers file download
    4. Returns HTTP status codes: 200, 404, 403, 415
4. **POST Request Handling**
    1. Accepts only application/json
    2. Saves JSON data in resources/uploads/
    3. Response: 201 Created with file path
    4. Returns 400 for invalid JSON, 415 for non-JSON
5. **Security Measures**
    1. Path traversal protection: blocks ../, /, \\ attempts
    2. Host header validation: only accepts 127.0.0.1:8080 or localhost:8080
    3. Logs forbidden attempts
6. **Connection Management**
    1. Keep-alive support (HTTP/1.1 default)
    2. Max 100 requests per persistent connection
    3. Timeout: 30 seconds
7. **Logging**
    1. Comprehensive logs: timestamps, thread ID, request method, path, status
    2. Logs file transfers including size

## **Setup Instructions**

1. **Clone the Repository**
   
      ``
       git clone (https://github.com/Sanskriti10247/http-server-project.git)
``


   ``
       cd http-server-project  
``

   
1. **Ensure Python 3.10+ is installed**
    1. Verify: ``` python3 --version  ```

       
1. **Directory Preparation**  
    The resources/ folder contains HTML, text, and image files.  
    Ensure the uploads/ folder exists for POST requests:       ```mkdir -p resources/uploads ```

   
## **Running the Server**
```
python3 server.py \[port\] \[host\] \[threads\]

```
- Default:
```
python3 server.py  
```
- Example with custom arguments:
```
python3 server.py 8000 0.0.0.0 20  
```
- Server log example:

    ``[2025-09-20 11:10:00] HTTP Server started on http://127.0.0.1:8080``

    ``[2025-09-20 11:10:00] Thread pool size: 10``

    ``[2025-09-20 11:10:00] Serving files from 'resources' directory``
  
**Reference**
  
 <img width="1600" height="505" alt="image" src="https://github.com/user-attachments/assets/f702ad5c-d0b1-4003-9f85-b41f1bc24c7b" />


## **Testing the Server**

### **1. GET Requests (Browser or Curl)**

```bash
# HTML pages
curl http://127.0.0.1:8080/
curl http://127.0.0.1:8080/about.html
curl http://127.0.0.1:8080/contact.html

# Binary downloads
curl -O http://127.0.0.1:8080/sample.txt
curl -O http://127.0.0.1:8080/notes.txt
curl -O http://127.0.0.1:8080/logo.png
curl -O http://127.0.0.1:8080/banner.png
curl -O http://127.0.0.1:8080/photo.jpeg
curl -O http://127.0.0.1:8080/portrait.jpeg
```
### References- Browser & Curl

**- HTML pages**

1. **Index.html:**
   
   <img width="1600" height="881" alt="image" src="https://github.com/user-attachments/assets/2b37843c-1886-481d-8430-de02f1b99779" />

3. **About.html:**
   
   <img width="1600" height="514" alt="image" src="https://github.com/user-attachments/assets/4bfa4f29-8aa5-46a1-b17f-52fa4b5ad270" />


   <img width="1600" height="881" alt="image" src="https://github.com/user-attachments/assets/caa20b6e-c149-4b45-96ab-888940670e55" />

5. **Contact.html:**
   
   <img width="1600" height="881" alt="image" src="https://github.com/user-attachments/assets/d3ead6d6-de36-465a-a27b-7e995fb54fcb" />


**- Binary Downloads**

- **Curl:** 

<img width="1442" height="908" alt="image" src="https://github.com/user-attachments/assets/4b5e39c3-b872-4d1e-a45d-d6372e65799f" />




- **Browser:** 

<img width="1600" height="130" alt="image" src="https://github.com/user-attachments/assets/1d74c868-c195-42b4-927e-e589df1c084e" />


<img width="1600" height="865" alt="image" src="https://github.com/user-attachments/assets/d917b2fc-c190-4e05-8dcf-6389516dcac8" />


### **2\. POST Requests (JSON Upload)**
```
curl -X POST -H "Content-Type: application/json" -d '{"name":"Sanskriti"}' <http://127.0.0.1:8080/upload>

- Uploaded files are stored in resources/uploads/
- Response:

{  
"status": "success",  
"message": "File created successfully",  
"filepath": "/uploads/upload_20250920_111010.json"  
}  
```

**- References**

<img width="1600" height="455" alt="image" src="https://github.com/user-attachments/assets/4e99fa54-0372-4a2a-a21a-8a27d2b59951" />

<img width="1600" height="455" alt="image" src="https://github.com/user-attachments/assets/96b79ac1-e60f-4519-8a91-b711551ec52b" />



### **3\. Concurrency Testing**
```
curl -O <http://127.0.0.1:8080/logo.png> &  
curl -O <http://127.0.0.1:8080/photo.jpeg> &  
curl -O <http://127.0.0.1:8080/sample.txt> &  
curl -O <http://127.0.0.1:8080/about.html> &  
curl -O <http://127.0.0.1:8080/contact.html> &  
```
**- References**

<img width="1600" height="539" alt="image" src="https://github.com/user-attachments/assets/5acc5e34-7e2f-401e-819f-1932fb295a98" />


- Logs multiple threads handling simultaneous requests


### **4\. Security Testing**
```
curl <http://127.0.0.1:8080/../etc/passwd> # 403 Forbidden  
curl <http://127.0.0.1:8080/./././../config> # 403 Forbidden  
curl -H "Host: evil.com" <http://127.0.0.1:8080/> # 403 Forbidden  
curl <http://127.0.0.1:8080/> # 400 Bad Request if Host missing  
```
**- References**

- 200 (Valid Request) :

  <img width="1600" height="463" alt="image" src="https://github.com/user-attachments/assets/18b16518-3851-47a7-956e-a10fcfc30107" />

- 400 (Bad Request) :
  
  <img width="1600" height="312" alt="image" src="https://github.com/user-attachments/assets/d8e450fb-13a0-4b2c-a78e-b98b97dcb322" />
  
- 403 (Forbidden) :

  <img width="1600" height="272" alt="image" src="https://github.com/user-attachments/assets/f6e62cd4-021b-47ca-be7d-1bce680923eb" />

- More filepaths Access(403 -Forbidden) :
  
  <img width="1600" height="215" alt="image" src="https://github.com/user-attachments/assets/8f4f4c71-838b-4b2a-b60c-8e9c723d64ad" />

- 404 (File Not Found) :
  
  <img width="1600" height="215" alt="image" src="https://github.com/user-attachments/assets/9f276b7f-7a79-4308-958e-b3ab10c9bb72" />

- 405 (Method Not Allowed) :
  
  <img width="1600" height="215" alt="image" src="https://github.com/user-attachments/assets/fe48ae50-ff87-4750-84f6-5c7c3ecb655e" />

- 415 (Unsupported Media Type) :
  <img width="1600" height="215" alt="image" src="https://github.com/user-attachments/assets/17fea9a6-2320-49b4-bd6f-6dc34f2ed9a3" />


### **Some Checks as mentioned in the document** 

1. Thread pool + Put (not allowed)

![PHOTO-2025-09-20-19-48-19](https://github.com/user-attachments/assets/69337aa2-657f-4cca-88b2-d6bdb5fc2c03)

2. CHECKSUM FOR ALL FILES:
   
  - Photo.jpeg
    
   <img width="817" height="117" alt="Screenshot 2025-09-29 at 11 16 11 AM" src="https://github.com/user-attachments/assets/5ecb859c-39ef-45a7-bb4e-fc4cb6eb47b0" />
   
  - Banner.png
    
   <img width="817" height="66" alt="Screenshot 2025-09-29 at 11 17 18 AM" src="https://github.com/user-attachments/assets/87f2409a-8ced-4ffd-b2d5-2c0865320fdf" />

  - Notes.txt
    
   <img width="817" height="66" alt="Screenshot 2025-09-29 at 11 27 11 AM" src="https://github.com/user-attachments/assets/9138ee91-09ff-443b-a734-2a03643e507c" />

    
3.Missing Host Header- Response(Restriction)

![PHOTO-2025-09-20-21-03-21](https://github.com/user-attachments/assets/d1a69587-e26f-4936-8bfe-bdb792ac63b4)


## **Server Logging Example**
```
[2025-09-20 11:15:00\] \[Thread-1\] Connection from 127.0.0.1:54321  
[2025-09-20 11:15:00\] \[Thread-1\] Request: GET /logo.png  
[2025-09-20 11:15:00\] \[Thread-1\] Host validation: localhost:8080 ✓  
[2025-09-20 11:15:00\] \[Thread-1\] Sending binary file: logo.png (34567 bytes)  
[2025-09-20 11:15:00\] \[Thread-1\] Response: 200 OK (34567 bytes transferred)  
[2025-09-20 11:15:00\] \[Thread-1\] Connection: keep-alive  

```
**- References**

<img width="1600" height="449" alt="image" src="https://github.com/user-attachments/assets/78f1549c-515d-49c0-9cc1-a5e9467132c1" />

## **Limitations**

- **No HTTPS/SSL:** Only supports HTTP; data is transmitted in plaintext.
- **Limited File Types:** Only .html, .txt, .png, and .jpeg files are supported. Other types return 415.
- **Memory Usage:** Binary files are fully loaded into memory, which may slow transfers for large files.
- **Fixed Thread Pool:** Thread count is static; high load may queue or drop connections.
- **Simple POST Handling:** Only creates JSON files; updates or deletions are not supported.
- **Console Logging Only:** No persistent log files for analysis.
- **Connection Limits:** Keep-alive supports up to 100 requests; idle timeout is 30 seconds.
- **Localhost Only:** Host validation restricts access to 127.0.0.1 or localhost.

## **Future Enhancements**

- Add **HTTPS support** for secure communication.
- Implement **streaming/chunked file transfers** to handle large files efficiently.
- Support **more MIME types** and dynamic content handling.
- Enable **persistent log files** with configurable log levels.
- Allow **dynamic thread pool scaling** based on server load.
- Add **file update and delete functionality** for POST/PUT requests.
- Implement **advanced HTTP features**: caching headers, ETags, and chunked encoding.
- Support **remote access** with proper authentication and host validation.
  
 Table for reference :-
  
| Method      | Status            | Description                                                   |
| ----------- | ----------------- | ------------------------------------------------------------- |
| **GET**     | Supported         | Serves HTML pages and binary files with correct MIME/headers. |
| **POST**    | Supported         | Accepts only JSON, saves with timestamp in `uploads/`.        |
| **PUT**     | Placeholder       | Returns **405 Method Not Allowed** (not implemented yet).     |
| **DELETE**  | Placeholder       | Returns **405 Method Not Allowed** (not implemented yet).     |
| **HEAD**    | Not Implemented   | Future enhancement.                                           |
| **OPTIONS** | Not Implemented   | Future enhancement.                                           |
