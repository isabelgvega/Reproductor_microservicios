#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from http import server
import secrets
import Ice
import time
import json
import random
import os
import threading
import topic_management
import signal
import uuid
import sys
import IceStorm
Ice.loadSlice('iceflix.ice')
import IceFlix

ACTUALIZADO = False

AUTENTICATOR_AVAILABLE = {}
PRINCIPALES_DISP = {}

TAMANIO_TOKEN = 40
'''dictionary < string, string > UsersToken'''
TOKENS = set()
'''dictionary < string, string > UsersPasswords'''
USUARIOS= {}
ARCHIVO_USUARIO = './data/users.json'


#Estrcutura UsersDB
class UsersDB(IceFlix.UsersDB):

    def __init__(self,userPasswords,usersToken):
        self.userPasswords=userPasswords
        self.usersToken=usersToken

#Clase de eventos Revocations (Event channel for Authenticator() for notifications to all microservices interface Revocations  )
class Revocations(IceFlix.Revocations):

    global USUARIOS
    global TOKENS

    def __init__(self, server_ID):
        self.server_ID = server_ID

    #Emitido cuando expira un token. Args: string, string, string
    def revokeToken(self, userToken, srvId, current=None):

        global TOKENS
        if not srvId == self.server_ID:
            print("[AUTH]: Se ha emitido un revokeToken con el id: "+srvId+"\n")
            TOKENS.remove(userToken)

    #Emitido cuando un usuario es borrado. Args: string, string, string
    def revokeUser(self, user, srvId, current=None):

        if not srvId == self.server_ID:
            TOKENS.remove(USUARIOS[user]['token_actual'])
            print("[AUTH]: Se ha emitido un revokeUser con el id: "+srvId+"\n")
            del USUARIOS[user]


#Canal de eventos para todos los microservicios a todos los microservicios:
class ServiceAnnouncements(IceFlix.ServiceAnnouncements):

    def __init__(self, auth, uuid):
        self.auth = auth
        self.srvId = uuid

    #Emite un inicio de servicio, despues que este listo de atender clientes. Args: Object*, string
    def newService(self, service, srvId, current=None):

        global PRINCIPALES_DISP
        global AUTENTICATOR_AVAILABLE

        if not srvId == self.srvId:

            if service.ice_isA('::IceFlix::Authenticator'):

                if srvId not in AUTENTICATOR_AVAILABLE:

                    AUTENTICATOR_AVAILABLE[srvId] = IceFlix.AuthenticatorPrx.uncheckedCast(service)
                    
                    if len(AUTENTICATOR_AVAILABLE) > 0:

                        pase_usuario = self.auth.obtener_datos('contrasena_hash')
           
                        token_usuario = self.auth.obtener_datos('token_actual')
                        
                        print(str(token_usuario))
                        currentDatabase = UsersDB(pase_usuario, token_usuario)
                        nueva_autentificacion = IceFlix.AuthenticatorPrx.uncheckedCast(service)
                        
                        nueva_autentificacion.updateDB(currentDatabase, self.srvId)
                        print("[AUTH]: Updating database.... DONE!")
    
    #Emite cuando un servidor empieza a estar disponible. Args: Object*, string
    def announce(self, service, srvId, current=None):

        global PRINCIPALES_DISP
        global AUTENTICATOR_AVAILABLE

        if not srvId == self.srvId:

            if service.ice_isA('::IceFlix::Main'):

                if srvId not in PRINCIPALES_DISP:
                    
                    PRINCIPALES_DISP[srvId] = IceFlix.MainPrx.uncheckedCast(service)
                    print("[AUTH]: Received service announcement ::IceFlix::Main\n")

            if service.ice_isA('::IceFlix::Authenticator'):

                if srvId not in AUTENTICATOR_AVAILABLE:

                    AUTENTICATOR_AVAILABLE[srvId] = IceFlix.AuthenticatorPrx.uncheckedCast(service)
                    print("[AUTH]: Received service announcement ::IceFlix::Authenticator\n")

