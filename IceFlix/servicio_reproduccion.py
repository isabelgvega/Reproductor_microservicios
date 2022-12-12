#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rtsputils
import sqlite3
import threading
import topic_management
import uuid
import sys
import logging
import hashlib
from os import remove
import time
import random
import Ice
Ice.loadSlice('iceflix.ice') 
import IceFlix 

from os import listdir, name
from os.path import isfile


ARCHIVO_PROXYS = 'proxys.json'
BD_CATALOGO = 'db/catalogo.db'
DIRECCION_SUBIDA = 'resources_to_upload/'
DIRECCION_RAIZ = 'resources/'
CHUNK_TAM = 4096

reproducciones_disp = {}
catalogo_disp = {} 
principal_disp = {}
_archivosId_ = []
_archivos_ = []



class ServiceAnnouncements(IceFlix.ServiceAnnouncements):

    def __init__(self, identifier_uuid):

        self.serviceId = identifier_uuid
    
    def newService(self, servicio, serviceId, current=None):

        global reproducciones_disp
        global catalogo_disp
        global principal_disp
        
        if serviceId == self.serviceId:
            logging.debug("The announcement comes from itself")
            return
        else:
            
            print("[STREAMING]: New service from: {}".format(serviceId), flush=True) 
            proxy = IceFlix.MainPrx.checkedCast(servicio)
            if not proxy:
                logging.debug("The announcement comes from itself")
            else:
                  if serviceId not in principal_disp:
                    principal_disp[serviceId] = IceFlix.MainPrx.uncheckedCast(servicio)
                    print("[STREAMING]: A new service has been created: Main")
                
            proxy = IceFlix.MediaCatalogPrx.checkedCast(servicio)
            
            if not proxy:
                logging.debug("The announcement comes from itself")
            else:
                if serviceId not in catalogo_disp:
                    catalogo_disp[serviceId] = IceFlix.MediaCatalogPrx.uncheckedCast(servicio)
                    print("[STREAMING]: A new service has been created: MediaCatalog")
                    
            proxy = IceFlix.StreamProviderPrx.checkedCast(servicio)
            if not proxy:
                logging.debug("The announcement comes from itself")
                return
            else:       
                if serviceId not in reproducciones_disp:

                    reproducciones_disp[serviceId] = IceFlix.StreamProviderPrx.uncheckedCast(servicio)
                    print("[STREAMING]: A new service has been created: StreamProvider")


    def announce(self, servicio, serviceId, current=None):
        
        global reproducciones_disp
        global catalogo_disp
        global principal_disp

        if serviceId == self.serviceId:
            logging.debug("Received own announcement or already known. Ignoring")
            return
        else:
            if servicio.ice_isA('::IceFlix::Main') and serviceId not in principal_disp:
                    print("[STREAMING]: Received service announcement: Principal")
                    principal_disp[serviceId] = IceFlix.MainPrx.uncheckedCast(servicio)
                    

            elif servicio.ice_isA('::IceFlix::MediaCatalog') and serviceId not in catalogo_disp:

                    print("[STREAMING]: Received service announcement: MediaCatalog")
                    catalogo_disp[serviceId] = IceFlix.MediaCatalogPrx.uncheckedCast(servicio)
                        

            elif servicio.ice_isA('::IceFlix::StreamProvider') and serviceId not in reproducciones_disp:

                    print("[STREAMING]: Received service announcement: StreamProvider", flush=True)
                    reproducciones_disp[serviceId] = IceFlix.StreamProviderPrx.uncheckedCast(servicio)
                    


