# -*- coding: utf-8 -*-

##
# Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U.
# This file is part of openmano
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact with: nfvlabs@tid.es
##

'''
Implement like a proxy for TCP/IP in a separated thread.
It creates two sockets to bypass the TCP/IP packets among the fix console 
server specified at class construction (console_host, console_port)
and a client that connect against the (host, port) specified also at construction

                ---------------------           -------------------------------
                |       OPENMANO     |          |         VIM                  |
client 1  ----> | ConsoleProxyThread | ------>  |  Console server              |
client 2  ----> |  (host, port)      | ------>  |(console_host, console_server)|
   ...           --------------------            ------------------------------
'''
__author__="Alfonso Tierno"
__date__ ="$19-nov-2015 09:07:15$"

import socket
import select
import threading


class ConsoleProxyException(Exception):
    '''raise when an exception has found''' 
class ConsoleProxyExceptionPortUsed(ConsoleProxyException):
    '''raise when the port is used''' 

class ConsoleProxyThread(threading.Thread):
    buffer_size = 4096
    check_finish = 1 #frequency to check if requested to end in seconds

    def __init__(self, host, port, console_host, console_port):
        try:
            threading.Thread.__init__(self)
            self.console_host = console_host
            self.console_port = console_port
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
            self.name = "ConsoleProxy " + console_host + ":" + str(console_port)
            self.input_list = [self.server]
            self.channel = {}
            self.terminate = False #put at True from outside to force termination
        except (socket.error, socket.herror, socket.gaierror, socket.timeout) as e:
            if e is socket.error and e.errno==98:
                raise ConsoleProxyExceptionPortUsed("socket.error " + str(e))
            raise ConsoleProxyException(type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0])) )
        
    def run(self):
        while 1:
            try:
                inputready, _, _ = select.select(self.input_list, [], [], self.check_finish)
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
                self.server.close()
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
            forward.connect((self.console_host, self.console_port))
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
            print self.name, ": Exception on_connect to server %s:%d; %s: %s" % (self.console_host, self.console_port, type(e).__name__, str(e) )
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
            data = sock.recv(self.buffer_size)
            if len(data) == 0:
                self.on_close(sock, "peer closed")
            else:
                #print self.data
                sock = peersock
                peersock.send(data)
        except (socket.error, socket.herror, socket.gaierror, socket.timeout) as e:
            #print self.name, ": Exception %s: %s" % (type(e).__name__, str(e) )
            self.on_close(sock, "Exception %s: %s" % (type(e).__name__, str(e) ))

        

    #def start_timeout(self):
    #    self.timeout = time.time() + 120
        