#Interfaz Authenticator
class Authenticator (IceFlix.Authenticator):

    def __init__(self, broker, u_ID):
        self.broker = broker
        self.server_ID = u_ID 
            
    #obtiene el token o el passwordhash del usuario depende de lo que escriba en type (si se passwordhass se obtiene la contraseña y en caso contrario el token)
    def obtener_datos(self,type):
        global USUARIOS
        list = {}
        if type == 'contrasena_hash':
            for usuario in USUARIOS:
                content = USUARIOS[usuario].get(type, None)
                data = {usuario: content}
                list.update(data)
        else:
            for usuario in USUARIOS:
                content = USUARIOS[usuario].get(type, None)
                data = {usuario: content}
                list.update(data)
        return list
    #metodo que obtiene el proxy
    def obtener_proxy(self, proxy):

        self._proxy_ = proxy
    # metodo que actualiza la base de datos de usuario, actuallizando informacion en el archivo JSON
    def actualizar_bbdd_usuario(self):

        global USUARIOS
        with open(ARCHIVO_USUARIO, 'w') as contents:
            json.dump(USUARIOS, contents, indent=4, sort_keys=True)

    def obtenerActualizaciones_publicador(self):

        tema = topic_management.obtainManager(self.broker)
        actualizaciones_usuarios_tema = topic_management.obtainTopic(
            tema, 'UserUpdates')
        publicador = actualizaciones_usuarios_tema.getPublisher()
        actualizacion_usuarios = IceFlix.UserUpdatesPrx.uncheckedCast(
            publicador)
            
        return actualizacion_usuarios

    #Operaciones para tokens
    def actualizar_auths(self,usuario, token_nuevo, server_ID, actualizaciones):

        actualizar_usuario = actualizaciones
        actualizar_usuario.newToken(usuario, token_nuevo, server_ID)

    def remplazar_token(self,usuario, token_actual):

        global TOKENS
        global USUARIOS
        
    
        TOKENS.remove(token_actual)
        USUARIOS[usuario]['token_actual'] = ""
        token_nuevo = secrets.token_urlsafe(TAMANIO_TOKEN)
        return token_nuevo

    def aniadir_token(self,token_nuevo, usuario):

        global TOKENS
        global USUARIOS
        TOKENS.add(token_nuevo)
        USUARIOS[usuario]['token_actual'] = token_nuevo

    def eliminar_Usuarios(self,usuario, token_usuario):

        global TOKENS
        global USUARIOS
        for valor in TOKENS:
            if valor.__eq__(token_usuario):
                TOKENS.remove(valor)
                break
        del USUARIOS[usuario]

    #Si es usuario son userUpdates, sino son Revocation
    def obtener_publicaciones(self,type):

        tema = topic_management.obtainManager(self.broker)
       
        if str(type).__eq__('Revocations'):
            tema_revocacion = topic_management.obtainTopic(tema, type)
            publicador = tema_revocacion.getPublisher()
            revocacion = IceFlix.RevocationsPrx.uncheckedCast(publicador)
        
            return revocacion
        else:
            userUpdates_topic = topic_management.obtainTopic(tema, type)
            publicador = userUpdates_topic.getPublisher()
            atualizaciones_usuario = IceFlix.UserUpdatesPrx.uncheckedCast(publicador)
         
            return atualizaciones_usuario
    def timeout_revocacion(self,token_nuevo,serverid):
        time.sleep(120)
        print("[AUTH]: El token {} ha expirado".format(token_nuevo), flush=True)
        revoc = self.obtener_publicaciones('Revocations')
        print("[AUTH]: El revocations proxy es {}".format(revoc))
        revoc.revokeToken(token_nuevo, serverid)
    #Ex: Throws Unauthorized. Agrumentos tipo: string,string
    def refreshAuthorization(self, user, passwordHash, current=None):

        global USUARIOS
        global TOKENS

        if user not in USUARIOS:
            print("[AUTH]: User not found")
            raise IceFlix.Unauthorized()

        token_actual = USUARIOS[user].get('token_actual', None)
        contrasenia_hash_actual = USUARIOS[user].get('hash_contrasena', None)
        if not contrasenia_hash_actual == passwordHash:
            print("[AUTH]: Invalid Password")
            raise IceFlix.Unauthorized()
            
        token_nuevo = self.remplazar_token(user, token_actual)
        self.aniadir_token(token_nuevo, user)
        self.actualizar_bbdd_usuario()
        self.actualizar_auths(user, token_nuevo, self.server_ID, self.obtener_publicaciones('UserUpdates'))
        try:
            hilo=threading.Thread(target=self.timeout_revocacion,args=(token_nuevo, self.server_ID),).start()
            
        except Exception as e:
            print(e)
        return token_nuevo
        

            
    # Agrumentos tipo: string
    def isAuthorized(self, userToken, current=None):

        global TOKENS
        global USUARIOS
        autorizado=True

        with open(ARCHIVO_USUARIO, 'r') as contents:
            USUARIOS = json.load(contents)
        if userToken not in TOKENS or not userToken:
            autorizado = False
            
        return autorizado

    # Ex: Throws Unauthorized. Agrumentos tipo: string
    def whois(self, userToken, current=None):

        global TOKENS
        global USUARIOS

        with open(ARCHIVO_USUARIO, 'r') as contents:
            USUARIOS = json.load(contents)

        if userToken not in TOKENS:
            raise IceFlix.Unauthorized()
            
        for i in USUARIOS:
            if USUARIOS[i].get("token_actual", None) == userToken:
                usuarioWhoIs = str(i)
                return usuarioWhoIs

        return '¡Token no valido!'

    # Ex: Throws Unauthorized, TemporaryUnavailable. Agrumentos tipo: string,string,string
    def addUser(self, user,passwordHash, adminToken, current=None):

        global USUARIOS
        global TOKENS
        global PRINCIPALES_DISP

        if user in USUARIOS:
            print('[ERROR:] No puedes meter un usuario que ya existe')
            return

        proxy_main = random.choice(list(PRINCIPALES_DISP.values()))
  
        if proxy_main.isAdmin(adminToken):
            usuario_token = secrets.token_urlsafe(
                TAMANIO_TOKEN) 
            UserUpdates = self.obtener_publicaciones('UserUpdates')
            UserUpdates.newUser(
                user, passwordHash, self.server_ID)
            UserUpdates.newToken(user, usuario_token, self.server_ID)

            nuevo_usuario = {user: {
                "token_actual": usuario_token,
                "hash_contrasena": passwordHash
            }}

            USUARIOS.update(nuevo_usuario)  
            self.actualizar_bbdd_usuario()

            TOKENS.add(usuario_token)

        else:
            print("[AUTH]: [ERROR: ] USUARIO NO AUTORIZADO\n")
            raise IceFlix.Unauthorized()

    # Ex: Throws Unauthorized, TemporaryUnavailable. Agrumentos tipo: string,string
    def removeUser(self, user, adminToken, current=None):

        global USUARIOS
        global TOKENS
        global PRINCIPALES_DISP
        if user not in USUARIOS:
            print('[ERROR]: No se puede borrar a un usuario que no existe')
            return

        proxy_principal = random.choice(list(PRINCIPALES_DISP.values()))
        if proxy_principal.isAdmin(adminToken):
            Revocations = self.obtener_publicaciones('Revocations')
            Revocations.revokeUser(user, self.server_ID)
            self.eliminar_Usuarios(user, token_usuario=USUARIOS[user])
        
            self.actualizar_bbdd_usuario()
        else:
            raise IceFlix.Unauthorized()

    # Ex: Throws UnknownService. Agrumentos tipo: UsersDB,string
   
    def updateDB(self, currentDatabase, srvId, current=None):


        global USUARIOS
        global TOKENS
        global AUTENTICATOR_AVAILABLE
        global ACTUALIZADO

        if not ACTUALIZADO:

            ACTUALIZADO = True
            print("[AUTH]: Actualizando base de datos\n")

            if srvId not in AUTENTICATOR_AVAILABLE.keys():

                raise IceFlix.UnknownService()

            for user in currentDatabase.userPasswords.keys():
                nuevoUsuario = {user: {
                        "token_actual": currentDatabase.usersToken[user],
                        "hash_contrasena": currentDatabase.userPasswords[user]
                    }}

                USUARIOS.update(nuevoUsuario)
                TOKENS.add(currentDatabase.usersToken[user])

            print("[AUTH]: Base de datos actualizada\n")
    #para el server
    def obtener_BBDDTokens():
        global USUARIOS
        with open(ARCHIVO_USUARIO, 'r') as contents:
            USUARIOS = json.load(contents)