class StreamProvider(IceFlix.StreamProvider):

    def __init__(self, msgBroker, adapter, ReprodAnnProxy, identifier_uuid):

        self.adapter = adapter
        self._broker_ = msgBroker
        self.ReprodAnnProxy = ReprodAnnProxy
        self.servidorId = identifier_uuid
        self.initArchivos()
        self.initArchivosIdentif()
        print("[STREAMING]: -> Starting StreamProvider and Resources, Please wait")        



    def initArchivosIdentif(self):

        global _archivosId_ 
        global _archivos_

        for a in _archivos_:

            _archivosId_.append(self.calcularIdentifArchivo(a))

    def initArchivos(self):
        
        global _archivos_

        for a in listdir(DIRECCION_RAIZ):

            if isfile(DIRECCION_RAIZ+a):

                _archivos_.append(DIRECCION_RAIZ+a)


    def initArchivosCatalogo(self, current=None):

        global _archivosId_
        global _archivos_
        contador = 0

        print("[STREAMING]: Loading resources from "+ DIRECCION_RAIZ +" in the catalog service. Please wait.")

        for a in _archivos_:
            
            nombrearch = _archivos_[contador]
            id_archivo = _archivosId_[contador]
           
            print("[STREAMING]: Name of the film: " + nombrearch + "Identifier: " + id_archivo)
            contador += 1
            print("[STREAMING]: La id del servidor es {}".format(self.servidorId))
            self.ReprodAnnProxy.newMedia(id_archivo, nombrearch[:-4].replace(DIRECCION_RAIZ,""), self.servidorId)


    def calcularIdentifArchivo(self, archivo):
        
        s256hash = hashlib.sha256()

        with open(archivo,"rb") as a:

            for blockBytes in iter(lambda: a.read(4096),b""):

                s256hash.update(blockBytes)

        return s256hash.hexdigest()


    def crearControlador(self, autentificador, tkn, identif, msgBroker, adapter, current): 

        ControladorRep = StreamController(autentificador, tkn, identif, msgBroker, adapter)
        ControladorRepProxy = current.adapter.addWithUUID(ControladorRep)

        return IceFlix.StreamControllerPrx.checkedCast(ControladorRepProxy)



    def getStream(self, mediaId, userToken, current):    

        global principal_disp
        
        prxPrincipal = random.choice(list(principal_disp.values()))

        _principal_ = IceFlix.MainPrx.checkedCast(prxPrincipal)
        if(self.isAvailable(mediaId) == False):

            raise IceFlix.WrongMediaId()

        elif(_principal_.getAuthenticator().isAuthorized(userToken) == False):

            raise IceFlix.Unauthorized()
     

        print("[STREAMING]: -> Creating StreamController. Please wait.")

        ControladorRepProxy = self.crearControlador(_principal_.getAuthenticator(), userToken, mediaId, self._broker_, self.adapter, current)
        print(ControladorRepProxy)
        
        return ControladorRepProxy 



    def isAvailable(self, mediaId, current=None):

        global _archivosId_

        if mediaId not in _archivosId_: 

            return False

        else:
            return True



    def set_self_proxy(self, prx):

        self._proxy_ = prx


    def reannounceMedia(self, srvId, current=None):
        
        global catalogo_disp
        global _archivosId_
        global _archivos_
        
        if srvId not in catalogo_disp.keys():

            print("[STREAMING]: An error may have taken place")
            raise IceFlix.UnknownService
        
        contador = 0

        for a in _archivos_:

            nombreArch = _archivos_[contador]
            id_archivo = _archivosId_[contador]

            print("[STREAMING]: Name of the video: " + nombreArch + "Identifier: " + id_archivo)
            contador += 1
             
            self.ReprodAnnProxy.newMedia(id_archivo, nombreArch[:-4].replace(DIRECCION_RAIZ,""), self.servidorId)



    def uploadMedia(self, fileName, uploader, adminToken, current):
        
        global principal_disp
        global _archivosId_
        global _archivos_
       
        proxyMain = random.choice(list(principal_disp.values()))

        print("[STREAMING]: Uploading the video: " + fileName)
        _principal_ = IceFlix.MainPrx.checkedCast(proxyMain)

        if _principal_.isAdmin(adminToken) == False:
            print(adminToken)
            raise IceFlix.Unauthorized()
        
        mediaData = bytes()

        while True:

            dataChunk = uploader.receive(CHUNK_TAM)

            print(dataChunk)

            if dataChunk.__eq__(b''):
                break

            mediaData = dataChunk + mediaData

        if not mediaData:

            raise IceFlix.UploadError()

        hash  = hashlib.sha256()
        hash.update(mediaData)

        identMedia = hash.hexdigest()
        print("[STREAMING]: IDENTIFIER: "+ identMedia)

        print("[STREAMING]: Database is updating.")
        _archivosId_.append(identMedia)
        _archivos_.append(DIRECCION_SUBIDA + fileName)

        prx = self.adapter.addWithUUID(self)

        print("[STREAMING]: Operation completed, the resource has been uploaded.")
        print("[STREAMING]: \nLa id del provider es {}\n".format(self.servidorId))
        self.ReprodAnnProxy.newMedia(identMedia, fileName[:-4].replace(DIRECCION_RAIZ,""), self.servidorId)


    def deleteMedia(self, mediaId, adminToken, current=None):
        
        global principal_disp
        global _archivosId_
        global _archivos_
        prxPrincipal = random.choice(list(principal_disp.values()))

        _principal_ = IceFlix.MainPrx.checkedCast(prxPrincipal)

        
        if not self.isAvailable(mediaId) == True:
            
            raise IceFlix.WrongMediaId()

        elif not _principal_.isAdmin(adminToken) == True:

            raise IceFlix.Unauthorized()

        print("[STREAMING]: This resource will be deleted: " + mediaId)
        contador = 0
        
        for a in _archivosId_:

            if not a != mediaId:

                break

            contador += 1

        nombre = _archivos_[contador]
        
        print("[STREAMING]: Deleting " + nombre + " file, please wait.")
        
        _archivosId_.remove(mediaId)
        _archivos_.remove(nombre) 

        self.removeTile(nombre)

        print("[STREAMING]: Operation completed, " + nombre + " deleted.")
        self.ReprodAnnProxy.removedMedia(mediaId, self.servidorId)


 
    def connect(self):
        
        try:

            conexion = sqlite3.connect(BD_CATALOGO)
            
            return conexion
        
        except Exception:

            print("[STREAMING]: Error, something went wrong")



    def removeTile(self, nombre):
        
        print("[STREAMING]: The resource is being deleted from the database, please wait.")
        
            
       


        
    
