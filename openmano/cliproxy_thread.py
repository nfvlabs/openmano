#!/usr/bin/python
# This is a simple port-forward / proxy, written using only the default python
# library. If you want to make a suggestion or fix something you can contact-me
# at voorloop_at_gmail.com
# Distributed over IDC(I Don't Care) license
import socket
import select
import time
import sys
import threading

# Changing the buffer_size and delay, you can improve the speed and bandwidth.
# But when buffer get to high or delay go too down, you can broke things
buffer_size = 4096

class Forward:
    def __init__(self):
        self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, host, port):
        try:
            self.forward.connect((host, port))
            return self.forward
        except Exception as e:
            print "Conect to proxy exception", e
            return False

class CliProxyException(Exception):
    '''raise when an exception has found''' 
class CliProxyExceptionPortUsed(Exception):
    '''raise when the port is used''' 

class CliProxyThread(threading.Thread):
    active_delay = 0.0001
    inactive_delay = 1

    def __init__(self, host, port, proxy_host, proxy_port):
        try:
            threading.Thread.__init__(self)
            self.proxy_host = proxy_host
            self.proxy_port = proxy_port
            self.host = host
            self.port = port
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((host, port))
            self.server.listen(200)
            #TODO timeout in a lock section can be used to autoterminate the thread
            #when inactivity and timeout<time : set timeout=0 and terminate
            #from outside, close class when timeout==0; set timeout=time+120 when adding a new console on this thread
            #set self.timeout = time.time() + 120 at init
            self.name = "CLIproxy " + proxy_host + ":" + str(proxy_port)
            self.input_list = [self.server]
            self.channel = {}
            self.terminate = False #put at True from outside to force termination
        except (socket.error, socket.herror, socket.gaierror, socket.timeout) as e:
            raise CliProxyException(type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0])) )
        
    def run(self):
        while 1:
            try:
                inputready, _, _ = select.select(self.input_list, [], [], 1)
            except select.error as e:
                print self.name, ": Exception on select %s: %s" % (type(e).__name__, str(e) )
                self.on_terminate()

            if self.terminate:
                self.on_terminate()
                print self.name, ": Terminate because commanded"
                break
            
            for sock in inputready:
                if sock == self.server:
                    self.on_accept()
                else:
                    self.on_recv(sock)
                    
    def on_terminate(self):
        while self.input_list:
            if self.input_list[0] is self.server:
                server.close()
                del self.input_list[0]
            else:
                self.on_close(self.input_list[0], "Terminating thread")

    def on_accept(self):
        #accept
        try:
            clientsock, clientaddr = self.server.accept()
        except (socket.error, socket.herror, socket.gaierror, socket.timeout) as e:
            print self.name, ": Exception on_accept %s: %s" % (type(e).__name__, str(e) )
            return False
        #print self.name, ": Accept new client ", clientaddr

        #connect
        try:
            forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            forward.connect((self.proxy_host, self.proxy_port))
            name = "%s:%d => (%s:%d => %s:%d) => %s:%d" %\
                (clientsock.getpeername() + clientsock.getsockname()  + forward.getsockname() + forward.getpeername() )
            print self.name, ": new connection " + name
                
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            info = { "name": name,
                    "clientsock" : clientsock,
                    "serversock" : forward
                    }
            self.channel[clientsock] = info
            self.channel[forward] = info
            return True
        except (socket.error, socket.herror, socket.gaierror, socket.timeout) as e:
            print self.name, ": Exception on_connect to server %s:%d; %s: %s" % (self.proxy_host, self.proxy_port, type(e).__name__, str(e) )
            print self.name, ": Close client side ", clientaddr
            clientsock.close()
            return False

    def on_close(self, sock, cause):
        if sock not in self.channel:
            return  #can happen if there is data ready to received at both sides and the channel has been deleted. QUITE IMPROBABLE but just in case
        info = self.channel[sock]
        #debug info
        sockname = "client" if sock is info["clientsock"] else "server"
        print self.name, ": del connection %s %s at %s side" % (info["name"], cause, sockname)
        #close sockets
        try:
            # close the connection with client
            info["clientsock"].close()  # equivalent to do self.s.close()
        except (socket.error, socket.herror, socket.gaierror, socket.timeout) as e:
            print self.name, ": Exception on_close client socket %s: %s" % (type(e).__name__, str(e) )
        try:
            # close the connection with remote server
            info["serversock"].close()
        except (socket.error, socket.herror, socket.gaierror, socket.timeout) as e:
            print self.name, ": Exception on_close server socket %s: %s" % (type(e).__name__, str(e) )
        
        #remove objects from input_list
        self.input_list.remove(info["clientsock"])
        self.input_list.remove(info["serversock"])
        # delete both objects from channel dict
        del self.channel[info["clientsock"]]
        del self.channel[info["serversock"]]

    def on_recv(self, sock):
        if sock not in self.channel:
            return  #can happen if there is data ready to received at both sides and the channel has been deleted. QUITE IMPROBABLE but just in case
        info = self.channel[sock]
        peersock = info["serversock"] if sock is info["clientsock"] else info["clientsock"]
        try:
            data = sock.recv(buffer_size)
            if len(data) == 0:
                self.on_close(sock, "peer closed")
            else:
                #print self.data
                sock = peersock
                peersock.send(data)
        except (socket.error, socket.herror, socket.gaierror, socket.timeout) as e:
            #print self.name, ": Exception %s: %s" % (type(e).__name__, str(e) )
            self.on_close(sock, "Exception %s: %s" % (type(e).__name__, str(e) ))

        

    def start_timeout(self):
        self.timeout = time.time() + 120
        
        
if __name__ == '__main__':
        server = CliProxyThread('', 9999, '10.95.172.129', 6080)
        try:
            server.main_loop()
        except KeyboardInterrupt:
            print "Ctrl C - Stopping server"
            sys.exit(1)