# Clase de eventos UsersUpdate (Event channel for Authenticator() for notifications to other Authenticator()interface UserUpdates)

class UserUpdates(IceFlix.UserUpdates):

    def __init__(self, uuid):
        self.servicio_ID = uuid

    #Se añade nuevo usuario: args: string,string,string
    def newUser(self, user, passwordHash, srvId, current=None):

        global USUARIOS
        if not srvId == self.servicio_ID:
            print("[AUTH]: Se ha emitido un newUser con el id: "+srvId+"\n")
            nuevo_usuario = {user: {
                "token_actual": "",
                "hash_contrasena": passwordHash
            }}
            USUARIOS.update(nuevo_usuario)

    #Se añade nuevo token: args: string,string,string
    def newToken(self, user, userToken, srvId, current=None):

        global USUARIOS
        global TOKENS
        if not srvId == self.servicio_ID:
            print("[AUTH]: Se ha emitido un newToken con el id: "+srvId+"\n")
            USUARIOS[user]['token_actual'] = userToken
            TOKENS.add(userToken)


class Server(Ice.Application):

    def run(self, argv):

        global USUARIOS
        global TOKENS
        broker = self.communicator()
        self.communicator().stringToIdentity('Authenticator')
        adaptador = broker.createObjectAdapterWithEndpoints(
            'AuthenticatorAdapter', 'tcp')
        adaptador.activate()

        if os.path.exists(ARCHIVO_USUARIO): 
            with open(ARCHIVO_USUARIO, 'r') as contents:
                USUARIOS = json.load(contents)

            TOKENS = set(
                [user.get('token_actual', None) for user in USUARIOS.values()]
            )

        else:  
            with open(ARCHIVO_USUARIO, 'w') as contents:
                json.dump(USUARIOS, contents, indent=4, sort_keys=True)

        serverID = str(uuid.uuid4())
        manager_topics = topic_management.obtainManager(self.communicator())
        revocaciones_topic = topic_management.obtainTopic(manager_topics, 'Revocations')
        revocacion = Revocations(serverID)
        Revocations_proxy = adaptador.addWithUUID(revocacion)
        revocaciones_topic.subscribeAndGetPublisher({}, Revocations_proxy)

        topic_actualizar_usuario = topic_management.obtainTopic(manager_topics, 'UserUpdates')
        actualizacion_usuario = UserUpdates(serverID)
        actualizar_proxy = adaptador.addWithUUID(actualizacion_usuario)
        topic_actualizar_usuario.subscribeAndGetPublisher({}, actualizar_proxy)

      
        servant = Authenticator(broker, serverID)
        authID_service=self.communicator().stringToIdentity('Authenticator')
        proxy = adaptador.addWithUUID(servant)
        print('PROXY: "{}"'.format(proxy), flush=True)
        servant.obtener_proxy(proxy)

        topic_anounce_anon = topic_management.obtainTopic(manager_topics, 'ServiceAnnouncements')
        auth_announce = ServiceAnnouncements(servant, serverID)
        proxy_Aauth = adaptador.addWithUUID(auth_announce)
        topic_anounce_anon.subscribeAndGetPublisher({}, proxy_Aauth)
        
        time.sleep(12)
        try:
            threading.Thread(
                target=self.iniciar_hilos,
                args=(
                    topic_anounce_anon,
                    proxy,
                    serverID,
                ),
            ).start()

        except Exception as e:
            print(e)

        signal.signal(signal.SIGUSR1, servant.obtener_BBDDTokens)
        self.shutdownOnInterrupt()
        self.communicator().waitForShutdown()
        return 0

    def obtener_proxy_service(manager_topics):

        topic_anunce_service = topic_management.obtainTopic(manager_topics, 'ServiceAnnouncements')
        anunce_publicador = topic_anunce_service.getPublisher()
        proxy_service = IceFlix.ServiceAnnouncementsPrx.uncheckedCast(anunce_publicador)
        return proxy_service

    def iniciar_hilos(self,topic_announce,proxy,server_ID):

        publicador =IceFlix.ServiceAnnouncementsPrx.uncheckedCast(topic_announce.getPublisher())
        publicador.newService(proxy, server_ID)
        time.sleep(3)
        while True:
            try:
                publicador = IceFlix.ServiceAnnouncementsPrx.uncheckedCast(topic_announce.getPublisher())
                publicador.announce(proxy, server_ID)
                time.sleep(11)
            except Ice.CommunicatorDestroyedException as e:
                break

if __name__ == '__main__':
    SERVIDOR_AUTH = Server()
    sys.exit(SERVIDOR_AUTH.main(sys.argv))