class Revocations(IceFlix.Revocations):

    def __init__(self, gestor_topic, controlador, usuario, tkn, servidorId):
        
        self.controladorToken = tkn
        self.gestor_topic = gestor_topic
        self.user_controlador = usuario
        self.servidorId = servidorId
        self.controlador = controlador 


    def revokeUser(self, usuario, servidorId, current=None):
       
        if not servidorId == self.servidorId:

            print("[STREAMING]: Revoke User sent from {}".format(servidorId))

            if not (usuario != str(self.user_controlador)):
       
                topicSincronReprod = topic_management.obtainTopic(self.gestor_topic, self.controlador.getSyncTopic())
                publicadorSincronReprod = topicSincronReprod.getPublisher()

                prxSincronReprod = IceFlix.StreamSyncPrx.uncheckedCast(publicadorSincronReprod)
                prxSincronReprod.requestAuthentication()  



    def revokeToken(self, tokenUsuario, servidorId, current=None):

        if not servidorId == self.servidorId:

            print("[STREAMING]: RevokeToken sent from {}".format(servidorId))

            if not (tokenUsuario != str(self.controladorToken)):

                topicSincronReprod = topic_management.obtainTopic(self.gestor_topic, self.controlador.getSyncTopic())
                publicadorSincronReprod = topicSincronReprod.getPublisher()

                prxSincronReprod = IceFlix.StreamSyncPrx.uncheckedCast(publicadorSincronReprod)
                prxSincronReprod.requestAuthentication() 



    def updateToken(self, tkn, current=None):

        self.controladorToken = tkn




