import BaseHTTPServer
import SocketServer
import urlparse
import time
import sys
import os

def tail_f(file, interval = 1.0, atLeast1Kb = False):
    if atLeast1Kb == False:
        file.seek(0)
    else:
        file.seek(-1024,2)

    while True:
        where = file.tell()
        line = file.readline()
        if not line:
            time.sleep(interval)
            file.seek(where)
        else:
            yield line

class LogWebServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    daemon_threads = True

class LogRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        ae = self.headers.get('accept-encoding') or ''

        self.protocol_version = 'HTTP/1.1'
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')

        def write_chunk():
            tosend = '%X\r\n%s\r\n'%(len(chunk), chunk)
            self.wfile.write(tosend)

        parsedURL = urlparse.urlsplit(self.path)
        theFile = None
        atLeast1Kb = False
        try:
            filePath = parsedURL.query.split('=')[1]
            print("File is: " + filePath)
            if os.stat(filePath).st_size > 1024:
                atLeast1Kb = True
            try:
                theFile = open(filePath, "r")
            except IOError:
                self.send_error(404, "Problem reading file")
                return
        except:
            self.send_error(500, "?file=<some path> is required")
            return

        if parsedURL.path == "/download":
            self.send_header('Content-Disposition', 'attachment;' 'filename=%s' % filePath.split('/')[-1])
            self.end_headers()
            self.wfile.write(theFile.read())
        elif parsedURL.path == "/stream":
            self.send_header('Transfer-Encoding', 'chunked')
            self.end_headers()
            # get some chunks
            for chunk in tail_f(theFile, atLeast1Kb = atLeast1Kb):
                if not chunk:
                    continue
                write_chunk()
            # send the chunked trailer
            self.wfile.write('0\r\n\r\n')
        else:
            self.end_headers()
            self.wfile.write("Valid URLs are: '/stream', '/download'\n\n")

if __name__ == '__main__':
    listenIP = "0.0.0.0"
    if len(sys.argv) == 2:
        try:
            listenPort = int(sys.argv[1])
        except ValueError:
            print("Port number must be an integer...")
            sys.exit(1)
    else:
        print("No listen port specified, defaulting to 8080")
        listenPort = 8080
    server = LogWebServer(
        (listenIP, listenPort), LogRequestHandler)
    print("Starting server at http://" + listenIP + ":" + str(listenPort))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n<Ctrl-C> Caught, Shutting down.")