class Server(Ice.Application):

    def run(self, argv):

        Servbroker = self.communicator()

        adapter = Servbroker.createObjectAdapterWithEndpoints('StreamingAdapter', 'tcp')
        adapter.activate()
        gestor_topic = topic_management.obtainManager(self.communicator())

        ReprodAnnProxy = self.get_ReprodAnnProxy(gestor_topic)
        servidorId = str(uuid.uuid4())

        topicAnnouncPrincip = topic_management.obtainTopic(gestor_topic, 'ServiceAnnouncements')
        announcPrincip = ServiceAnnouncements(servidorId)

        proxyAnnouncPrincip = adapter.addWithUUID(announcPrincip)
        topicAnnouncPrincip.subscribeAndGetPublisher({}, proxyAnnouncPrincip)
        ServProvider = StreamProvider(Servbroker, adapter, ReprodAnnProxy, servidorId)
        servProviderProxy = adapter.add(ServProvider, Servbroker.stringToIdentity("streamprovider1"))

        ServProvider.set_self_proxy(servProviderProxy)
        
        ProxyServicioPrinc = self.get_ProxyServPrincip(gestor_topic)
        print('"{}"'.format(servProviderProxy))
        time.sleep(11)
        
        print("[STREAMING]: -> server prepared")
        try:

            threading.Thread(target=self.init_threads, args=(ProxyServicioPrinc, servProviderProxy, servidorId, ServProvider,),).start() 
            
        except Exception as error:

            print("[STREAMING]: Error, something went wrong in streaming")
            
        self.shutdownOnInterrupt()

        Servbroker.waitForShutdown()
        
        return 0



    def get_ReprodAnnProxy(self, gestor_topic):

        topicAnnRep = topic_management.obtainTopic(gestor_topic, 'StreamAnnouncements')
        announPubli = topicAnnRep.getPublisher()

        ReprodAnnProxy = IceFlix.StreamAnnouncementsPrx.uncheckedCast(announPubli)

        return ReprodAnnProxy
    
    def get_ProxyServPrincip(self, gestor_topic):

        topicAnnServic = topic_management.obtainTopic(gestor_topic, 'ServiceAnnouncements')
        announPubli = topicAnnServic.getPublisher()

        proxyAnnServic = IceFlix.ServiceAnnouncementsPrx.uncheckedCast(announPubli)

        return proxyAnnServic


    def init_threads(self, publisher, services, servidorId, provider):

        publisher.newService(services, servidorId)

        time.sleep(4) 
        provider.initArchivosCatalogo()
        
        while True:

            try:

                publisher.announce(services, servidorId)

                time.sleep(9)

            except Ice.CommunicatorDestroyedException as error:

                break



class StreamController(IceFlix.StreamController): 

    def __init__(self, autentificador, tkn, identif_media, msgBroker, adapter):

        print("[STREAMING]: Starting Stream Controller. Please wait.")

        self.autentificador = autentificador 
        self.usuario = self.autentificador.whois(tkn) 
        self.tokenUsuario = tkn
        self._IdentifMedia_ = identif_media
        self.msgBroker = msgBroker
        servidorId = str(uuid.uuid4())     
        
        self.adapter = adapter
        gestor_topic = topic_management.obtainManager(msgBroker)

        self.revocations = Revocations(gestor_topic, self, self.usuario, self.tokenUsuario, servidorId) 

        topicRevocations = topic_management.obtainTopic(gestor_topic, 'Revocations')
        proxyRevocations = self.adapter.addWithUUID(self.revocations)
        topicRevocations.subscribeAndGetPublisher({}, proxyRevocations)
        print("[STREAMING]: Related resource: " + self._IdentifMedia_)


    def getSyncTopic(self, current=None):

        gestor_topic = topic_management.obtainManager(self.msgBroker)
        topicSincronReprod = topic_management.obtainTopic(gestor_topic, 'StreamSync')

        return topicSincronReprod.getName()


    def getSDP(self, userToken, port, current=None):

        global _archivosId_
        global _archivos_
        
        if not self.autentificador.isAuthorized(userToken) == True:

            raise IceFlix.Unauthorized()
        
        contador = 0

        for identif in _archivosId_:

            if identif == self._IdentifMedia_:

                break

            contador += 1
        
        nombreMedia = _archivos_[contador]

        self.rtspEmisor = rtsputils.RTSPEmitter(nombreMedia, '127.0.0.1', port)
        self.rtspEmisor.start() 

        playRTP = self.rtspEmisor.playback_uri

        return playRTP


    def stop(self, current=None):

        self.rtspEmisor.stop()

        print("[STREAMING]: The Controller has been erased")

        del self  



    def refreshAuthentication(self, userToken, current=None):

        if not self.autentificador.isAuthorized(userToken):
        
            raise IceFlix.Unauthorized()

        self.tokenUsuario = userToken
        self.revocations.updateToken(userToken)



    
STREAM = Server()
sys.exit(STREAM.main(sys.argv))
